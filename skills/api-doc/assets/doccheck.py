#!/usr/bin/env python3
"""
doccheck.py — TRIPWIRE cross-checker for api-doc output (docs/api/ vs Go code).
Zero install: pure Python 3 (stdlib only). Companion to the api-doc skill's Step 4.

WHY THIS EXISTS
  api-doc's old verify was a single-agent self-check: the same agent that wrote
  the doc re-read the source and judged itself. The blind-spot is structural — an
  agent that miscounted fields while writing tends to miscount them again while
  checking. This script is the DETERMINISTIC, independent measure of the things a
  machine CAN count, so "verify passed" rests on evidence, not on the writer's
  confidence (the same principle neo's lint.py/docverify.py encode for HTML docs).

PHILOSOPHY: TRIPWIRE, NOT GROUND TRUTH
  Regex cannot parse Go as well as a compiler. So this script does NOT decide a doc
  is wrong — it RAISES A SIGNAL for a human/agent to inspect:
    • ERROR  = a mismatch the script is confident about (broken link, struct field
               with no doc row, a bool typed M). The agent confirms each before
               fixing; a genuine false positive is skipped + noted, never blindly
               "fixed". The agent loops until ERRORs clear OR ~3 rounds stall.
    • NOTE   = something the script deliberately CANNOT verify confidently (error-row
               tracing, step counting, custom-type enums, response wrappers, a struct
               it could not match with confidence). Never silently skipped — printed
               so the Layer-2 fresh-eyes verifier knows where to look. Each NOTE line
               ends in "needs fresh-eyes"; NOTEs never fail the run.

  To stay a tripwire (no false ERROR on a correct doc), every uncertain case
  DEGRADES to a NOTE rather than an ERROR: an unmatched / ambiguous / loose struct
  match, a duplicate struct name, a heading at the wrong level, an unparseable route
  handler — all become NOTEs, never confident ERRORs.

WHAT IT CHECKS  (4 groups, ordered high→low confidence)
  C1 Coverage     index links resolve · every endpoint file is in the index ·
                  route handlers in code → endpoint files (missing=ERROR; the reverse,
                  orphan doc, is a NOTE since handler parsing is best-effort)
  C2 Field count  per doc table, reverse-lookup the Go struct whose json tags are the
                  tightest superset of the table's fields; flag serializable struct
                  fields with no doc row (the dangerous direction: undocumented field)
                  -> ERROR. No confident match (unmatched/ambiguous/loose/dup) -> NOTE
  C3 M/O          for fields mapped in C2, recompute M/O from struct tags and compare
                  (required→M, pointer→O, bool-without-required→O, omitempty→O)-> ERROR
  C4 Structure    every endpoint file has Method + Path + >=1 example ·
                  every ```json block parses (catches trailing commas)     -> ERROR

  NOTE sources (always emitted for the fresh-eyes pass): an Error Responses table
  (error tracing is multi-layer + consolidation — out of regex reach), a Business
  Logic section (step counting is judgment), a Remark mentioning a custom type /
  wrapper / "See ... Object", inline query params. See NOTE_SECTIONS / NOTE_PATTERNS.

USAGE
  python3 doccheck.py docs/api/            --src .        # whole tree vs ./ source
  python3 doccheck.py docs/api/consent/x.md --src ./svc   # one file
  (--src also accepts --src=PATH; arg order is irrelevant. --src = repo root, where
   go.mod lives — usually ".")
Exit code: 0 = no ERROR (NOTEs/WARNINGs ok), 1 = at least one ERROR.
"""
import re, sys, json, pathlib
from collections import defaultdict


# ───────────────────────── Go source parsing ─────────────────────────

# A field line:  Name   *pkg.Type   `json:"x,omitempty" validate:"required"`
RE_FIELD = re.compile(
    r'^\s*([A-Za-z_]\w*)\s+([\*\[\]\w.]+)\s*(?:`([^`]*)`)?\s*(?://.*)?$')
