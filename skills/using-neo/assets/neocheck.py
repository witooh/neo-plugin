#!/usr/bin/env python3
"""
neocheck.py — run every MACHINE gate for a card and print one table.

The gates already exist; the failure mode this closes is a human or an agent running
two of the three and calling the card done. One command, one table, one exit code —
so "were the gates run?" is answerable from a single pasted block instead of trust.

  python3 neocheck.py <repo> <card> [--ac-source PATH] [--timeout SECONDS] [--min-coverage PCT]

Runs, against <repo>:
  AC coverage    e2echeck.py   tests/e2e/specs + this card's AC source --card <card>
                 AC source = docs/tasks/<card>/spec.md, or --ac-source PATH for a legacy
                 docs/design/<usecase>/ layout. An e2e suite with no AC source is a FAIL,
                 not a skip: a skip prints as "not applicable" and counts toward green.
  Unit coverage  the repo's own coverage target (discovered from its Makefile)
  API contract   apispeccheck.py docs/api --check

Judgment items (api-spec drift, code-review, fresh-eyes, MR if the user asked to ship) are NOT
run here and are listed as outstanding, so the table never reads as more than it is.

Exit 0 = at least one machine gate ran and every one that ran passed; 1 = at least one
failed; 2 = usage/setup error; 3 = no machine gate applied, so nothing was verified.
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
    ("API drift", "openapi-doc — Go source vs docs/api — when HTTP/contract touched"),
    ("Code review", "fresh-eyes + Security axis when the diff earns it"),
    ("Fresh eyes", "only when the wave diff touches production / docs/api / e2e"),
    ("MR", "human confirm — only if the user asked to ship"),
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


def ac_source_path(repo, card, override):
    """Where this card's ACs live: the explicit override, else the neo spec."""
    if override:
        return override if os.path.isabs(override) else os.path.join(repo, override)
    return os.path.join(repo, "docs", "tasks", card, "spec.md")


def gate_ac(repo, card, timeout, override=None):
    specs = os.path.join(repo, "tests", "e2e", "specs")
    src = ac_source_path(repo, card, override)
    if not os.path.isdir(specs):
        return "SKIP", "no tests/e2e/specs", "—"
    if not os.path.exists(src):
        # SKIP counts toward the green summary and prints as "not applicable", so the
        # likeliest real gap — nobody wrote this card's ACs down — would read as a pass.
        # A card claimed done against a live e2e suite has an AC source, or it has a gap.
        return "FAIL", f"no AC source at {os.path.relpath(src, repo)}", "—"
    cmd = [sys.executable, E2ECHECK, specs, src, "--card", card]
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


def suite_title_sweep(repo, card, timeout, override=None):
    """Title-grammar problems across the WHOLE suite, not just this card's files.

    The AC gate deliberately downgrades a malformed title in another card's file to a note, so
    one card is never held hostage by another's mistake. The side effect is that a team running
    only `--card` never sees those breakages at all. This re-runs without `--card`, where every
    file is in scope, and surfaces the count — as information, not as this card's failure.
    """
    specs = os.path.join(repo, "tests", "e2e", "specs")
    src = ac_source_path(repo, card, override)
    if not (os.path.isdir(specs) and os.path.exists(src)):
        return None
    _rc, out = run([sys.executable, E2ECHECK, specs, src], repo, timeout)
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
    argv = sys.argv[1:]
    ac_source = None
    if "--ac-source" in argv:
        i = argv.index("--ac-source")
        if i + 1 >= len(argv):
            sys.stderr.write("neocheck: --ac-source needs a path\n")
            sys.exit(2)
        ac_source = argv[i + 1]
        argv = argv[:i] + argv[i + 2:]
    pos = [a for a in argv if not a.startswith("--")]
    opts = {"--timeout": 900, "--min-coverage": 80}
    for flag in opts:
        if flag in argv:
            i = argv.index(flag)
            if i + 1 < len(argv):
                if not argv[i + 1].isdigit():
                    sys.stderr.write(f"neocheck: {flag} needs a whole number, got {argv[i + 1]!r}\n")
                    sys.exit(2)
                opts[flag] = int(argv[i + 1])
                pos = [a for a in pos if a != argv[i + 1]]
    timeout, minimum = opts["--timeout"], opts["--min-coverage"]
    if len(pos) < 2:
        sys.stderr.write("usage: neocheck.py <repo> <card> [--ac-source PATH]"
                         " [--timeout SECONDS] [--min-coverage PCT]\n")
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
        ("AC coverage",) + gate_ac(repo, card, timeout, ac_source),
        ("Unit coverage",) + gate_coverage(repo, timeout, minimum),
        ("API contract",) + gate_api(repo, timeout),
    ]

    print(f"neocheck — {card} @ {repo}\n")
    w = max(len(r[0]) for r in rows)
    for name, status, detail, cmd in rows:
        print(f"  {name:<{w}}  {status:<5}  {detail:<34}  {cmd}")
    sweep = suite_title_sweep(repo, card, timeout, ac_source)
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
        # A caller reads exit 0 as "verified". Zero gates verified nothing, so it is not 0.
        print("NO MACHINE GATE APPLIED — nothing was verified: " + ", ".join(skipped))
        sys.exit(3)
    print(f"PASS — {len(rows) - len(skipped)} machine gate(s) green"
          + (f"; {', '.join(skipped)} skipped (not applicable here)" if skipped else ""))


if __name__ == "__main__":
    main()
