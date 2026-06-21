#!/usr/bin/env python3
"""
pubcheck.py — TRIPWIRE for `confluence-api-doc`: Confluence storage-XHTML validation.
Zero install: pure Python 3 (stdlib only). Companion to the confluence-api-doc skill —
Layer 1a (pre-flight, before any push) + the `--roundtrip` comparator (Layer 1b).

WHY THIS EXISTS
  The publish path assembles each page from the `docs/api/*.yaml` api-spec and converts its
  markdown into Confluence *storage* XHTML and POSTs it. A malformed conversion (a dropped `]]>`, an unbalanced `<td>`,
  a leaked `<` ) can still return HTTP 200 and leave a *broken page*. REST status is
  not evidence the page is right. This script is the deterministic measure of what a
  machine can check about the storage BEFORE it ships, and a canonical comparator that
  confirms what Confluence stored matches what we sent.

PHILOSOPHY: TRIPWIRE, NOT GROUND TRUTH (same as colcheck.py)
  • ERROR = a confident defect (storage won't parse, unbalanced table/list/CDATA, a
            bare unescaped `<`/`&`, a source table that vanished from the storage).
            The agent confirms + fixes the conversion, re-stages, re-runs.
  • NOTE  = something to eyeball but not fail on. Ends in "needs fresh-eyes".

TWO MODES
  1. Pre-flight (default):  python3 pubcheck.py <staged-dir>
     Validates every page artifact in the dir BEFORE pushing. Two artifact shapes:
       • `*.json` manifest  {"title": str, "source": "<markdown>", "storage": "<xhtml>"}
         → full check incl. C8 source↔storage element-count cross-check.
       • `*.xml` / `*.html` raw storage → C1-C6 only (no title / no source for C8).
  2. Round-trip:  python3 pubcheck.py --roundtrip <expected-file> <actual-file>
     Canonicalizes both storage strings (drops volatile attrs Confluence injects on
     store — ac:macro-id / ac:schema-version / ac:local-id — sorts attrs, collapses
     inter-tag whitespace) and reports real drift. CDATA payloads are compared EXACTLY
     (code content must survive verbatim). Confluence rewrites storage on store, so a
     naive byte compare is useless; canonicalization is what makes the diff meaningful.

CHECKS (pre-flight)
  C1 well-formedness  storage parses as XML (HTML entities neutralized first)   ERROR
  C2 CDATA balance    every `<![CDATA[` has a matching `]]>`                     ERROR
  C3 code-macro       each code structured-macro has a plain-text-body + CDATA   ERROR/NOTE
  C4 table balance    <table>/<tr>/<td|th> balanced; no empty <tr>              ERROR
  C5 list balance     <ul>/<ol>/<li> balanced                                   ERROR
  C6 entities         no bare `&` or `<` outside CDATA                          ERROR
  C7 title            manifest title non-empty                                  ERROR
  C8 count crosscheck source markdown tables/code-blocks ≤ storage equivalents  ERROR

Exit code: 0 = no ERROR / no drift, 1 = at least one ERROR / drift.
"""
import re, sys, json, pathlib, html.entities
from xml.dom import minidom
from collections import defaultdict

VOLATILE_ATTRS = {'ac:macro-id', 'ac:schema-version', 'ac:local-id'}
RE_CDATA = re.compile(r'<!\[CDATA\[(.*?)\]\]>', re.S)
# A bare `&` not starting a valid entity (&amp; &#60; &#xA9; &mdash; …).
RE_BAD_AMP = re.compile(r'&(?!#\d+;|#x[0-9A-Fa-f]+;|[A-Za-z][A-Za-z0-9]*;)')
# A bare `<` not starting a tag / close-tag / comment / declaration.
RE_BAD_LT = re.compile(r'<(?![A-Za-z/!?])')
RE_NAMED_ENTITY = re.compile(r'&([A-Za-z][A-Za-z0-9]*);')


