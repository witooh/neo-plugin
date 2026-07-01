#!/usr/bin/env python3
"""
docverify.py — cross-DOCUMENT semantic linter for the design-docs HTML site.
Zero install: pure Python 3 (stdlib only). Companion to lint.py.

WHY THIS EXISTS
  lint.py is per-FILE and STRUCTURAL (tag balance, unescaped < / &, .card missing
  status). docverify.py is cross-FILE and SEMANTIC: it resolves the references that
  span documents. That is the exact gap nothing else covers —
    • the browser's components.js derives summaries/matrices WITHIN one page only;
      it never sees a sibling file, so a <tc-card traces="AC-99"> that points at an
      AC which does not exist renders blank and ships silently;
    • single-pass author self-review (preamble §3) misses cross-reference drift
      (proven: an author cannot reliably catch their own dangling references).
  This script is the deterministic, independent check for that class.

WHAT IT CHECKS  (all read from the SOURCE HTML authoring tags <ac-card>/<tc-card>/
                 <ac>/<tc> — schema: references/html-output.md §5 + assets/js/components.js)

  acceptance-criteria.html (the AC doc):
    A1  <ac-card status> is present and exactly "ready" or "blocked"        -> ERROR
    A2  status="blocked" has a non-empty <blocker> child; "ready" has none  -> ERROR
    A3  <ac-card priority>, when present, is p0 | p1 | p2                    -> WARNING
    A4  AC ids are unique and match AC-<n>                                  -> ERROR
        (non-contiguous numbering is allowed — descope can leave gaps)      -> WARNING
    A5  every <ac-summary><ac ref> matches a real <ac-card id>, and every
        <ac-card> is listed once in <ac-summary> (no phantom / missing row;
        an absent summary is reported once, not once per uncovered card)   -> ERROR
    A6  no duplicate IDs within one card's own JIRA list (jira-ref.md §4)   -> WARNING

  test-cases.html (the test-case doc):  T1..T3 mirror A1/A2/A5 for <tc-card> (A3 priority
  + A6 JIRA-dup apply to TC too — the basics check is tag-agnostic); plus
    T4  <tc-deferred><tc ref> set == the set of blocked <tc-card> ids       -> ERROR
        (an absent <tc-deferred> with blocked TCs collapses to one error)

  cross-file AC <-> test cases  (only when BOTH docs exist):
    X1  every <tc-card traces> AC-id exists in the AC doc (no phantom trace)-> ERROR
    X2  every AC id is traced by >= 1 <tc-card> (coverage; Blocked ACs too) -> ERROR
    X3  a <tc-card> tracing ANY Blocked AC is itself status="blocked"       -> ERROR
        (ac-status.md §3 — a Blocked AC propagates @blocked to its TCs)
    X4  <tc-card jira> == the traced ACs' jira, inherited VERBATIM: the
        order-preserving dedup-union, same IDs / order / casing             -> ERROR
        (jira-ref.md §2/§4 — verbatim; never invented, dropped, or reordered)
    X5  every <ac-card traces> TC-id exists in the test-case doc            -> ERROR

  execution evidence  AC <-> test cases <-> test-report.html  (only when ALL THREE exist):
    X6  every READY AC is traced by >= 1 <tc-card> that PASSED              -> ERROR
        (data-status="ready" in test-report.html; ❌Fail / ⏸Deferred / absent
         do NOT satisfy it). Blocked ACs + their @blocked/deferred TCs are
         EXEMPT (X3/T4 — a deferred test is correctly not expected to pass);
         a READY AC with NO tracing TC is X2's coverage gap, not X6's. Closes
         "scoped-pass != feature-complete": a feature can no longer read DONE
         while a ready AC has no PASSING test run. (mapping: test-execution-report.md)

  every page in the folder  (callout discipline — html-output.md §5.1):
    C1  no version/changelog <callout-box> on a spec page (-> VERSION.md)   -> ERROR
        (start-anchored, or a mid-text version + a change-verb co-signal)
    C2  no doc-vs-code gap <callout-box> (-> gap-analysis.md + chat report) -> ERROR
    C3  <= 6 hand-authored callouts/page outside a <h2 id="notes"> region   -> WARNING
        (Notes-region callouts are exempt — that IS the correct home; a card's
         own <blocker> callout is element-emitted, not authored, so never counted)

  LEGACY (ac-status.md §1): if NO card in a doc carries a `status` at all, the doc
  predates the Status schema → every card is treated as Ready and A1/A2 are skipped
  (one WARNING). A *partial* status state (some cards have it, some don't) is a real
  defect and DOES fail A1 — backfill is required.

STAGE-AWARE
  Runs only the checks whose inputs are present and prints what was checked vs
  skipped, so a half-finished usecase folder (AC written, tests not yet) does not
  false-fail. QA — last in the BA->Architect->QA chain, with every doc present —
  is where the full cross-file set runs: downstream verifying upstream, mechanically.
  Once test-report.html also exists (QA's Dev-Loop execution), X6 additionally requires
  every ready AC to have a PASSING tracing test — the final, execution-evidence stage.

ROBUSTNESS
  Parsing is case-insensitive (the DOM lowercases custom-element names), quote-aware
  (single or double quotes; a literal `>` inside a quoted value does not truncate the
  tag), and comment/script/style/pre/code regions are stripped before matching (so a
  schema example or commented-out card is not parsed as live markup). A file that
  cannot be read, or any per-folder crash, is reported as that folder's error — it
  never aborts the whole run.

DELIBERATELY NOT CHECKED
  Architect's traceability.html (AC -> design element, GATE AR4) is hand-authored
  free-form with no stable custom-element schema to parse — a check there would be
  guesswork. It stays covered by AR4 + the downstream adversarial verify pass.
  The <trace-matrix> (AC->TC) derives from on-page <ac-card>s in the browser and is
  covered here at the source level by X1/X2/X5, and at the execution level by X6
  (a traced TC must actually PASS in test-report.html, not merely be authored).

USAGE
  python3 docverify.py DIR        # every usecase folder under DIR (recursive)
  python3 docverify.py USECASE/   # a single usecase folder
Exit code: 0 = clean (no ERROR), 1 = at least one ERROR.
"""
import re, sys, pathlib