# An embedded field:  pkg.Type   (no field name, no tag) — or just  BaseResponse
RE_EMBED = re.compile(r'^\s*(\*?[A-Za-z_][\w.]*)\s*(?://.*)?$')
RE_JSON_TAG = re.compile(r'json:"([^"]*)"')
RE_REQUIRED = re.compile(r'(?:validate|binding):"[^"]*\brequired\b[^"]*"')
# `type Name [optional-type-params] struct {`  — the type-param group keeps generics visible.
RE_STRUCT = re.compile(r'type\s+(\w+)\s*(?:\[[^\]]*\])?\s+struct\s*\{')
# Route registration across Fiber/Echo/Chi/Gin: x.Get("/p", handler.Fn)
RE_ROUTE = re.compile(
    r'\b\w+\.(Get|Post|Put|Patch|Delete|Options|Head)\s*\(\s*"([^"]*)"\s*,\s*([^)]+)\)',
    re.I)
# A handler reference we trust: a dotted selector ending in an exported method,
# e.g. handler.GetUser / h.GetUser. Closures (`func(...`), factories (`h.X(deps)`),
# and bare lowercase locals do NOT match → the route is skipped, not guessed.
RE_HANDLER = re.compile(r'^[\w.]+\.([A-Z]\w*)$')

RE_MD_LINK = re.compile(r'\[[^\]]*\]\(([^)]+)\)')
RE_JSON_BLOCK = re.compile(r'```json\s*\n(.*?)```', re.S)
# A field-table section accidentally authored at H3 (template prescribes H2).
RE_H3_FIELD = re.compile(r'^###\s+(request body|response|path parameters|query parameters)',
                         re.I | re.M)

# Field-table sections and their M/O policy. Request headings are an exact set (the
# template gives them no "(...)" suffix), whereas a Response heading carries a status
# suffix ("Response (200 OK)") and so is matched by prefix in is_response() below.
REQUEST_HEADINGS = ('request body', 'path parameters', 'query parameters')

# NOTE sources — judgment areas the script will not touch, surfaced for fresh-eyes.
# A section-name → message map + a regex → message list; add a new judgment area by
# adding one entry here, not a new code branch. Every message ends "needs fresh-eyes".
NOTE_SECTIONS = {
    'error responses': 'error-rows: trace handler→usecase→domain-service + '
                       'consolidation needs fresh-eyes',
    'business logic':  'step counting/wording needs fresh-eyes (P1 verbatim / P2 rules)',
    'query parameters': 'inline query params: M/O depends on explicit handler check — '
                        'needs fresh-eyes',
}
NOTE_PATTERNS = [
    (re.compile(r'See\s+\w+\s+Object|wrapper|custom type', re.I),
     'nested object / wrapper / custom-type — verify enum + shape, needs fresh-eyes'),
]


def iter_structs(text):
    """Yield (struct_name, body_text) for every `type X struct { ... }` (generics ok).
       Brace-matched so a struct is read whole even with anonymous inner structs."""
    for m in RE_STRUCT.finditer(text):
        depth, i, n = 1, m.end(), len(text)
        while i < n and depth:
            c = text[i]
            if c == '{':
                depth += 1
            elif c == '}':
                depth -= 1
            i += 1
        yield m.group(1), text[m.end():i - 1]