# ───────────────────────── storage helpers ─────────────────────────

def xmlsafe_entities(s):
    """Replace named HTML entities (&mdash; &rarr; &nbsp; …) with numeric refs so a
       vanilla XML parser accepts real Confluence storage. The 5 XML-predefined names
       are left as-is. Numeric refs and unknown names are untouched."""
    def repl(m):
        name = m.group(1)
        if name in ('amp', 'lt', 'gt', 'quot', 'apos'):
            return m.group(0)
        cp = html.entities.name2codepoint.get(name)
        return f'&#{cp};' if cp else m.group(0)
    return RE_NAMED_ENTITY.sub(repl, s)


def strip_cdata(s):
    return RE_CDATA.sub('', s)


def extract_cdata(s):
    return RE_CDATA.findall(s)


def parse_storage(storage):
    """Parse a storage fragment into a DOM (wrapped in a namespaced root). Raises on
       malformed input. Named HTML entities are neutralized first."""
    wrapped = ('<root xmlns:ac="urn:ac" xmlns:ri="urn:ri">'
               + xmlsafe_entities(storage) + '</root>')
    return minidom.parseString(wrapped)


def _canon(node, out):
    nt = node.nodeType
    if nt == node.ELEMENT_NODE:
        attrs = []
        if node.attributes:
            for i in range(node.attributes.length):
                a = node.attributes.item(i)
                if a.name in VOLATILE_ATTRS:
                    continue
                attrs.append((a.name, a.value))
        attrs.sort()
        out.append('<' + node.tagName + ''.join(f' {k}="{v}"' for k, v in attrs) + '>')
        for ch in node.childNodes:
            _canon(ch, out)
        out.append('</' + node.tagName + '>')
    elif nt == node.CDATA_SECTION_NODE:
        out.append('<![CDATA[' + node.data + ']]>')          # exact — code must survive
    elif nt == node.TEXT_NODE:
        t = re.sub(r'\s+', ' ', node.data.strip())
        if t:
            out.append(t)


def canonicalize(storage):
    """Canonical form of a storage fragment for round-trip comparison: volatile attrs
       dropped, attrs sorted, inter-tag whitespace collapsed, CDATA preserved exactly."""
    dom = parse_storage(storage)
    out = []
    for ch in dom.documentElement.childNodes:
        _canon(ch, out)
    return ''.join(out)


def _count(tag, s):
    return (len(re.findall(rf'<{tag}\b', s)), len(re.findall(rf'</{tag}>', s)))


# ───────────────────────── pre-flight checks ─────────────────────────