AC_DOC = "acceptance-criteria.html"
TC_DOC = "test-cases.html"
REPORT_DOC = "test-report.html"


# ---- noise stripping (mirror lint.py: comments + script/style/pre/code are not live markup) ----

_NOISE_TAGS = ("script", "style", "pre", "code")


def strip_noise(html):
    html = re.sub(r"<!--.*?-->", "", html, flags=re.S)
    for t in _NOISE_TAGS:
        html = re.sub(r"(<" + t + r"\b[^>]*>).*?(</" + t + r"\s*>)",
                      lambda m: m.group(1) + m.group(2), html, flags=re.S | re.I)
    return html


def load(path):
    """Read a doc and strip noise — the single place the read policy lives, so the
       two call sites in check_usecase cannot drift (e.g. on errors='replace')."""
    return strip_noise(path.read_text(encoding="utf-8", errors="replace"))


# ---- tiny HTML helpers (regex-based, same spirit as lint.py — no parser dep) ----
# Case-insensitive on tag/attribute NAMES (HTML is); attribute VALUES are preserved
# verbatim (JIRA casing is part of the contract). Quote-aware so a `>` inside a
# quoted attribute value does not end the tag early.

_QUOTED_OR_NONGT = r'(?:"[^"]*"|\'[^\']*\'|[^>])*'


def attr(open_tag, name):
    """Value of name="..." / name='...' in an opening-tag string. None if absent."""
    m = re.search(r'\b' + re.escape(name) + r'\s*=\s*(?:"([^"]*)"|\'([^\']*)\')',
                  open_tag, re.I)
    if not m:
        return None
    return (m.group(1) if m.group(1) is not None else m.group(2)).strip()


def elements(html, tag):
    """Yield (open_tag_str, inner_html) for each <tag ...>...</tag>.
       (?=[\\s/>]) makes <ac> NOT match <ac-card>; case-insensitive; quote-aware."""
    out = []
    open_re = re.compile(r'<' + re.escape(tag) + r'(?=[\s/>])' + _QUOTED_OR_NONGT + r'>', re.I)
    close_re = re.compile(r'</' + re.escape(tag) + r'\s*>', re.I)
    for m in open_re.finditer(html):
        rest = html[m.end():]
        cm = close_re.search(rest)
        inner = rest[:cm.start()] if cm else ""
        out.append((m.group(0), inner))
    return out