def parse_struct_fields(body):
    """Parse one struct body into a list of field dicts. Inner anonymous-struct
       blocks are skipped at depth>0 (best-effort — nested objects are a NOTE area)."""
    fields, depth = [], 0
    for line in body.splitlines():
        stripped = line.strip()
        depth += stripped.count('{') - stripped.count('}')
        if not stripped or stripped.startswith('//') or depth > (1 if '{' in stripped else 0):
            continue
        m = RE_FIELD.match(line)
        if m and (m.group(3) is not None or _looks_typed(m.group(2))):
            go_name, gotype, tag = m.group(1), m.group(2), m.group(3) or ''
            if go_name in ('struct', 'func', 'interface'):
                continue
            jt = RE_JSON_TAG.search(tag)
            json_name = jt.group(1).split(',')[0] if jt else go_name
            omitempty = bool(jt and 'omitempty' in jt.group(1))
            fields.append({
                'go': go_name, 'json': json_name, 'type': gotype,
                'required': bool(RE_REQUIRED.search(tag)),
                'pointer': gotype.startswith('*'),
                'bool': gotype.lstrip('*') == 'bool',
                'omitempty': omitempty,
                'embedded': False,
                'exported': go_name[:1].isupper(),
            })
            continue
        em = RE_EMBED.match(line)
        if em and depth == 0:
            fields.append({'go': em.group(1), 'embedded': True,
                           'type': em.group(1).lstrip('*')})
    return fields


def _looks_typed(t):
    """A bare 2-token line is a field only if token2 looks like a Go type, not prose."""
    return bool(re.match(r'^[\*\[\]\w.]+$', t)) and not t[:1].isspace()


def parse_go(src_root):
    """Return (structs, routes, dup_names). structs: name -> [field dicts] (embedded
       unresolved). dup_names: struct names defined differently in >1 file — excluded
       from matching so a wrong same-named struct can't silently pass/fail a doc.
       Skips _test.go and vendor/. Returns (None, [], set()) if no Go files found."""
    root = pathlib.Path(src_root)
    structs, routes, dup_names, found = {}, [], set(), False
    for gofile in root.rglob('*.go'):
        if gofile.name.endswith('_test.go') or 'vendor' in gofile.parts:
            continue
        found = True
        try:
            text = gofile.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        for name, body in iter_structs(text):
            fields = parse_struct_fields(body)
            if name in structs and structs[name] != fields:
                dup_names.add(name)           # same name, different shape across files
            structs[name] = fields
        for rm in RE_ROUTE.finditer(text):
            hm = RE_HANDLER.match(rm.group(3).strip())   # trusted dotted-exported ref only
            if hm:
                routes.append({'method': rm.group(1).upper(),
                               'path': rm.group(2), 'handler': hm.group(1)})
    return (structs if found else None), routes, dup_names


def resolve_serializable(struct_name, structs, _seen=None):
    """Serializable json field dicts of a struct, with embedded structs inlined
       recursively (the template wants embedded fields expanded into the parent table).
       Excludes json:"-" and unexported fields. _seen guards against import cycles."""
    _seen = _seen or set()
    if struct_name not in structs or struct_name in _seen:
        return None
    _seen.add(struct_name)
    out = []
    for f in structs[struct_name]:
        if f.get('embedded'):
            sub = resolve_serializable(f['type'].split('.')[-1], structs, _seen)
            if sub:
                out.extend(sub)
            continue
        if f['json'] == '-' or not f['exported']:
            continue
        out.append(f)
    return out


def pascal_to_kebab(name):
    s = re.sub(r'([a-z0-9])([A-Z])', r'\1-\2', name)
    s = re.sub(r'([A-Z]+)([A-Z][a-z])', r'\1-\2', s)
    return s.lower()


def compute_mo(field, is_request):
    """M/O from struct tags (api-doc-template.md § M/O Classification)."""
    if is_request:
        if field['required']:
            return 'M'
        if field['pointer'] or field['omitempty'] or field['bool']:
            return 'O'
        return 'M'
    return 'O' if field['pointer'] else 'M'


# ───────────────────────── Markdown doc parsing ─────────────────────────

def split_sections(md):
    """{heading_text: section_body} split on `## ` headings (H2). Text before the
       first H2 is keyed ''. Heading text is lowercased + trimmed."""
    parts = re.split(r'^##\s+(.+?)\s*$', md, flags=re.M)
    out = {'': parts[0]}
    for i in range(1, len(parts), 2):
        out[parts[i].strip().lower()] = parts[i + 1]
    return out