def check_page(label, title, source, storage, errors, notes):
    """Validate one converted page's storage XHTML. title/source may be None (raw mode)."""
    # C2 — CDATA balance
    opens, closes = storage.count('<![CDATA['), storage.count(']]>')
    if opens != closes:
        errors.append((label, 'ERROR', f'CDATA unbalanced: {opens} "<![CDATA[" vs {closes} "]]>"'))

    # C3 — code-macro integrity
    n_macros = len(re.findall(r'<ac:structured-macro\s+ac:name="code"', storage))
    n_bodies = len(re.findall(r'<ac:plain-text-body>', storage))
    if n_macros > n_bodies:
        errors.append((label, 'ERROR', f'{n_macros} code macro(s) but only {n_bodies} '
                                       f'<ac:plain-text-body> — a body is missing'))
    n_body_cdata = len(re.findall(r'<ac:plain-text-body>\s*<!\[CDATA\[', storage))
    if n_bodies > n_body_cdata:
        notes.append((label, f'{n_bodies - n_body_cdata} code body/ies not wrapped in CDATA '
                             f'— verify the code content is intact; needs fresh-eyes'))

    # C4 — table balance
    for tag in ('table', 'tr'):
        o, c = _count(tag, storage)
        if o != c:
            errors.append((label, 'ERROR', f'<{tag}> unbalanced: {o} open vs {c} close'))
    cells = len(re.findall(r'<td\b', storage)) + len(re.findall(r'<th\b', storage))
    rows = len(re.findall(r'<tr\b', storage))
    for tr in re.findall(r'<tr\b.*?</tr>', storage, re.S):
        if '<td' not in tr and '<th' not in tr:
            errors.append((label, 'ERROR', 'a <tr> has no <td>/<th> cell (empty row)'))
    if rows and cells < rows:
        notes.append((label, f'{rows} <tr> but only {cells} cells — possible dropped cell; '
                             f'needs fresh-eyes'))

    # C5 — list balance
    for tag in ('ul', 'ol', 'li'):
        o, c = _count(tag, storage)
        if o != c:
            errors.append((label, 'ERROR', f'<{tag}> unbalanced: {o} open vs {c} close'))

    # C6 — unescaped & / < outside CDATA
    bare = strip_cdata(storage)
    if RE_BAD_AMP.search(bare):
        n = len(RE_BAD_AMP.findall(bare))
        errors.append((label, 'ERROR', f'{n} bare "&" not part of a valid entity (escape as &amp;)'))
    if RE_BAD_LT.search(bare):
        n = len(RE_BAD_LT.findall(bare))
        errors.append((label, 'ERROR', f'{n} bare "<" not starting a tag (escape as &lt;)'))

    # C7 — title
    if title is not None and not str(title).strip():
        errors.append((label, 'ERROR', 'page title is empty'))

    # C1 — well-formedness (last: C2/C6 issues explain a parse failure)
    try:
        parse_storage(storage)
    except Exception as e:
        msg = re.sub(r'\s+', ' ', str(e))[:120]
        errors.append((label, 'ERROR', f'storage is not well-formed XML ({msg})'))

    # C8 — source↔storage element-count cross-check (manifest mode only)
    if source is not None:
        md_tables = _count_md_tables(source)
        st_tables = len(re.findall(r'<table\b', storage))
        if md_tables > st_tables:
            errors.append((label, 'ERROR', f'source has {md_tables} markdown table(s) but storage '
                                           f'has {st_tables} <table> — a table was dropped/garbled'))
        md_code = source.count('```') // 2
        st_code = len(re.findall(r'<ac:structured-macro\s+ac:name="code"', storage))
        if md_code > st_code:
            errors.append((label, 'ERROR', f'source has {md_code} code block(s) but storage has '
                                           f'{st_code} code macro(s) — a code block was dropped'))
    elif title is not None:
        notes.append((label, 'no source markdown in manifest — element-count cross-check (C8) '
                             'skipped; needs fresh-eyes'))


def _count_md_tables(md):
    """Count markdown tables = a header row (| … |) immediately followed by a separator
       row (|---|)."""
    lines, n, i = md.splitlines(), 0, 0
    while i < len(lines) - 1:
        if lines[i].strip().startswith('|') and re.match(r'^\|[\s:|-]+\|?\s*$', lines[i + 1].strip()):
            n += 1
            i += 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                i += 1
        else:
            i += 1
    return n


# ───────────────────────── round-trip ─────────────────────────