def has_nonempty_child(inner, tag):
    m = re.search(r'<' + re.escape(tag) + r'(?=[\s>])' + _QUOTED_OR_NONGT + r'>(.*?)</'
                  + re.escape(tag) + r'\s*>', inner, re.S | re.I)
    if not m:
        return False
    return bool(re.sub(r'<[^>]+>', '', m.group(1)).strip())   # strip void/inline tags too


def split_ws(v):
    return [x for x in re.split(r'\s+', v.strip()) if x] if v else []


def split_csv(v):
    return [x.strip() for x in v.split(',') if x.strip()] if v else []


# ---- parsing the authoring tags into plain dicts ----

def parse_cards(html, tag):
    """tag = 'ac-card' or 'tc-card'."""
    cards = []
    for open_tag, inner in elements(html, tag):
        cards.append({
            "id":       attr(open_tag, "id"),
            "status":   (attr(open_tag, "status") or "").lower() or None,
            "priority": attr(open_tag, "priority"),
            "traces":   split_ws(attr(open_tag, "traces")),
            "jira":     split_csv(attr(open_tag, "jira")),
            "blocker":  has_nonempty_child(inner, "blocker"),
        })
    return cards


_CARD_DIV_RE = re.compile(r'<div\b' + _QUOTED_OR_NONGT + r'>', re.I)


def parse_report_results(html):
    """X6 input — test-report.html renders each TC result as a canonical .card div
       <div class="card" id="TC-NNN" data-status="ready|blocked|pending"> (mapping in
       test-execution-report.md: ✅Pass→ready, ❌Fail→blocked, ⏸Deferred/⚠️Blocked→
       pending). Returns {TC-id: data-status} for every .card div carrying an id.
       A NEW matcher, NOT parse_cards(): the report uses the EXPANDED .card div, not
       the <tc-card> authoring tag. Reuses attr(); the "card" split-token test mirrors
       lint.py so link-card / *-card are not mistaken for a result; strip_noise()
       upstream keeps a .card inside <pre>/<code>/comment from being read as live."""
    out = {}
    for m in _CARD_DIV_RE.finditer(html):
        open_tag = m.group(0)
        if "card" not in (attr(open_tag, "class") or "").split():
            continue
        tid = attr(open_tag, "id")
        if not tid:
            continue
        out[tid] = (attr(open_tag, "data-status") or "").lower() or None
    return out


def parse_refs(html, parent_tag):
    """Refs of the <ac>/<tc> child rows inside a <parent_tag> block (scoped, so a
       bare <ac>/<tc> outside a summary is never picked up)."""
    refs = []
    child = "ac" if parent_tag == "ac-summary" else "tc"
    for _, inner in elements(html, parent_tag):
        for open_tag, _ in elements(inner, child):
            r = attr(open_tag, "ref")
            if r:
                refs.append(r)
    return refs


def parse_callouts(html):
    """Each hand-authored <callout-box ...>inner</callout-box> as {kind, text}.
       text = inner with tags stripped + whitespace-collapsed — enough for the
       body-start (version) + keyword (gap) matching in classify_callout(). A card's
       own <blocker> callout is emitted by components.js (never authored as a
       <callout-box>), so it is correctly invisible here. Reuses elements()/attr()."""
    out = []
    for open_tag, inner in elements(html, "callout-box"):
        text = re.sub(r'<[^>]+>', ' ', inner)            # drop inline <b>/<code>/<a>/…
        text = re.sub(r'\s+', ' ', text).strip()
        out.append({"kind": (attr(open_tag, "kind") or "").lower(), "text": text})
    return out


# ---- checks ----

ID_RE = {"ac-card": re.compile(r'^AC-\d+$'), "tc-card": re.compile(r'^TC-\d+$')}


def _dupes(seq):
    seen, dup = set(), set()
    for x in seq:
        if x in seen:
            dup.add(x)
        seen.add(x)
    return dup


def _id_span(ids):
    """Compact 'AC-001..AC-015' for a set of AC-/TC-style ids (single id, or a sorted
       list when ids don't share the <prefix>-<number> shape) — lets an entirely
       missing summary/deferred table report one readable span, not one error per card."""
    good = sorted((i for i in ids if i and re.match(r'^[A-Za-z]+-\d+$', i)),
                  key=lambda x: int(x.split("-")[1]))
    if not good:
        return ", ".join(sorted(ids))
    return good[0] if len(good) == 1 else f"{good[0]}..{good[-1]}"