def is_response(heading):
    """A Response field table: 'response (200 ok)' yes, 'response example' no."""
    return heading.startswith('response') and 'example' not in heading


def parse_md_tables(section):
    """Yield (label, [rows]) for each markdown table in a section. label = the
       nearest preceding bold line (e.g. '**Item Object:**') or '' for the main table.
       Each row = dict of header->cell (headers lowercased)."""
    tables, lines = [], section.splitlines()
    label, i = '', 0
    while i < len(lines):
        line = lines[i].strip()
        bm = re.match(r'^\*\*(.+?)\*\*\s*$', line)
        if bm:
            label = bm.group(1).strip()
            i += 1
            continue
        if line.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|?\s*$', lines[i + 1].strip()):
            headers = [h.strip().lower() for h in line.strip('|').split('|')]
            rows, i = [], i + 2
            while i < len(lines) and lines[i].strip().startswith('|'):
                cells = [c.strip() for c in lines[i].strip().strip('|').split('|')]
                rows.append(dict(zip(headers, cells)))
                i += 1
            tables.append((label, rows))
            label = ''
            continue
        i += 1
    return tables


def row_field_name(row):
    """The field-name cell of a table row, backticks stripped. Single source for the
       column-fallback chain so C2 (count) and C3 (M/O) never disagree on the name."""
    v = row.get('field name') or row.get('field') or (next(iter(row.values()), '') if row else '')
    return v.strip().strip('`').strip()


def table_field_names(rows):
    return [n for n in (row_field_name(r) for r in rows) if n]


# ───────────────────────── checks ─────────────────────────

def check_index(docs_dir, endpoint_files, errors):
    """C1a/C1b — index links resolve, and every endpoint file is in the index."""
    index = docs_dir / 'index.md'
    if not index.exists():
        errors.append(('index.md', 'ERROR', 'index.md missing'))
        return
    text = index.read_text(encoding='utf-8', errors='replace')
    linked = set()
    for m in RE_MD_LINK.finditer(text):
        target = m.group(1).split('#')[0].strip()
        if not target or target.startswith(('http://', 'https://')) or not target.endswith('.md'):
            continue
        linked.add(re.sub(r'^\./', '', target))
        if not (docs_dir / target).resolve().exists():
            errors.append(('index.md', 'ERROR', f'link to "{target}" → file does not exist'))
    for f in endpoint_files:
        rel = f.relative_to(docs_dir).as_posix()
        if rel not in linked:
            errors.append((rel, 'ERROR', f'endpoint file not linked from index.md ({rel})'))


def check_handler_coverage(docs_dir, endpoint_files, routes, errors, notes):
    """C1c — route handler names (→kebab) vs endpoint files. Best-effort tripwire:
       a route with no doc is a confident ERROR (a forgotten doc); the reverse (a doc
       with no matching route) is a NOTE, because handler parsing is best-effort and an
       'orphan' may just be a route whose handler we couldn't parse."""
    if not routes:
        return
    by_stem = {f.stem: f.relative_to(docs_dir).as_posix() for f in endpoint_files}
    handler_files = {pascal_to_kebab(r['handler']) for r in routes}
    for hf in sorted(handler_files - set(by_stem)):
        errors.append(('(coverage)', 'ERROR', f'route handler "{hf}" has no endpoint doc file'))
    for stem in sorted(set(by_stem) - handler_files):
        notes.append((by_stem[stem], f'endpoint file matches no parsed route handler '
                                     f'("{stem}") — verify the route exists (needs fresh-eyes)'))


