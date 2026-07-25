#!/usr/bin/env python3
"""
neocheck.py — run every MACHINE gate for a card and print one table.

The gates already exist; the failure mode this closes is a human or an agent running
two of the three and calling the card done. One command, one table, one exit code —
so "were the gates run?" is answerable from a single pasted block instead of trust.

  python3 neocheck.py <repo> <card> [--timeout SECONDS] [--min-coverage PCT]

Runs, against <repo>:
  AC coverage    e2echeck.py   tests/e2e/specs + docs/tasks/<card>/spec.md --card <card>
  Unit coverage  the repo's own coverage target (discovered from its Makefile)
  API contract   apispeccheck.py docs/api --check

Judgment gates (api-spec drift, code-review, fresh-eyes, spec/plan + MR approval) are NOT
run here and are listed as outstanding, so the table never reads as more than it is.

Exit 0 = every machine gate passed; 1 = at least one failed; 2 = usage/setup error.
Stdlib only.
"""
import os
import re
import subprocess
import sys

SKILL_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
E2ECHECK = os.path.join(SKILL_ROOT, "e2e-playwright", "assets", "e2echeck.py")
APISPECCHECK = os.path.join(SKILL_ROOT, "api-spec", "assets", "apispeccheck.py")

MANUAL_GATES = [
    ("API drift", "openapi-doc — Go source vs docs/api"),
    ("Code review", "code-review — Standards / Spec / Security"),
    ("Fresh eyes", "REVIEW step — independent pass on the diff"),
    ("Spec + plan, MR", "human approval"),
]


def run(cmd, cwd, timeout):
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, p.stdout + p.stderr
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout}s"
    except OSError as e:
        return 2, str(e)


def coverage_target(repo):
    """The repo's own coverage target — the one whose recipe measures coverage."""
    mk = os.path.join(repo, "Makefile")
    if not os.path.isfile(mk):
        return None
    with open(mk, encoding="utf-8", errors="replace") as fh:
        src = fh.read()
    # target: ... then its indented recipe, up to the next non-indented line
    best = None
    for m in re.finditer(r"^([A-Za-z][\w-]*):[^\n=]*\n((?:[ \t]+.*\n|\n)*)", src, re.M):
        name, recipe = m.group(1), m.group(2)
        if "check-coverage.sh" in recipe:
            return name  # an enforcing gate always wins
        if "-coverprofile" in recipe and best is None:
            best = name
    return best


def gate_ac(repo, card, timeout):
    specs = os.path.join(repo, "tests", "e2e", "specs")
    spec_md = os.path.join(repo, "docs", "tasks", card, "spec.md")
    if not os.path.isdir(specs):
        return "SKIP", "no tests/e2e/specs", "—"
    if not os.path.isfile(spec_md):
        return "SKIP", f"no docs/tasks/{card}/spec.md", "—"
    cmd = [sys.executable, E2ECHECK, specs, spec_md, "--card", card]
    rc, out = run(cmd, repo, timeout)
    if "No-AC mode" in out:
        return ("PASS" if rc == 0 else "FAIL"), "No-AC mode — nothing to cover", f"e2echeck.py … --card {card}"
    m = re.search(r"covered \(active it\):\s*(\d+)", out)
    d = re.search(r"declared deferred:\s*(\d+)", out)
    detail = f"{m.group(1) if m else '?'} covered, {d.group(1) if d else '0'} deferred"
    return ("PASS" if rc == 0 else "FAIL"), detail, f"e2echeck.py … --card {card}"


def gate_coverage(repo, timeout, minimum):
    """Run the repo's coverage target AND apply the threshold here.

    Not every repo's target enforces: some print the percentage and exit 0 at any value.
    Trusting the exit code alone would report PASS at 40% — a gate that cannot fail is
    theatre, so the number is compared here regardless of what the Makefile does.
    """
    target = coverage_target(repo)
    if not target:
        return "SKIP", "no coverage target in Makefile", "—"
    rc, out = run(["make", target], repo, timeout)
    m = re.search(r"coverage gate (?:passed|failed): ([\d.]+)%", out) or \
        re.search(r"^total:\s+\(statements\)\s+([\d.]+)%", out, re.M)
    cmd = f"make {target}"
    if not m:
        why = "target failed before reporting coverage" if rc != 0 else "ran but reported no percentage"
        return "FAIL", why, cmd
    pct = float(m.group(1))
    if rc != 0:
        return "FAIL", f"{pct}% (target failed)", cmd
    if pct < minimum:
        return "FAIL", f"{pct}% < {minimum}% (target does not enforce)", cmd
    return "PASS", f"{pct}% ≥ {minimum}%", cmd