def check_card_basics(cards, tag, errors, warns):
    """A1/A2/A4/A6 (ac) and T1/T2 (tc) — status enum, blocker presence, id format,
       JIRA self-dup. Honors the legacy 'no status anywhere → all Ready' rule."""
    kind = "AC" if tag == "ac-card" else "TC"
    legacy = bool(cards) and not any(c["status"] for c in cards)
    if legacy:
        warns.append(f"{kind} doc carries no status on any card — treating all as Ready "
                     f"(legacy doc, ac-status.md §1); backfill Status to silence this")
    ids = []
    for c in cards:
        cid = c["id"] or f"<{tag} with no id>"
        ids.append(c["id"])
        if not legacy:
            if c["status"] not in ("ready", "blocked"):
                errors.append(f'{cid}: status must be "ready" or "blocked" '
                              f'(found {c["status"]!r})')
            if c["status"] == "blocked" and not c["blocker"]:
                errors.append(f"{cid}: status=blocked but has no non-empty <blocker> child")
            if c["status"] == "ready" and c["blocker"]:
                errors.append(f"{cid}: status=ready must not carry a <blocker> child")
        if c["priority"] and c["priority"].lower() not in ("p0", "p1", "p2"):
            warns.append(f'{cid}: priority {c["priority"]!r} is not p0/p1/p2')
        if c["id"] and not ID_RE[tag].match(c["id"]):
            errors.append(f'{cid}: id does not match {kind}-<number>')
        if len(c["jira"]) != len(set(c["jira"])):
            warns.append(f'{cid}: JIRA Ref {c["jira"]} has duplicate IDs (dedupe — jira-ref.md §4)')
    for d in sorted(_dupes([i for i in ids if i])):
        errors.append(f"{d}: duplicate {kind} id")
    nums = sorted(int(i.split("-")[1]) for i in ids if i and ID_RE[tag].match(i))
    if nums:
        missing = [n for n in range(nums[0], nums[-1] + 1) if n not in nums]
        if missing:
            warns.append(f"{kind} numbering has gaps at "
                         f"{', '.join(f'{kind}-{n:03d}' for n in missing)} "
                         f"(ok if intentionally descoped)")


def check_summary_pairs(card_ids, refs, kind, errors):
    """A5 / T3 — summary rows and cards must be the same set (no phantom / missing).
       When the summary lists NO rows at all (table absent or empty) the gap is one
       structural fact, so it is reported once — not once per uncovered card."""
    cset, rset = set(card_ids), set(refs)
    if cset and not rset:
        errors.append(f"no <{kind}-summary> rows found — {len(cset)} {kind.upper()} "
                      f"card(s) uncovered ({_id_span(cset)})")
        return
    for r in sorted(rset - cset):
        errors.append(f"{r}: <{kind}-summary> row references no <{kind}-card> on the page")
    for c in sorted(cset - rset):
        errors.append(f"{c}: <{kind}-card> is missing from the <{kind}-summary> table")
    for d in sorted(_dupes(refs)):
        errors.append(f"{d}: listed more than once in <{kind}-summary>")


