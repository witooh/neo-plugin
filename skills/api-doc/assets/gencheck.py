#!/usr/bin/env python3
"""
gencheck.py — TRIPWIRE cross-checker for `api-doc gen` output (OpenCollection YAML vs Go code).
Zero install: pure Python 3 (stdlib only; uses PyYAML if present, else a safe fallback).
Companion to the api-doc skill's `gen` command, Layer 1.

WHY THIS EXISTS
  The old verify was a single-agent self-check: the same agent that wrote the
  collection re-read the source and judged itself. The blind-spot is structural —
  an agent that miscounted fields while writing tends to miscount them again while
  checking. This script is the DETERMINISTIC, independent measure of the things a
  machine CAN count, so "verify passed" rests on evidence, not on the writer's
  confidence (the same principle neo's lint.py/docverify.py encode for HTML docs).

PHILOSOPHY: TRIPWIRE, NOT GROUND TRUTH
  Regex cannot parse Go as well as a compiler. So this script does NOT decide a doc
  is wrong — it RAISES A SIGNAL for a human/agent to inspect:
    • ERROR  = a mismatch the script is confident about (missing request file, struct
               field with no doc row, a bool typed M, a url path-param not declared).
               The agent confirms each before fixing; a genuine false positive is
               skipped + noted, never blindly "fixed". Loop until ERRORs clear OR
               ~3 rounds stall.
    • NOTE   = something the script deliberately CANNOT verify confidently (error-row
               tracing, step counting, custom-type enums, a struct it could not match,
               a file it could not parse without a YAML lib). Never silently skipped —
               printed so the Layer-2 fresh-eyes verifier knows where to look. Each
               NOTE line ends in "needs fresh-eyes"; NOTEs never fail the run.

  To stay a tripwire (no false ERROR on a correct collection), every uncertain case
  DEGRADES to a NOTE rather than an ERROR.

WHAT IT CHECKS  (ordered high→low confidence)
  C1 Coverage   route handlers in code → request .yml files (missing=ERROR; the
                reverse, orphan file, is a NOTE since handler parsing is best-effort) ·
                collection-root opencollection.yml `docs:` exists with a Common Error
                Responses section (the old index.md replacement)            -> ERROR
  C2 Field count per `docs:` table, reverse-lookup the Go struct whose json tags are
                the tightest superset of the table's fields; flag serializable struct
                fields with no doc row (undocumented field)                  -> ERROR
                No confident match (unmatched/ambiguous/loose/dup)           -> NOTE
  C3 M/O        for fields mapped in C2, recompute M/O from struct tags and compare
                (required→M, pointer→O, bool-without-required→O, omitempty→O) -> ERROR
  C4 Structure  every request .yml has info.name + http.method + http.url + a docs:
                block · `http.url` path params (:name) ⇔ `params` (type: path) ·
                `http.body.data` + every ```json fence in docs parse · seq unique
                per folder · docs Request-Body mandatory fields ⊆ body.data keys -> ERROR

  NOTE sources (always emitted for the fresh-eyes pass): an Error Responses table
  (error tracing is multi-layer), a Business Logic section (step counting is judgment),
  a Remark mentioning a custom type / wrapper / "See ... Object", inline query params,
  a user-added runtime/examples block (confirm it survived Update). See
  NOTE_SECTIONS / NOTE_PATTERNS.

USAGE
  python3 gencheck.py <collection-root>          --src .        # whole collection vs ./ source
  python3 gencheck.py <collection>/consent/x.yml --src ./svc    # one request file
  (--src also accepts --src=PATH; arg order is irrelevant. --src = repo root, where
   go.mod lives — usually ".")
Exit code: 0 = no ERROR (NOTEs/WARNINGs ok), 1 = at least one ERROR.
"""
import re, sys, json, pathlib
from collections import defaultdict

try:
    import yaml                      # PyYAML — full YAML structural checks when present
    HAVE_YAML = True
except Exception:
    HAVE_YAML = False                # fallback: docs: block checks only, rest → NOTE


# ───────────────────────── Go source parsing (format-agnostic core) ─────────────────────────

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


# ───────────────────────── Markdown doc parsing (reused on the docs: block) ─────────────────────────

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


# ───────────────────────── YAML request reading ─────────────────────────