def suite_title_sweep(repo, card, timeout):
    """Title-grammar problems across the WHOLE suite, not just this card's files.

    The AC gate deliberately downgrades a malformed title in another card's file to a note, so
    one card is never held hostage by another's mistake. The side effect is that a team running
    only `--card` never sees those breakages at all. This re-runs without `--card`, where every
    file is in scope, and surfaces the count — as information, not as this card's failure.
    """
    specs = os.path.join(repo, "tests", "e2e", "specs")
    spec_md = os.path.join(repo, "docs", "tasks", card, "spec.md")
    if not (os.path.isdir(specs) and os.path.isfile(spec_md)):
        return None
    _rc, out = run([sys.executable, E2ECHECK, specs, spec_md], repo, timeout)
    bad = [ln for ln in out.splitlines() if ln.startswith("ERROR:") and "is not in [<CARD> - AC-NNN] form" in ln]
    return len(bad)


def gate_api(repo, timeout):
    api = os.path.join(repo, "docs", "api")
    if not os.path.isdir(api):
        return "SKIP", "no docs/api", "—"
    rc, out = run([sys.executable, APISPECCHECK, api, "--check"], repo, timeout)
    m = re.search(r"FAIL — (\d+) error", out)
    detail = f"{m.group(1)} error(s)" if m else "0 errors"
    return ("PASS" if rc == 0 else "FAIL"), detail, "apispeccheck.py docs/api --check"


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = {"--timeout": 900, "--min-coverage": 80}
    for flag in opts:
        if flag in sys.argv:
            i = sys.argv.index(flag)
            if i + 1 < len(sys.argv):
                if not sys.argv[i + 1].isdigit():
                    sys.stderr.write(f"neocheck: {flag} needs a whole number, got {sys.argv[i + 1]!r}\n")
                    sys.exit(2)
                opts[flag] = int(sys.argv[i + 1])
                pos = [a for a in pos if a != sys.argv[i + 1]]
    timeout, minimum = opts["--timeout"], opts["--min-coverage"]
    if len(pos) < 2:
        sys.stderr.write("usage: neocheck.py <repo> <card> [--timeout SECONDS] [--min-coverage PCT]\n")
        sys.exit(2)
    repo, card = os.path.abspath(pos[0]), pos[1]
    if not os.path.isdir(repo):
        sys.stderr.write(f"neocheck: {repo} is not a directory\n")
        sys.exit(2)
    for asset in (E2ECHECK, APISPECCHECK):
        if not os.path.isfile(asset):
            sys.stderr.write(f"neocheck: missing checker {asset}\n")
            sys.exit(2)

    rows = [
        ("AC coverage",) + gate_ac(repo, card, timeout),
        ("Unit coverage",) + gate_coverage(repo, timeout, minimum),
        ("API contract",) + gate_api(repo, timeout),
    ]

    print(f"neocheck — {card} @ {repo}\n")
    w = max(len(r[0]) for r in rows)
    for name, status, detail, cmd in rows:
        print(f"  {name:<{w}}  {status:<5}  {detail:<34}  {cmd}")
    sweep = suite_title_sweep(repo, card, timeout)
    if sweep:
        print(f"\n  suite-wide: {sweep} malformed test title(s) in other cards' files — not this"
              f" card's gate, but someone owns them (re-run e2echeck without --card to list)")

    print("\n  not machine-checkable — still owed:")
    for name, what in MANUAL_GATES:
        print(f"    {name:<16} {what}")

    failed = [r[0] for r in rows if r[1] == "FAIL"]
    skipped = [r[0] for r in rows if r[1] == "SKIP"]
    print()
    if failed:
        print(f"FAIL — {', '.join(failed)}")
        sys.exit(1)
    if len(skipped) == len(rows):
        # Never let "nothing ran" read as green.
        print("NO MACHINE GATE APPLIED — nothing was verified: " + ", ".join(skipped))
        return
    print(f"PASS — {len(rows) - len(skipped)} machine gate(s) green"
          + (f"; {', '.join(skipped)} skipped (not applicable here)" if skipped else ""))


if __name__ == "__main__":
    main()
