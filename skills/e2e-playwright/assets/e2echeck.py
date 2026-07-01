#!/usr/bin/env python3
"""
e2echeck.py — L1 tripwire for AC-driven HTTP e2e specs (Jest + Playwright request).

Checks that every acceptance criterion in the source-of-intent is traced by an e2e
test whose title carries the stable prefix  [<CARD> - AC-NNN]  — and distinguishes:
  - it("[CARD - AC-NNN] ...")        → COVERED (an active, runnable test)
  - it.skip("[CARD - AC-NNN] ...")   → DECLARED non-HTTP-observable (must carry a reason;
                                        whether the reason is VALID is L2's judgment, not this)
  - an AC in the source but in neither → UNCOVERED  (an ERROR — a silent gap)

This is a TRIPWIRE, not ground truth: it parses test-title strings with regex (not a TS
AST) and counts AC coverage. Semantic fidelity — does the test actually assert the AC's
expected status/error-code — is the L2 fresh-eyes verifier's job.

  python3 e2echeck.py <spec-dir-or-file> <ac-source-file-or-dir> [--card GI-74]

<spec-dir-or-file> : a tests/e2e/specs dir (scanned for *.e2e.ts/.spec.ts) or one spec file.
<ac-source>        : the design doc(s) the ACs live in (a file or a dir — .md/.html/.txt are
                     all read as text); AC ids are extracted as the tokens  AC-<n>.
--card             : the expected JIRA card (e.g. GI-74). Optional — inferred from the spec
                     titles when omitted.

Exit 0 = PASS (0 errors); exit 1 = at least one ERROR; exit 2 = usage/IO error.
NOTE lines never fail. Stdlib only — no third-party dependency.
"""
import sys
import os
import re
import glob

errors = []
notes = []


def err(msg):
    errors.append(msg)


def note(msg):
    notes.append(msg)


# ---- AC id normalization (so AC-001 in a test == AC-1 in a design doc) ----

def norm_ac(ac):
    """AC-001 / AC-01 / AC-1 → canonical AC-1 for comparison."""
    m = re.match(r"AC-0*(\d+)$", ac, re.I)
    return f"AC-{int(m.group(1))}" if m else ac.upper()


# ---- the stable test-title prefix:  [<CARD> - AC-NNN] ... -----------------
# card = letters + dash + digits (GI-74, BFID-5); then " - " ; then AC-NNN.
PREFIX_RE = re.compile(
    r"\[\s*([A-Za-z][A-Za-z0-9]*-\d+)\s*-\s*(AC-\d+)\b([^\]]*)\]",
    re.I,
)

# a Jest/Playwright test declaration: it / test, optional .skip/.only/.todo,
# then a quoted title. Capture the modifier + the title string (quote-aware).
TEST_RE = re.compile(
    r"""\b(it|test)(\.\w+)?\s*\(\s*(["'`])((?:\\.|(?!\3).)*)\3""",
    re.S,
)

AC_TOKEN_RE = re.compile(r"\bAC-\d+\b", re.I)


def iter_spec_files(spec_path):
    if os.path.isfile(spec_path):
        return [spec_path]
    pats = ("*.e2e.ts", "*.e2e.js", "*.spec.ts", "*.spec.js")
    out = []
    for p in pats:
        out += glob.glob(os.path.join(spec_path, "**", p), recursive=True)
    return sorted(set(out))