def map_table_to_struct(field_names, name_sets, resolved):
    """Reverse-lookup the Go struct for a doc table: the TIGHTEST struct whose
       serializable json names ⊇ the table's fields. Returns (name, fields) only when
       confident; otherwise (None, reason) so the caller degrades to a NOTE:
         no-source / empty-table / unmatched / ambiguous (size tie) / loose (struct
         far larger than the table → probably the wrong struct)."""
    if name_sets is None:
        return None, 'no-source'
    if not field_names:
        return None, 'empty-table'
    want = set(field_names)
    hits = sorted((n for n, names in name_sets.items() if want <= names),
                  key=lambda n: len(name_sets[n]))
    if not hits:
        return None, 'unmatched'
    best = hits[0]
    if len(hits) > 1 and len(name_sets[hits[1]]) == len(name_sets[best]):
        return None, 'ambiguous'                       # two equally-tight supersets
    if len(name_sets[best]) - len(want) > max(2, len(want)):
        return None, 'loose'                           # struct ≫ table → not confident
    return best, resolved[best]


def check_endpoint(path, docs_dir, name_sets, resolved, errors, notes):
    """C2/C3/C4 + NOTE emission for one endpoint .md file."""
    rel = path.relative_to(docs_dir).as_posix()
    md = path.read_text(encoding='utf-8', errors='replace')
    sections = split_sections(md)

    # C4 — structure (always)
    if not re.search(r'\*\*Method:\*\*', md):
        errors.append((rel, 'ERROR', 'missing **Method:** line'))
    if not re.search(r'\*\*Path:\*\*', md):
        errors.append((rel, 'ERROR', 'missing **Path:** line'))
    json_blocks = RE_JSON_BLOCK.findall(md)
    if not json_blocks:
        errors.append((rel, 'ERROR', 'no ```json example block'))
    for jb in json_blocks:
        try:
            json.loads(jb)
        except json.JSONDecodeError as e:
            errors.append((rel, 'ERROR', f'invalid JSON example ({e.msg} line {e.lineno})'))
    if RE_H3_FIELD.search(md):
        notes.append((rel, 'a field section is at H3 (template uses H2) — the script reads '
                           'H2 only, so it may be skipped; needs fresh-eyes'))

    # C2/C3 — field count + M/O, only when Go source is available
    if name_sets is not None:
        for heading, body in sections.items():
            is_req = heading in REQUEST_HEADINGS
            if not (is_req or is_response(heading)):
                continue
            for label, rows in parse_md_tables(body):
                names = table_field_names(rows)
                if not names:
                    continue
                struct_name, info = map_table_to_struct(names, name_sets, resolved)
                if struct_name is None:
                    notes.append((rel, f'table "{label or heading}" → no confident struct '
                                       f'match ({info}); field-count + M/O need fresh-eyes'))
                    continue
                doc_names = set(names)
                for f in info:
                    if f['json'] not in doc_names:
                        errors.append((rel, 'ERROR',
                                       f'{struct_name}.{f["json"]} is serializable but has no row '
                                       f'in "{label or heading}" (undocumented field)'))
                by_json = {f['json']: f for f in info}
                for r in rows:
                    fn = row_field_name(r)
                    mo = (r.get('mandatory') or '').strip().upper()
                    if fn in by_json and mo in ('M', 'O'):
                        expect = compute_mo(by_json[fn], is_req)
                        if expect != mo:
                            errors.append((rel, 'ERROR', f'field `{fn}`: tags → {expect}, doc says {mo}'))

    # NOTE sources — judgment areas the script will not touch (always; data-driven)
    for sec, msg in NOTE_SECTIONS.items():
        if sec in sections:
            notes.append((rel, msg))
    for pat, msg in NOTE_PATTERNS:
        if pat.search(md):
            notes.append((rel, msg))


# ───────────────────────── main ─────────────────────────

def parse_args(argv):
    """(target, src) from argv. --src consumes its value (space or =) regardless of
       position; the first bare token is the docs target."""
    positional, src = [], '.'
    it = iter(argv)
    for a in it:
        if a == '--src':
            src = next(it, '.')
        elif a.startswith('--src='):
            src = a[len('--src='):]
        elif a.startswith('--'):
            continue
        else:
            positional.append(a)
    target = pathlib.Path(positional[0]) if positional else pathlib.Path('docs/api')
    return target, src


