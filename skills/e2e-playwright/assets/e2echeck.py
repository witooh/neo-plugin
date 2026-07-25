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
# The prefix is a bracketed label whose last id is the AC. Everything before the
# final " - AC-NNN" is the label, so all three real shapes parse:
#   [GI-1036 - AC-005]              label GI-1036            (JIRA key)
#   [awareness-answer-resp - AC-001] label awareness-answer-resp (slug card, no JIRA key)
#   [TC-028 - GI-52 - AC-001]       label "TC-028 - GI-52"    (test-case id + card)
PREFIX_RE = re.compile(
    r"\[([^\]]*?)\s*-\s*(AC-\d+)\b([^\]]*)\]",
    re.I,
)

# A table-driven title interpolates the AC id:  it(`[GI-1036 - ${tc.ac}] ...`)
DYN_PREFIX_RE = re.compile(r"\[([^\]]*?)\s*-\s*\$\{\s*([\w.]+)\s*\}", re.I)

# Within a label, a JIRA-style key. The LAST one is the card: in "TC-028 - GI-52"
# the leading token is a test-case id and the card is GI-52.
CARD_TOKEN_RE = re.compile(r"\b[A-Za-z][A-Za-z0-9]*-\d+\b")


def card_of(label):
    """The card id inside a prefix label — the last JIRA-style key, else the whole label."""
    keys = CARD_TOKEN_RE.findall(label)
    return (keys[-1] if keys else label.strip()).upper()

# a Jest/Playwright test declaration: it / test, optional .skip/.only/.todo,
# then a quoted title. Capture the modifier + the title string (quote-aware).
TEST_RE = re.compile(
    r"""\b(it|test)(\.\w+)?\s*\(\s*(["'`])((?:\\.|(?!\3).)*)\3""",
    re.S,
)

AC_TOKEN_RE = re.compile(r"\bAC-\d+\b", re.I)

# "GI-445 AC-008" — or "the GI-445 verify-session (AC-008)" — in GI-446's spec references
# ANOTHER card's criterion, not one of this card's own. Harvesting it invents an AC that can
# never be covered: a phantom UNCOVERED that sends people hunting for a test that should not
# exist. An AC id counts as foreign when a DIFFERENT card id appears just before it on the
# same line; a mention of this card's own id is left alone.
FOREIGN_LOOKBEHIND = 40

# No-AC mode: a task with no acceptance criteria titles its tests `[<CARD>] <desc>` — a card
# prefix with no AC segment. Only honoured at the START of a title, so an incidental `[x]`
# mid-sentence is not mistaken for a card.
CARD_ONLY_RE = re.compile(r"^\s*\[([^\]]+)\]")

# An AC deliberately left unbuilt must be declared once, machine-readably, in the AC
# source:   Deferred-ACs: AC-011, AC-012 — biometric challenge protocol (D10)
# Prose is not scanned for the word "deferred": a real spec line reads "Was: defer
# AC-007/008/013 … AC-007 + AC-008 un-deferred … AC-013 remains deferred", where
# line-level matching gets every one of the three wrong.
DEFERRED_RE = re.compile(r"^[^\S\n]*Deferred-ACs?[^\S\n]*:(.*)$", re.I | re.M)


def resolve_dynamic_acs(src, it_pos, expr):
    """`${tc.ac}` → the AC ids of the table the enclosing loop draws `tc` from.

    Follows  for (const tc of scheduleCases)  →  const scheduleCases = [ { ac: "AC-001" }, ... ].
    Returns [] when the chain cannot be followed, so the caller can report it rather
    than silently crediting nothing.
    """
    var, _, field = expr.partition(".")
    if not field:
        return []
    head = src[:it_pos]
    loop = None
    for m in re.finditer(rf"\bfor\s*\(\s*(?:const|let|var)\s+{re.escape(var)}\s+of\s+(\w+)", head):
        loop = m
    if not loop:
        return []
    tm = None
    for m in re.finditer(rf"\b{re.escape(loop.group(1))}\b[^=\n]*=\s*\[", head):
        tm = m
    if not tm:
        return []
    depth, i = 0, tm.end() - 1
    while i < len(head):
        if head[i] == "[":
            depth += 1
        elif head[i] == "]":
            depth -= 1
            if depth == 0:
                break
        i += 1
    body = head[tm.end() - 1:i + 1]
    return re.findall(rf"{re.escape(field)}\s*:\s*[\"'`](AC-\d+)[\"'`]", body, re.I)


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