def check_cross(ac_cards, tc_cards, errors):
    """X1..X5 — cross-file AC <-> test-case resolution."""
    ac_by_id = {c["id"]: c for c in ac_cards if c["id"]}
    tc_ids = {c["id"] for c in tc_cards if c["id"]}
    ac_ids = set(ac_by_id)
    blocked_ac = {i for i, c in ac_by_id.items() if c["status"] == "blocked"}

    traced_acs = set()
    for tc in tc_cards:
        tid = tc["id"] or "<tc-card with no id>"
        existing = []
        for ac in tc["traces"]:                                   # X1 — phantom AC trace
            if ac in ac_ids:
                existing.append(ac)
                traced_acs.add(ac)
            else:
                errors.append(f"{tid}: traces {ac} which is not an AC in {AC_DOC}")
        if any(ac in blocked_ac for ac in existing) and tc["status"] != "blocked":   # X3
            hit = ", ".join(ac for ac in existing if ac in blocked_ac)
            errors.append(f"{tid}: traces Blocked AC ({hit}) but TC status is "
                          f"{tc['status']!r}, not blocked")
        expected = []                                             # X4 — verbatim, order-preserving
        for ac in existing:
            for j in ac_by_id[ac]["jira"]:
                if j not in expected:
                    expected.append(j)
        if tc["jira"] != expected:
            errors.append(f"{tid}: JIRA Ref {tc['jira'] or '(none)'} != inherited "
                          f"{expected or '(none)'} from {', '.join(existing) or 'its ACs'} "
                          f"(verbatim, same order — jira-ref.md §2)")

    for ac in sorted(ac_ids - traced_acs):                        # X2 — coverage
        errors.append(f"{ac}: no test case traces it (coverage gap)")

    for ac in ac_cards:                                           # X5 — phantom AC->TC trace
        for tc in ac["traces"]:
            if tc not in tc_ids:
                errors.append(f"{ac['id']}: traces {tc} which is not a TC in {TC_DOC}")


def check_execution(ac_cards, tc_cards, results, errors):
    """X6 — execution evidence: every READY AC must be traced by >= 1 test case that
       PASSED (data-status="ready") in test-report.html. Closes "scoped-pass !=
       feature-complete": a feature can no longer read DONE while a ready AC has no
       PASSING test run. EXEMPT: Blocked ACs + their @blocked/deferred TCs (X3/T4 — a
       deferred test is correctly not expected to pass), so iterate ready ACs only. An
       AC with NO tracing TC is X2's coverage gap, not X6's (skip — no double report).
       `results` = {TC-id: data-status} from parse_report_results(); a legacy AC doc
       (no status anywhere) treats every AC as ready, mirroring check_card_basics.
       check_usecase runs this ONLY when test-report.html exists (stage-aware), so the
       pre-report phases never false-fail. Per-usecase like X1/X2/X5 — an AC whose
       tests live in another usecase folder is out of scope (locality assumption)."""
    ac_by_id = {c["id"]: c for c in ac_cards if c["id"]}
    legacy = bool(ac_cards) and not any(c["status"] for c in ac_cards)
    ready_ac = {i for i, c in ac_by_id.items()
                if c["status"] == "ready" or (legacy and c["status"] != "blocked")}

    tracing = {}                                                  # ready AC -> [tracing TC ids]
    for tc in tc_cards:
        tid = tc["id"] or "<tc-card with no id>"
        for ac in tc["traces"]:
            if ac in ready_ac:
                tracing.setdefault(ac, []).append(tid)

    human = {"ready": "Pass", "blocked": "Fail", "pending": "Deferred/Blocked"}
    for ac in sorted(ready_ac):                                   # X6
        tcs = sorted(tracing.get(ac, []))
        if not tcs:                                               # X2 owns "no tracing TC"
            continue
        if any(results.get(t) == "ready" for t in tcs):          # >= 1 tracing TC passed → covered
            continue
        if all(t not in results for t in tcs):                    # case (b) — none executed
            errors.append(f"{ac}: tracing test case(s) {', '.join(tcs)} absent from "
                          f"{REPORT_DOC} — no execution evidence")
        else:                                                     # case (a) — ran, none passed
            res = ", ".join((f"{t}={results[t]}({human.get(results[t], results[t] or 'no-status')})"
                             if t in results else f"{t}=absent") for t in tcs)
            errors.append(f"{ac}: no tracing test case PASSED in {REPORT_DOC} "
                          f"(traced by {', '.join(tcs)}; results: {res}) — feature not proven complete")


# ---- callout discipline (html-output.md §5.1): a spec page = current desired state.
#      version/changelog + doc-vs-code gap notes must NOT live in a <callout-box> on the
#      page — they belong in VERSION.md / gap-analysis.md. Run on EVERY page in the folder
#      (traceability/index too), not just the card docs. ----

DENSITY_CAP = 6                                                 # non-exempt callouts/page → warn
_SEMVER = r'\d+\.\d+(?:\.\d+)?'                                 # X.Y[.Z] — shared by both version detectors
VERSION_RE = re.compile(r'^\s*v?' + _SEMVER + r'\b', re.I)     # body STARTS with an (optional-v) semver token
GAP_PHRASES = ("doc-vs-code", "doc vs code", "code-compliance gap", "compliance gap",
               "plumbing gap", "rate plumbing", "implementation gap", "not yet implement",
               "not implemented", "re-align", "realign", "supersede")  # substrings → also -ed/-ment/-ing, supersedes/-d