def extract_block_scalar(text, key, base_indent=0):
    """Best-effort: dedented content of a `key: |`/`>` block scalar at column
       base_indent, or None. Used as the no-PyYAML fallback for the top-level docs:."""
    pat = re.compile(r'^' + ' ' * base_indent + re.escape(key) + r':\s*[|>][+-]?\s*$')
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if pat.match(line):
            block = []
            for j in range(i + 1, len(lines)):
                ln = lines[j]
                if ln.strip() == '':
                    block.append('')
                    continue
                indent = len(ln) - len(ln.lstrip(' '))
                if indent <= base_indent:
                    break
                block.append(ln)
            indents = [len(b) - len(b.lstrip(' ')) for b in block if b.strip()]
            if not indents:
                return ''
            cut = min(indents)
            return '\n'.join(b[cut:] if b.strip() else '' for b in block).rstrip('\n')
    return None


def read_request_yaml(path):
    """Parse one request .yml. With PyYAML: full structured read. Without: extract the
       top-level docs: block only and mark the rest 'manual' (caller degrades to NOTE)."""
    text = path.read_text(encoding='utf-8', errors='replace')
    out = {'ok': True, 'mode': 'yaml' if HAVE_YAML else 'manual',
           'info': {}, 'http': {}, 'settings': {}, 'docs': None,
           'body_type': None, 'body_data': None, 'params': [],
           'has_runtime': False, 'has_examples': False}
    if HAVE_YAML:
        try:
            d = yaml.safe_load(text)
        except Exception as e:
            out['ok'] = False
            out['error'] = f'{type(e).__name__}'
            return out
        if not isinstance(d, dict):
            out['ok'] = False
            out['error'] = 'top level is not a mapping'
            return out
        out['info'] = d.get('info') if isinstance(d.get('info'), dict) else {}
        out['http'] = d.get('http') if isinstance(d.get('http'), dict) else {}
        out['settings'] = d.get('settings') if isinstance(d.get('settings'), dict) else {}
        out['docs'] = d.get('docs') if isinstance(d.get('docs'), str) else None
        out['has_runtime'] = 'runtime' in d
        out['has_examples'] = 'examples' in d
        body = out['http'].get('body') if isinstance(out['http'].get('body'), dict) else {}
        out['body_type'] = body.get('type')
        out['body_data'] = body.get('data') if isinstance(body.get('data'), str) else None
        params = out['http'].get('params')
        out['params'] = [p for p in params if isinstance(p, dict)] if isinstance(params, list) else []
    else:
        out['docs'] = extract_block_scalar(text, 'docs', 0)
    return out


# ───────────────────────── checks ─────────────────────────

def check_root_docs(root, errors, notes):
    """C1 — collection-root opencollection.yml carries a docs: block with a Common
       Error Responses section (the index.md replacement)."""
    oc = root / 'opencollection.yml'
    if not oc.exists():
        errors.append(('opencollection.yml', 'ERROR', 'opencollection.yml missing at collection root'))
        return
    text = oc.read_text(encoding='utf-8', errors='replace')
    docs = None
    if HAVE_YAML:
        try:
            d = yaml.safe_load(text)
            docs = d.get('docs') if isinstance(d, dict) and isinstance(d.get('docs'), str) else None
        except Exception:
            docs = extract_block_scalar(text, 'docs', 0)
    else:
        docs = extract_block_scalar(text, 'docs', 0)
    if not docs:
        errors.append(('opencollection.yml', 'ERROR',
                       'collection-root docs: missing (service overview + Common Error Responses)'))
        return
    if 'common error' not in docs.lower():
        errors.append(('opencollection.yml', 'ERROR',
                       'collection-root docs: has no "Common Error Responses" section'))
    elif len(docs.strip()) < 40:
        notes.append(('opencollection.yml',
                      'collection-root docs: looks too short for an overview — needs fresh-eyes'))