def collect_specs(spec_path, expected_card=None):
    """Return {norm_ac: {'active': [(title, card)], 'skipped': [(title, has_reason, card)]}} + cards.

    Each credit carries the card that claimed it, because AC ids are numbered PER CARD: two
    cards both own an AC-001. Matching by bare id across the suite reports a card with no tests
    at all as fully covered, off another card's AC-001 — a false PASS, the worst kind. `--card`
    filtering happens in main(); this function only records who claimed what.

    Primary coverage = the [<CARD> - AC-NNN] title prefix (strict — validates grammar + card).
    Secondary coverage = any extra AC-<n> token on the SAME physical line as the it() (e.g. a
    `// (also AC-008)` comment) — credited leniently with the same active/skipped status, because
    a single test often co-covers ACs; the L2 fresh-eyes verifier confirms each claim is real.

    Title-grammar problems are attributed to the card that OWNS the file: with `--card X`, a
    malformed title in a file holding no test for X is reported as a NOTE, not an ERROR. One
    card's gate must not be held hostage by another card's spec file — a gate that fails for
    someone else's mistake is a gate people learn to ignore. Coverage errors for X stay ERRORs.
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
        file_cards = set()
        grammar = []
        for m in TEST_RE.finditer(src):
            modifier = (m.group(2) or "").lower()
            title = m.group(4)
            skipped = (".skip" in modifier) or (".todo" in modifier)
            def credit(acs_here, reason_text, card):
                for nac in acs_here:
                    slot = cov.setdefault(nac, {"active": [], "skipped": []})
                    if skipped:
                        slot["skipped"].append((title, bool(reason_text), card))
                    else:
                        slot["active"].append((title, card))

            pm = PREFIX_RE.search(title)
            if not pm:
                # A table-driven title interpolates its AC id — resolve it from the table.
                dm = DYN_PREFIX_RE.search(title)
                if dm:
                    dyn = resolve_dynamic_acs(src, m.start(), dm.group(2))
                    if not dyn:
                        grammar.append(
                            f"{rel}: table-driven title interpolates ${{{dm.group(2)}}} but its AC ids "
                            f"could not be resolved — the loop must read `for (const X of TABLE)` with "
                            f"TABLE holding literal `{dm.group(2).partition('.')[2] or 'ac'}: \"AC-NNN\"` entries"
                        )
                        continue
                    dyn_card = card_of(dm.group(1))
                    file_cards.add(dyn_card)
                    credit({norm_ac(a) for a in dyn}, title[dm.end():].strip(), dyn_card)
                    continue
                # a test with no valid prefix — flag only if it looks like it meant to have one
                if AC_TOKEN_RE.search(title):
                    grammar.append(f"{rel}: test title references an AC but is not in [<CARD> - AC-NNN] form: {title!r}")
                    continue
                # No-AC mode: `[<CARD>] <desc>` still identifies its card.
                cm = CARD_ONLY_RE.match(title)
                if cm:
                    file_cards.add(card_of(cm.group(1)))
                continue
            card = card_of(pm.group(1))
            file_cards.add(card)
            # primary (from the prefix) + secondary (other AC tokens on the it() line)
            line = _phys_line(src, m.start())
            credit(
                {norm_ac(pm.group(2))} | {norm_ac(t) for t in AC_TOKEN_RE.findall(line)},
                (pm.group(3) + title[pm.end():]).strip(),
                card,
            )
        cards |= file_cards
        # Grammar problems belong to whoever owns the file (see docstring).
        foreign = bool(expected_card) and expected_card not in file_cards
        for msg in grammar:
            if foreign:
                note(f"{msg}  [another card's file — not counted against {expected_card}]")
            else:
                err(msg)
    return cov, cards, files


def foreign_ac_spans(text, expected_card):
    """Offsets of AC ids that belong to a card other than `expected_card` (see FOREIGN_LOOKBEHIND)."""
    if not expected_card:
        return set()
    spans = set()
    for m in AC_TOKEN_RE.finditer(text):
        line_start = text.rfind("\n", 0, m.start()) + 1
        window = text[max(line_start, m.start() - FOREIGN_LOOKBEHIND):m.start()]
        others = [c for c in CARD_TOKEN_RE.findall(window) if c.upper() != expected_card]
        if others:
            spans.add(m.start())
    return spans


def collect_acs(ac_path, expected_card=None):
    """AC ids (normalized → original-form) and declared deferrals from the design source(s).

    Returns (found, deferred) where deferred maps a normalized AC id to the reason given
    on its `Deferred-ACs:` line.
    """
    if os.path.isfile(ac_path):
        files = [ac_path]
    elif os.path.isdir(ac_path):
        files = sorted(
            f for f in glob.glob(os.path.join(ac_path, "**", "*"), recursive=True)
            if os.path.isfile(f) and f.rsplit(".", 1)[-1].lower() in ("md", "html", "htm", "txt", "yaml", "yml", "json")
        )
    else:
        err(f"ac-source {ac_path} is neither a file nor a directory")
        return {}, {}
    found = {}
    deferred = {}
    for fp in files:
        text = read_text(fp)
        foreign = foreign_ac_spans(text, expected_card)
        for m in AC_TOKEN_RE.finditer(text):
            if m.start() in foreign:
                continue
            found.setdefault(norm_ac(m.group()), m.group().upper())
        for dm in DEFERRED_RE.finditer(text):
            # ids come only from the list BEFORE the reason separator: the reason itself often
            # names other ACs ("AC-010 is not listed because …") and must not defer them.
            decl = dm.group(1)
            sep = re.search(r"—|--|;", decl)
            head = decl[:sep.start()] if sep else decl
            reason = decl[sep.end():].strip() if sep else ""
            ids = AC_TOKEN_RE.findall(head)
            if not ids:
                err(f"{os.path.relpath(fp)}: a Deferred-ACs line names no AC id")
                continue
            if not reason:
                err(f"{os.path.relpath(fp)}: Deferred-ACs {', '.join(ids)} states no reason — a deferral without a reason is a silently dropped AC")
            for tok in ids:
                deferred[norm_ac(tok)] = reason
    return found, deferred


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

    expected_card = (card_arg or "").upper() or None
    cov, cards, files = collect_specs(spec_path, expected_card)
    acs, deferred = collect_acs(ac_path, expected_card)

    # No-AC mode (SKILL.md): a task with no ACs has no coverage gate — title grammar and card
    # consistency are still checked, but there is nothing to cover, so this is not a failure.
    no_ac_mode = not acs
    if no_ac_mode:
        note(f"no AC ids (AC-<n>) in {ac_path} — No-AC mode: coverage gate is N/A, "
             f"title grammar still checked. If this task DOES have ACs, number them AC-001… first.")

    # card consistency
    if expected_card and cards and expected_card not in cards:
        err(f"--card {expected_card} not found in any spec title (saw: {', '.join(sorted(cards)) or 'none'})")
    if len(cards) > 1:
        note(f"specs mix multiple card ids: {', '.join(sorted(cards))}")

    # coverage rows. With --card, only that card's tests count: an AC-001 owned by another
    # card proves nothing about this one.
    def mine(entries):
        return [e for e in entries if not expected_card or e[-1] == expected_card]

    covered, skipped_only, uncovered, deferred_only = [], [], [], []
    for nac, orig in sorted(acs.items(), key=lambda kv: int(re.sub(r"\D", "", kv[0]) or 0)):
        slot = cov.get(nac) or {"active": [], "skipped": []}
        active, skips = mine(slot["active"]), mine(slot["skipped"])
        if active:
            covered.append(orig)
            if nac in deferred:
                note(f"{orig}: declared deferred but an active test covers it — un-defer it in the spec or drop the test")
        elif nac in deferred:
            deferred_only.append(orig)
        elif skips:
            skipped_only.append(orig)
            for _title, has_reason, _card in skips:
                if not has_reason:
                    err(f"{orig}: only an it.skip() with no reason — a non-HTTP-observable AC must state why in its title")
        else:
            uncovered.append(orig)
            err(f"{orig}: no e2e test — add an it(\"[<CARD> - {orig} ...]\") or, if not HTTP-observable, an it.skip() with a reason")

    # orphans: AC referenced by a spec but absent from the AC source. Meaningless in No-AC
    # mode — with no source, every AC in the suite would be "orphaned".
    for nac in sorted(cov) if not no_ac_mode else []:
        if nac not in acs:
            note(f"{cov.get(nac) and nac}: a spec references {nac} but it is not in the AC source — stale test or incomplete source?")

    # ---- report -----------------------------------------------------------
    if no_ac_mode:
        print(f"No-AC mode — coverage gate N/A.  specs scanned: {len(files)}")
    else:
        print("AC coverage:")
        print(f"  covered (active it):        {len(covered)}  {', '.join(covered)}")
        print(f"  declared non-observable:    {len(skipped_only)}  {', '.join(skipped_only)}  (it.skip — L2 validates the reason)")
        print(f"  declared deferred:          {len(deferred_only)}  {', '.join(deferred_only)}  (Deferred-ACs in the spec — L2 validates the reason)")
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
    if no_ac_mode:
        print("PASS — 0 error(s) (No-AC mode: title grammar clean, no coverage to gate)")
        return
    print(f"PASS — 0 error(s) ({len(covered)} AC covered, {len(skipped_only)} declared non-observable, {len(deferred_only)} deferred)")


if __name__ == "__main__":
    main()