# words that ALSO occur in legit spec prose ("cache is stale", "data drift between regions")
# — a gap only WITH a code-pointer co-signal (CODE_SIGNAL), never on their own:
GAP_WEAK = ("gap", "plumbing", "verified", "migration", "drift", "stale")
CODE_SIGNAL = re.compile(r'\b(code|grep|adapter|port|handler|implement)\b', re.I)
# mid-text version + change-verb co-signal (mirrors the GAP_WEAK tier). VERSION_MIDTEXT
# REQUIRES the "v" prefix (+ a dot) so "Base 0.5%" / bare "v2" / "API v2.0" never match alone.
VERSION_MIDTEXT = re.compile(r'\bv' + _SEMVER + r'\b', re.I)
CHANGE_VERB = re.compile(r'\b(closed|added|removed|refined|revised|clarified|promoted|'
                         r'demoted|deprecated|introduced|renamed|resolved|bumped|'
                         r'released|superseded|reverted)\b', re.I)


def classify_callout(text):
    """'version' | 'gap' | 'ok'. A start-anchored version wins outright. 'gap' needs a STRONG
       phrase, or a WEAK word AND a code-pointer co-signal — so a legit spec note ("…verified
       against GetProductResponse") stays 'ok', but "plumbing gap … port" is a gap. A mid-text
       version is changelog only WITH a change-verb co-signal (so "…CLOSED v1.5.1…" flags, but
       a bare "v2" / "API v2.0" with no verb stays 'ok'). Tuned to the real corpus; widen
       GAP_PHRASES as new docs surface."""
    if VERSION_RE.match(text):
        return "version"
    low = text.lower()
    if any(p in low for p in GAP_PHRASES):
        return "gap"
    if any(re.search(r'\b' + re.escape(w) + r'\b', low) for w in GAP_WEAK) and CODE_SIGNAL.search(low):
        return "gap"
    if VERSION_MIDTEXT.search(low) and CHANGE_VERB.search(low):
        return "version"
    return "ok"


def split_at_notes(html):
    """(pre, notes_region) split at the first <h2|section id="notes">. Callouts inside the
       Notes region are EXEMPT — a cross-cutting note placed there IS the correct routing."""
    m = re.search(r'<(?:h2|section)\b[^>]*\bid\s*=\s*["\']notes["\']', html, re.I)
    return (html, "") if not m else (html[:m.start()], html[m.start():])


def check_callouts(html, fname, errors, warns):
    """C1/C2 version+gap callouts on a spec page -> ERROR; C3 density -> WARNING.
       The Notes region (split_at_notes) is exempt from all three."""
    pre, _notes = split_at_notes(html)
    live = 0
    for c in parse_callouts(pre):
        kind = classify_callout(c["text"])
        if kind == "ok":
            live += 1
            continue
        snip = (c["text"][:60] + "…") if len(c["text"]) > 60 else c["text"]
        if kind == "version":
            errors.append(f'{fname}: version/changelog callout on a spec page — move it to '
                          f'VERSION.md + the index.html version table (starts "{snip}")')
        else:                                              # gap
            errors.append(f'{fname}: doc-vs-code gap callout on a spec page — move it to '
                          f'gap-analysis.md + report it in the chat response (starts "{snip}")')
    if live > DENSITY_CAP:
        warns.append(f'{fname}: {live} hand-authored callouts (cap {DENSITY_CAP}) — fold '
                     f'element-specific notes into their section, cross-cutting ones into a '
                     f'single <h2 id="notes"> section (html-output.md §5.1)')