def roundtrip(expected_path, actual_path, errors, notes):
    """Compare what we pushed (expected) to what Confluence stored (actual) after
       canonicalization. CDATA payloads must match exactly; structural drift is reported
       for the agent to judge (Confluence may rewrite benignly in ways canon misses)."""
    label = f'{expected_path.name} ↔ {actual_path.name}'
    exp = expected_path.read_text(encoding='utf-8', errors='replace')
    act = actual_path.read_text(encoding='utf-8', errors='replace')

    ce = ca = None
    try:
        ce = canonicalize(exp)
    except Exception as e:
        errors.append((label, 'ERROR', f'expected storage will not parse ({str(e)[:80]})'))
    try:
        ca = canonicalize(act)
    except Exception as e:
        errors.append((label, 'ERROR', f'actual (re-fetched) storage will not parse ({str(e)[:80]})'))
    if ce is None or ca is None:
        return

    # CDATA payloads — exact (code content)
    if extract_cdata(exp) != extract_cdata(act):
        errors.append((label, 'ERROR', 'CDATA (code-block) content differs after round-trip '
                                       '— a code example was altered on store'))

    if ce == ca:
        return  # clean

    # Find first divergence and show a small window each side.
    i = 0
    while i < min(len(ce), len(ca)) and ce[i] == ca[i]:
        i += 1
    lo = max(0, i - 30)
    errors.append((label, 'ERROR', 'structural drift after round-trip (review — Confluence may '
                                   'rewrite benignly):'))
    notes.append((label, f'  expected …{ce[lo:i + 50]!r}'))
    notes.append((label, f'  actual   …{ca[lo:i + 50]!r}'))


# ───────────────────────── main ─────────────────────────

def collect(target):
    if target.is_file():
        return [target]
    out = []
    for ext in ('*.json', '*.xml', '*.html'):
        out.extend(sorted(target.glob(ext)))
    return out


def _bucket():
    return {'ERROR': [], 'NOTE': []}


def load_page(path):
    """(title, source, storage) for one artifact. .json = manifest; .xml/.html = raw."""
    text = path.read_text(encoding='utf-8', errors='replace')
    if path.suffix == '.json':
        d = json.loads(text)
        return d.get('title'), d.get('source'), d.get('storage', '')
    return None, None, text


def report_and_exit(errors, notes, n_items, unit):
    by_file = defaultdict(_bucket)
    for fname, _lvl, msg in errors:
        by_file[fname]['ERROR'].append(msg)
    for fname, msg in notes:
        by_file[fname]['NOTE'].append(msg)
    for fname in sorted(by_file):
        rec = by_file[fname]
        errs, nts = rec['ERROR'], rec['NOTE']
        status = f'{len(errs)} ERROR' if errs else 'OK'
        extra = f' / {len(nts)} note' if nts else ''
        print(f"{'✗' if errs else '✓'} {fname:46} {status}{extra}")
        for e in errs:
            print(f"    ERROR  {e}")
        for n in nts:
            print(f"    NOTE   {n}")
    total = len(errors)
    print(f"\n{'FAILED' if total else 'PASS'} — {total} error(s) / {len(notes)} note(s) "
          f"across {n_items} {unit}")
    sys.exit(1 if total else 0)


def main():
    argv = sys.argv[1:]
    errors, notes = [], []

    if argv and argv[0] == '--roundtrip':
        rest = argv[1:]
        if len(rest) != 2:
            print("usage: pubcheck.py --roundtrip <expected-file> <actual-file>")
            sys.exit(2)
        exp, act = pathlib.Path(rest[0]), pathlib.Path(rest[1])
        if not exp.exists() or not act.exists():
            print("pubcheck: expected/actual file not found")
            sys.exit(2)
        roundtrip(exp, act, errors, notes)
        report_and_exit(errors, notes, 1, 'page pair')
        return

    positional = [a for a in argv if not a.startswith('--')]
    target = pathlib.Path(positional[0]) if positional else pathlib.Path('.api-doc-publish')
    if not target.exists():
        print(f"pubcheck: {target} not found — nothing to check")
        sys.exit(0)

    pages = collect(target)
    if not pages:
        print("pubcheck: no .json/.xml/.html page artifacts — nothing to check")
        sys.exit(0)

    for p in pages:
        label = p.name
        try:
            title, source, storage = load_page(p)
        except Exception as e:
            errors.append((label, 'ERROR', f'cannot read page artifact ({e!r})'))
            continue
        if not storage:
            errors.append((label, 'ERROR', 'no storage content in artifact'))
            continue
        check_page(label, title, source, storage, errors, notes)

    report_and_exit(errors, notes, len(pages), 'page(s)')


if __name__ == '__main__':
    main()