def collect_docs(target):
    """(docs_dir, [endpoint files]). target may be the docs dir or a single .md.
       Directory mode walks recursively so loose / deeply-nested files are not skipped."""
    if target.is_file():
        docs_dir = target.parent if target.parent.name == 'api' else target.parent.parent
        return docs_dir, [target]
    files = [f for f in sorted(target.rglob('*.md')) if f.name != 'index.md']
    return target, files


def _bucket():
    return {'ERROR': [], 'NOTE': []}


def main():
    target, src = parse_args(sys.argv[1:])

    if not target.exists():
        print(f"doccheck: {target} not found — nothing to check")
        sys.exit(0)

    docs_dir, endpoint_files = collect_docs(target)
    if not endpoint_files and not (docs_dir / 'index.md').exists():
        print("doccheck: no endpoint .md files or index.md — nothing to check")
        sys.exit(0)

    structs, routes, dup_names = parse_go(src)
    # Resolve every struct's serializable fields ONCE — map_table_to_struct then only
    # does a per-table subset test, instead of re-resolving the whole struct universe
    # for every table of every endpoint. Duplicate-named structs are excluded so a
    # wrong same-named struct can't be matched.
    if structs is None:
        name_sets = resolved = None
    else:
        resolved = {n: resolve_serializable(n, structs) for n in structs}
        name_sets = {n: {f['json'] for f in ser}
                     for n, ser in resolved.items() if ser and n not in dup_names}

    errors, notes = [], []
    if target.is_dir():
        check_index(docs_dir, endpoint_files, errors)
        check_handler_coverage(docs_dir, endpoint_files, routes, errors, notes)
    if name_sets is None:
        notes.append(('(global)', f'no Go source under --src {src!r} — coverage/field/M-O '
                                  'checks skipped; needs fresh-eyes'))
    elif dup_names:
        notes.append(('(global)', f'struct name(s) defined differently in >1 file '
                                  f'({", ".join(sorted(dup_names))}) — excluded from matching; '
                                  'needs fresh-eyes'))

    for f in endpoint_files:
        try:
            check_endpoint(f, docs_dir, name_sets, resolved, errors, notes)
        except Exception as e:                       # one bad file can't blank the run
            errors.append((f.name, 'ERROR', f'doccheck crashed on this file ({e!r})'))

    # ---- report (grouped by file, lint.py-style) ----
    by_file = defaultdict(_bucket)
    for fname, _level, msg in errors:
        by_file[fname]['ERROR'].append(msg)
    for fname, msg in notes:
        by_file[fname]['NOTE'].append(msg)

    # Show every endpoint file (clean ones as ✓ OK) so "checked" is visible, then
    # structural entries (index.md / (coverage) / (global)).
    endpoint_rels = [f.relative_to(docs_dir).as_posix() for f in endpoint_files]
    special = sorted(k for k in by_file if k not in endpoint_rels)
    for fname in special + endpoint_rels:
        rec = by_file[fname]
        errs, nts = rec['ERROR'], rec['NOTE']
        status = f'{len(errs)} ERROR' if errs else 'OK'
        extra = f' / {len(nts)} note' if nts else ''
        print(f"{'✗' if errs else '✓'} {fname:46} {status}{extra}")
        for e in errs:
            print(f"    ERROR  {e}")
        for n in nts:
            print(f"    NOTE   {n}")

    total_err = len(errors)
    print(f"\n{'FAILED' if total_err else 'PASS'} — {total_err} error(s) / {len(notes)} note(s) "
          f"across {len(endpoint_files)} endpoint file(s)")
    sys.exit(1 if total_err else 0)


if __name__ == '__main__':
    main()