def check_route_coverage(root, request_files, routes, errors, notes):
    """C1 — route handler names (→kebab) vs request files. Best-effort tripwire: a route
       with no file is a confident ERROR; the reverse (a file with no matching route) is
       a NOTE, because handler parsing is best-effort."""
    if not routes:
        return
    by_stem = {f.stem: f.relative_to(root).as_posix() for f in request_files}
    handler_files = {pascal_to_kebab(r['handler']) for r in routes}
    for hf in sorted(handler_files - set(by_stem)):
        errors.append(('(coverage)', 'ERROR', f'route handler "{hf}" has no request .yml file'))
    for stem in sorted(set(by_stem) - handler_files):
        notes.append((by_stem[stem], f'request file matches no parsed route handler '
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


def check_request(path, root, name_sets, resolved, errors, notes, seq_seen):
    """C2/C3/C4 + NOTE emission for one request .yml file."""
    rel = path.relative_to(root).as_posix()
    r = read_request_yaml(path)
    if not r['ok']:
        errors.append((rel, 'ERROR', f'YAML parse failed ({r.get("error", "")})'))
        return
    info, http = r['info'], r['http']
    yaml_mode = r['mode'] == 'yaml'

    if yaml_mode:
        # C4a — YAML-native structure
        if not info.get('name'):
            errors.append((rel, 'ERROR', 'info.name missing'))
        if info.get('type') not in (None, 'http'):
            notes.append((rel, f'info.type is {info.get("type")!r}, not "http" — needs fresh-eyes'))
        url = http.get('url') or ''
        if not (http.get('method') or '').strip():
            errors.append((rel, 'ERROR', 'http.method missing'))
        if not url:
            errors.append((rel, 'ERROR', 'http.url missing'))
        if r['settings'].get('encodeUrl') is not True:
            notes.append((rel, 'settings.encodeUrl is not true — needs fresh-eyes'))
        # seq uniqueness is aggregated per folder in main()
        seq = info.get('seq')
        if seq is not None:
            seq_seen[path.parent.as_posix()].setdefault(seq, []).append(rel)
        # C4b — path params: ":name" in url ⇔ params(type: path)
        url_params = set(re.findall(r':([A-Za-z_]\w*)', url))
        decl_path = {p.get('name') for p in r['params'] if p.get('type') == 'path' and p.get('name')}
        for up in sorted(url_params - decl_path):
            errors.append((rel, 'ERROR', f'path param ":{up}" in url not declared in params (type: path)'))
        for dp in sorted(decl_path - url_params):
            errors.append((rel, 'ERROR', f'params declares path param "{dp}" absent from http.url'))
        # C4c — runnable body JSON
        if r['body_type'] == 'json' and r['body_data']:
            try:
                json.loads(r['body_data'])
            except json.JSONDecodeError as e:
                errors.append((rel, 'ERROR', f'http.body.data invalid JSON ({e.msg} line {e.lineno})'))
    else:
        notes.append((rel, 'no YAML parser (PyYAML/yq absent) — http-block structure, path-param, '
                           'and body.data checks skipped; needs fresh-eyes'))

    docs = r['docs']
    if not docs:
        errors.append((rel, 'ERROR', 'docs: block missing or empty'))
        return

    # C4c — JSON fences inside docs
    for jb in RE_JSON_BLOCK.findall(docs):
        try:
            json.loads(jb)
        except json.JSONDecodeError as e:
            errors.append((rel, 'ERROR', f'invalid JSON example in docs ({e.msg} line {e.lineno})'))
    if RE_H3_FIELD.search(docs):
        notes.append((rel, 'a docs field section is at H3 (template uses H2) — the script reads '
                           'H2 only, so it may be skipped; needs fresh-eyes'))

    sections = split_sections(docs)

    # C2/C3 — field count + M/O against Go structs (when source available)
    req_body_rows = None
    for heading, body in sections.items():
        is_req = heading in REQUEST_HEADINGS
        if not (is_req or is_response(heading)):
            continue
        if heading == 'path parameters':
            continue   # URL segments, not a serializable struct — C4b validates them via http.url ↔ params
        for label, rows in parse_md_tables(body):
            if heading == 'request body' and req_body_rows is None:
                req_body_rows = rows
            names = table_field_names(rows)
            if not names:
                continue
            if name_sets is None:
                continue
            struct_name, inf = map_table_to_struct(names, name_sets, resolved)
            if struct_name is None:
                notes.append((rel, f'table "{label or heading}" → no confident struct '
                                   f'match ({inf}); field-count + M/O need fresh-eyes'))
                continue
            doc_names = set(names)
            for f in inf:
                if f['json'] not in doc_names:
                    errors.append((rel, 'ERROR',
                                   f'{struct_name}.{f["json"]} is serializable but has no row '
                                   f'in "{label or heading}" (undocumented field)'))
            by_json = {f['json']: f for f in inf}
            for rr in rows:
                fn = row_field_name(rr)
                mo = (rr.get('mandatory') or '').strip().upper()
                if fn in by_json and mo in ('M', 'O'):
                    expect = compute_mo(by_json[fn], is_req)
                    if expect != mo:
                        errors.append((rel, 'ERROR', f'field `{fn}`: tags → {expect}, doc says {mo}'))

    # NEW — reconcile docs Request-Body mandatory fields ⊆ runnable http.body.data keys
    if yaml_mode and r['body_type'] == 'json' and r['body_data'] and req_body_rows:
        try:
            body_json = json.loads(r['body_data'])
        except Exception:
            body_json = None
        if isinstance(body_json, dict):
            keys = set(body_json.keys())
            doc_field_names = {row_field_name(rr) for rr in req_body_rows if row_field_name(rr)}
            for rr in req_body_rows:
                fn = row_field_name(rr)
                mo = (rr.get('mandatory') or '').strip().upper()
                if fn and mo == 'M' and fn not in keys:
                    errors.append((rel, 'ERROR',
                                   f'mandatory body field `{fn}` (docs) missing from http.body.data example'))
            for k in sorted(keys - doc_field_names):
                notes.append((rel, f'http.body.data has key "{k}" not in the docs Request Body '
                                   f'table — needs fresh-eyes'))

    # NOTE sources — judgment areas the script will not touch (always; data-driven)
    for sec, msg in NOTE_SECTIONS.items():
        if sec in sections:
            notes.append((rel, msg))
    for pat, msg in NOTE_PATTERNS:
        if pat.search(docs):
            notes.append((rel, msg))
    if r['has_runtime'] or r['has_examples']:
        notes.append((rel, 'request has a runtime/examples block (possibly user-added) — '
                           'confirm Update preserved it; needs fresh-eyes'))


# ───────────────────────── main ─────────────────────────

def parse_args(argv):
    """(target, src) from argv. --src consumes its value (space or =) regardless of
       position; the first bare token is the collection target."""
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
    target = pathlib.Path(positional[0]) if positional else pathlib.Path('.')
    return target, src


def collect_requests(target):
    """(root, [request .yml files]). Excludes opencollection.yml, folder.yml, and
       anything under environments/. Walks recursively so nested groups aren't skipped."""
    if target.is_file():
        root, p = target.parent, target.parent
        while p != p.parent:
            if (p / 'opencollection.yml').exists():
                root = p
                break
            p = p.parent
        return root, [target]
    files = []
    for f in sorted(target.rglob('*.yml')):
        if f.name in ('opencollection.yml', 'folder.yml'):
            continue
        if 'environments' in f.relative_to(target).parts:
            continue
        files.append(f)
    return target, files


def _bucket():
    return {'ERROR': [], 'NOTE': []}


def main():
    target, src = parse_args(sys.argv[1:])

    if not target.exists():
        print(f"gencheck: {target} not found — nothing to check")
        sys.exit(0)

    root, request_files = collect_requests(target)
    if not request_files and not (root / 'opencollection.yml').exists():
        print("gencheck: no request .yml files or opencollection.yml — nothing to check")
        sys.exit(0)

    structs, routes, dup_names = parse_go(src)
    # Resolve every struct's serializable fields ONCE — map_table_to_struct then only
    # does a per-table subset test. Duplicate-named structs are excluded so a wrong
    # same-named struct can't be matched.
    if structs is None:
        name_sets = resolved = None
    else:
        resolved = {n: resolve_serializable(n, structs) for n in structs}
        name_sets = {n: {f['json'] for f in ser}
                     for n, ser in resolved.items() if ser and n not in dup_names}

    errors, notes, seq_seen = [], [], defaultdict(dict)
    if target.is_dir():
        check_root_docs(root, errors, notes)
        check_route_coverage(root, request_files, routes, errors, notes)
    if not HAVE_YAML:
        notes.append(('(global)', 'PyYAML not installed — YAML structural checks (http block, '
                                  'path params, body.data) degraded to per-file NOTEs; install '
                                  'PyYAML or yq for full gen verify (needs fresh-eyes)'))
    if name_sets is None:
        notes.append(('(global)', f'no Go source under --src {src!r} — coverage/field/M-O '
                                  'checks skipped; needs fresh-eyes'))
    elif dup_names:
        notes.append(('(global)', f'struct name(s) defined differently in >1 file '
                                  f'({", ".join(sorted(dup_names))}) — excluded from matching; '
                                  'needs fresh-eyes'))

    for f in request_files:
        try:
            check_request(f, root, name_sets, resolved, errors, notes, seq_seen)
        except Exception as e:                       # one bad file can't blank the run
            errors.append((f.name, 'ERROR', f'gencheck crashed on this file ({e!r})'))

    # seq uniqueness per folder
    for folder, seqmap in seq_seen.items():
        for seq, rels in seqmap.items():
            if len(rels) > 1:
                errors.append((rels[0], 'ERROR',
                               f'seq {seq} is reused within this folder by: {", ".join(rels)}'))

    # ---- report (grouped by file, lint.py-style) ----
    by_file = defaultdict(_bucket)
    for fname, _level, msg in errors:
        by_file[fname]['ERROR'].append(msg)
    for fname, msg in notes:
        by_file[fname]['NOTE'].append(msg)

    request_rels = [f.relative_to(root).as_posix() for f in request_files]
    special = sorted(k for k in by_file if k not in request_rels)
    for fname in special + request_rels:
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
          f"across {len(request_files)} request file(s)")
    sys.exit(1 if total_err else 0)


if __name__ == '__main__':
    main()