def read_text(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.read()
    except Exception as e:  # noqa: BLE001
        err(f"{os.path.relpath(path)}: cannot read — {e}")
        return ""


def _phys_line(src, pos):
    """The single physical line of source containing offset `pos`."""
    start = src.rfind("\n", 0, pos) + 1
    end = src.find("\n", pos)
    return src[start:] if end == -1 else src[start:end]


def collect_specs(spec_path):
    """Return {norm_ac: {'active': [..titles], 'skipped': [(title, has_reason)]}} + cards seen.

    Primary coverage = the [<CARD> - AC-NNN] title prefix (strict — validates grammar + card).
    Secondary coverage = any extra AC-<n> token on the SAME physical line as the it() (e.g. a
    `// (also AC-008)` comment) — credited leniently with the same active/skipped status, because
    a single test often co-covers ACs; the L2 fresh-eyes verifier confirms each claim is real.
    """
    cov = {}
    cards = set()
    files = iter_spec_files(spec_path)
    if not files:
        err(f"no spec files (*.e2e.ts/.spec.ts) found under {spec_path}")
        return cov, cards, files
    for fp in files:
        src = read_text(fp)
        rel = os.path.relpath(fp)
        for m in TEST_RE.finditer(src):
            modifier = (m.group(2) or "").lower()
            title = m.group(4)
            skipped = (".skip" in modifier) or (".todo" in modifier)
            pm = PREFIX_RE.search(title)
            if not pm:
                # a test with no valid prefix — flag only if it looks like it meant to have one
                if AC_TOKEN_RE.search(title):
                    err(f"{rel}: test title references an AC but is not in [<CARD> - AC-NNN] form: {title!r}")
                continue
            cards.add(pm.group(1).upper())
            reason_text = (pm.group(3) + title[pm.end():]).strip()
            # primary (from the prefix) + secondary (other AC tokens on the it() line)
            line = _phys_line(src, m.start())
            acs_here = {norm_ac(pm.group(2))} | {norm_ac(t) for t in AC_TOKEN_RE.findall(line)}
            for nac in acs_here:
                slot = cov.setdefault(nac, {"active": [], "skipped": []})
                if skipped:
                    slot["skipped"].append((title, bool(reason_text)))
                else:
                    slot["active"].append(title)
    return cov, cards, files


def collect_acs(ac_path):
    """Extract the set of AC ids (normalized → original-form) from the design source(s)."""
    if os.path.isfile(ac_path):
        files = [ac_path]
    elif os.path.isdir(ac_path):
        files = sorted(
            f for f in glob.glob(os.path.join(ac_path, "**", "*"), recursive=True)
            if os.path.isfile(f) and f.rsplit(".", 1)[-1].lower() in ("md", "html", "htm", "txt", "yaml", "yml", "json")
        )
    else:
        err(f"ac-source {ac_path} is neither a file nor a directory")
        return {}
    found = {}
    for fp in files:
        for tok in AC_TOKEN_RE.findall(read_text(fp)):
            found.setdefault(norm_ac(tok), tok.upper())
    return found


def main():
    pos = [a for a in sys.argv[1:] if not a.startswith("--")]
    card_arg = None
    for a in sys.argv[1:]:
        if a.startswith("--card"):
            card_arg = a.split("=", 1)[1] if "=" in a else None
    # support `--card GI-74` (space form)
    if "--card" in sys.argv:
        i = sys.argv.index("--card")
        if i + 1 < len(sys.argv) and not sys.argv[i + 1].startswith("--"):
            card_arg = sys.argv[i + 1]
            pos = [a for a in pos if a != card_arg]

    if len(pos) < 2:
        sys.stderr.write("usage: e2echeck.py <spec-dir-or-file> <ac-source> [--card GI-74]\n")
        sys.exit(2)
    spec_path, ac_path = pos[0], pos[1]
    if not os.path.exists(spec_path):
        sys.stderr.write(f"e2echeck: spec path {spec_path} does not exist\n")
        sys.exit(2)
    if not os.path.exists(ac_path):
        sys.stderr.write(f"e2echeck: ac-source {ac_path} does not exist\n")
        sys.exit(2)

    cov, cards, files = collect_specs(spec_path)
    acs = collect_acs(ac_path)

    if not acs:
        err(f"no AC ids (AC-<n>) found in {ac_path} — cannot verify coverage")

    # card consistency
    expected_card = (card_arg or "").upper() or None
    if expected_card and cards and expected_card not in cards:
        err(f"--card {expected_card} not found in any spec title (saw: {', '.join(sorted(cards)) or 'none'})")
    if len(cards) > 1:
        note(f"specs mix multiple card ids: {', '.join(sorted(cards))}")

    # coverage rows
    covered, skipped_only, uncovered = [], [], []
    for nac, orig in sorted(acs.items(), key=lambda kv: int(re.sub(r"\D", "", kv[0]) or 0)):
        slot = cov.get(nac)
        if slot and slot["active"]:
            covered.append(orig)
        elif slot and slot["skipped"]:
            skipped_only.append(orig)
            for title, has_reason in slot["skipped"]:
                if not has_reason:
                    err(f"{orig}: only an it.skip() with no reason — a non-HTTP-observable AC must state why in its title")
        else:
            uncovered.append(orig)
            err(f"{orig}: no e2e test — add an it(\"[<CARD> - {orig} ...]\") or, if not HTTP-observable, an it.skip() with a reason")

    # orphans: AC referenced by a spec but absent from the AC source
    for nac in sorted(cov):
        if nac not in acs:
            note(f"{cov.get(nac) and nac}: a spec references {nac} but it is not in the AC source — stale test or incomplete source?")

    # ---- report -----------------------------------------------------------
    print("AC coverage:")
    print(f"  covered (active it):        {len(covered)}  {', '.join(covered)}")
    print(f"  declared non-observable:    {len(skipped_only)}  {', '.join(skipped_only)}  (it.skip — L2 validates the reason)")
    print(f"  UNCOVERED:                  {len(uncovered)}  {', '.join(uncovered)}")
    print(f"  specs scanned: {len(files)}   AC ids in source: {len(acs)}")
    print()
    for n in notes:
        print("NOTE:", n)
    for e in errors:
        print("ERROR:", e)
    if errors:
        print(f"FAIL — {len(errors)} error(s)")
        sys.exit(1)
    print(f"PASS — 0 error(s) ({len(covered)} AC covered, {len(skipped_only)} declared non-observable)")


if __name__ == "__main__":
    main()