def check_usecase(folder):
    errors, warns, checked, skipped = [], [], [], []
    ac_path, tc_path = folder / AC_DOC, folder / TC_DOC

    ac_cards = tc_cards = None
    loaded = {}                                           # stash for the callout pass — no re-read
    if ac_path.exists():
        html = load(ac_path)
        loaded[AC_DOC] = html
        ac_cards = parse_cards(html, "ac-card")
        check_card_basics(ac_cards, "ac-card", errors, warns)
        check_summary_pairs([c["id"] for c in ac_cards if c["id"]],
                            parse_refs(html, "ac-summary"), "ac", errors)
        checked.append(AC_DOC)
    else:
        skipped.append(AC_DOC)

    if tc_path.exists():
        html = load(tc_path)
        loaded[TC_DOC] = html
        tc_cards = parse_cards(html, "tc-card")
        check_card_basics(tc_cards, "tc-card", errors, warns)
        check_summary_pairs([c["id"] for c in tc_cards if c["id"]],
                            parse_refs(html, "tc-summary"), "tc", errors)
        deferred = set(parse_refs(html, "tc-deferred"))           # T4
        blocked = {c["id"] for c in tc_cards if c["status"] == "blocked" and c["id"]}
        if blocked and not deferred:                              # whole table absent → one error
            errors.append(f"no <tc-deferred> rows found — {len(blocked)} blocked TC(s) "
                          f"not deferred ({_id_span(blocked)})")
        else:
            for x in sorted(blocked - deferred):
                errors.append(f"{x}: blocked TC missing from <tc-deferred> table")
            for x in sorted(deferred - blocked):
                errors.append(f"{x}: listed in <tc-deferred> but is not a blocked <tc-card>")
        checked.append(TC_DOC)
    else:
        skipped.append(TC_DOC)

    report_results = None
    report_path = folder / REPORT_DOC
    if report_path.exists():
        html = load(report_path)
        loaded[REPORT_DOC] = html                                 # stash for the callout pass — no re-read
        report_results = parse_report_results(html)

    if ac_cards is not None and tc_cards is not None:
        check_cross(ac_cards, tc_cards, errors)
        checked.append("cross-file AC<->TC")
        if report_results is not None:                            # X6 — execution evidence (stage-aware)
            check_execution(ac_cards, tc_cards, report_results, errors)
            checked.append("execution evidence AC<->TC<->report")
        else:
            skipped.append("execution evidence AC<->TC<->report (test-report.html absent)")
    elif ac_cards is not None:
        skipped.append("cross-file AC<->TC (test-cases.html absent)")
        if report_path.exists():
            skipped.append("execution evidence AC<->TC<->report (test-cases.html absent)")

    # callout discipline — EVERY page in the folder (traceability/index too,
    # which the card-based checks above never open). Skips _shell/_partials.
    pages = [p for p in sorted(folder.glob("*.html")) if not p.name.startswith("_")]
    for page in pages:
        try:
            check_callouts(loaded.get(page.name) or load(page), page.name, errors, warns)
        except Exception as e:
            errors.append(f"{page.name}: callout check failed ({e!r})")
    if pages:
        checked.append(f"callout discipline ({len(pages)} page(s))")

    return errors, warns, checked, skipped


def main():
    roots = [pathlib.Path(a) for a in sys.argv[1:]] or [pathlib.Path(".")]
    folders = set()
    for r in roots:
        if r.is_dir():
            for name in (AC_DOC, TC_DOC):
                for f in r.rglob(name):
                    folders.add(f.parent)
        elif r.name in (AC_DOC, TC_DOC):
            folders.add(r.parent)

    if not folders:
        print("docverify: no acceptance-criteria.html / test-cases.html found — nothing to check")
        sys.exit(0)

    total_err = 0
    for folder in sorted(folders):
        try:
            errs, warns, checked, skipped = check_usecase(folder)
        except Exception as e:                                    # one bad folder can't blank the run
            errs, warns, checked, skipped = [f"docverify crashed on this folder: {e!r}"], [], [], []
        total_err += len(errs)
        mark = "✗" if errs else "✓"
        head = "FAIL" if errs else "OK"
        print(f"{mark} {str(folder):46} {head}"
              + (f" / {len(warns)} warn" if warns else ""))
        print(f"    checked: {', '.join(checked) or '—'}"
              + (f"  |  skipped: {', '.join(skipped)}" if skipped else ""))
        for e in errs:
            print(f"    ERROR  {e}")
        for w in warns:
            print(f"    warn   {w}")

    print(f"\n{'FAILED' if total_err else 'PASS'} — {total_err} error(s) "
          f"across {len(folders)} usecase folder(s)")
    sys.exit(1 if total_err else 0)


if __name__ == "__main__":
    main()
