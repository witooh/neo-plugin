#!/usr/bin/env python3
"""
driftcheck.py: TRIPWIRE drift checker (Go code vs the Bruno collection under bruno/). Zero
install: pure Python 3 (stdlib + PyYAML, parsing through the sibling docsparse.py).
Deterministic layer of the bruno skill's verify.

WHY THIS EXISTS
  Go code is the SOURCE OF TRUTH; each Bruno request file's `docs:` markdown is generated from
  it. This script scans the Go code and reports where a request's `docs:` has DRIFTED from the
  implementation (a stale contract). It is the DETERMINISTIC, independent measure a machine CAN count, so reconciling
  the collection rests on evidence, not the writer's confidence. (It writes no file; it
  reads bruno/**/*.yml + Go.)

PHILOSOPHY: TRIPWIRE, NOT GROUND TRUTH
    • DRIFT = a Go-vs-collection mismatch the script is confident about (a route on one side
              only, a serializable field with no docs row, a docs field absent from the
              struct, an M/O or type that disagree on a confidently-matched field). Each is
              confirmed before the collection is reconciled; a genuine false positive: e.g.
              an endpoint documented before it is built, or an intentionally-undocumented
              route, is confirmed + skipped, never blindly "fixed". Loop until DRIFT clears
              OR ~3 rounds stall, then escalate.
    • NOTE  = something the script deliberately CANNOT decide confidently (a field group it
              could not match to a Go struct, the response envelope wrapper, handler-inline
              query/path params, a request file that did not parse). Printed for the
              fresh-eyes verifier; each ends "needs fresh-eyes"; NOTEs never fail the run.
  Every uncertain case DEGRADES to a NOTE rather than a confident DRIFT.

WHAT IT CHECKS  (ordered high→low confidence)
  D1 Route drift     every Go route is documented by a spec endpoint, and every spec endpoint
                     is implemented by a Go route (matched by method + normalised path, base-
                     URL-suffix-tolerant). A one-sided route = DRIFT. A literal `.Group("/x")`
                     prefix is added to the route path when the group is assigned in the same
                     function or passed to a uniquely-named function; else the path stays literal.
  D2 Field drift     per matched endpoint, reverse-lookup the Go struct whose json names ⊇ the
                     docs field group (top-level Body rows → request struct; each
                     success-response parent group, e.g. `data` → that struct), then compare:
                       • presence: a serializable Go field with no spec row (undocumented) OR
                         a spec field absent from the struct (stale) = DRIFT;
                       • M/O     : compute_mo(tags) vs the spec `mandatory` (M|O) = DRIFT;
                       • type    : go→spec-type mapping vs the spec `type` (confident cases
                         only: bool/[]T/numeric; struct/map/custom/time → skipped) = DRIFT.
                     No confident struct match / envelope wrapper / inline params → NOTE. So is
                     a group that a struct name defined more than once could also describe: the
                     duplicate is excluded, and a lookalike struct must not be paired instead.

USAGE
  python3 driftcheck.py bruno --src .          # bruno root + Go root (where go.mod lives)
  python3 driftcheck.py       --src ./svc      # bruno root defaults to bruno
  (--src also accepts --src=PATH; arg order is irrelevant.)
Exit code: 0 = no DRIFT (NOTEs/WARNINGs ok), 1 = at least one DRIFT, 2 = the bruno root or the Go
source is missing, or PyYAML is missing (nothing was compared).
"""
import re, sys, json, pathlib
from collections import defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
try:
    import docsparse                 # shared Bruno docs parser (sibling file)
except ModuleNotFoundError as e:
    if e.name != "yaml":
        raise
    sys.exit(print("driftcheck.py: needs PyYAML (pip install pyyaml)", file=sys.stderr) or 2)

# ═════════════════════ Go source parsing (the reused engine) ═════════════════════

RE_FIELD = re.compile(
    r'^\s*([A-Za-z_]\w*)\s+([\*\[\]\w.]+)\s*(?:`([^`]*)`)?\s*(?://.*)?$')
RE_EMBED = re.compile(r'^\s*(\*?[A-Za-z_][\w.]*)\s*(?://.*)?$')
RE_JSON_TAG = re.compile(r'json:"([^"]*)"')
RE_REQUIRED = re.compile(r'(?:validate|binding):"[^"]*\brequired\b[^"]*"')
RE_STRUCT = re.compile(r'type\s+(\w+)\s*(?:\[[^\]]*\])?\s+struct\s*\{')
RE_ROUTE = re.compile(
    r'\b(\w+)\.(Get|Post|Put|Patch|Delete|Options|Head)\s*\(\s*"([^"]*)"\s*,\s*([^)]+)\)',
    re.I)
RE_HANDLER = re.compile(r'^[\w.]+\.([A-Z]\w*)$')
RE_CLOSURE = re.compile(r'\s*func\s*\([^)]*\b(?:Context|Ctx|ResponseWriter)\b')
RE_FUNC = re.compile(r'^func\s+(?:\([^)]*\)\s*)?(\w+)\s*(?:\[[^\]]*\])?\s*\(([^)]*)\)', re.M)
RE_GROUP = r'(\w+)\.Group\(\s*"([^"]*)"'
RE_GROUP_ASSIGN = re.compile(r'\b(\w+)\s*:?=\s*' + RE_GROUP)
RE_GROUP_ARG = re.compile(RE_GROUP + r'[^()]*\)$')
RE_CALL = re.compile(r'\b(\w+)\(')


def iter_structs(text):
    """Yield (struct_name, body_text) for every `type X struct { ... }` (brace-matched)."""
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


def _looks_typed(t):
    return bool(re.match(r'^[\*\[\]\w.]+$', t)) and not t[:1].isspace()


def parse_struct_fields(body):
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


def _functions(text):
    """Yield (name, params, body) per top-level func; (None, [], …) holds the text before the first."""
    heads = list(RE_FUNC.finditer(text))
    yield None, [], text[:heads[0].start()] if heads else text
    for m, nxt in zip(heads, heads[1:] + [None]):
        params = [p.split()[0] for p in m.group(2).split(',') if p.strip()]
        yield m.group(1), params, text[m.end():nxt.start() if nxt else len(text)]


def _call_args(text, i):
    """Top-level arguments of the call whose `(` ends at index i (brackets balanced)."""
    args, depth, start = [], 1, i
    while i < len(text) and depth:
        c = text[i]
        if c in '([{':
            depth += 1
        elif c in ')]}':
            depth -= 1
        elif c == ',' and depth == 1:
            args.append(text[start:i])
            start = i + 1
        i += 1
    return [a.strip() for a in args + [text[start:i - 1]]]


def _join(prefix, path):
    return prefix.rstrip('/') + '/' + path.lstrip('/') if prefix and path.strip('/') else prefix or path


def _prefixes(fn, var, calls, seen=frozenset()):
    """Every `.Group("…")` prefix `var` carries inside fn: from an assignment in fn, or from the
       calls that pass a group to fn. {''} when unknown, when `var` is assigned twice or when
       fn's name is defined twice: the route then keeps its literal path."""
    if (id(fn), var) in seen:
        return {''}
    seen = seen | {(id(fn), var)}
    if var in fn['groups']:
        if fn['groups'][var] is None:
            return {''}
        parent, sub = fn['groups'][var]
        return {_join(p, sub) for p in _prefixes(fn, parent, calls, seen)}
    if var not in fn['params']:
        return {''}
    idx, out = fn['params'].index(var), set()
    for caller, args in calls[fn['name']]:
        if idx >= len(args):
            continue
        g = RE_GROUP_ARG.match(args[idx])
        if g:
            out |= {_join(p, g.group(2)) for p in _prefixes(caller, g.group(1), calls, seen)}
        else:
            out |= _prefixes(caller, args[idx], calls, seen)
    return out or {''}


def parse_go(src_root):
    """Return (structs, routes, dup_names). Skips _test.go, vendor/ and, when src_root holds a
       go.mod, every nested module below it (tools/*, worktrees, templates).
       dup_names maps a struct name defined differently in >1 place to each distinct field list.
       Returns (None, [], {}) if no Go files found."""
    root = pathlib.Path(src_root)
    nested = ({m.parent for m in root.rglob('go.mod') if m.parent != root}
              if (root / 'go.mod').is_file() else set())
    structs, routes, dup_names, found = {}, [], {}, False
    by_name = defaultdict(list)
    for gofile in root.rglob('*.go'):
        if gofile.name.endswith('_test.go') or 'vendor' in gofile.parts:
            continue
        if any(p in nested for p in gofile.parents):
            continue
        found = True
        try:
            text = gofile.read_text(encoding='utf-8', errors='replace')
        except Exception:
            continue
        for name, body in iter_structs(text):
            fields = parse_struct_fields(body)
            if name in structs and structs[name] != fields:
                variants = dup_names.setdefault(name, [structs[name]])
                if fields not in variants:
                    variants.append(fields)
            structs[name] = fields
        for name, params, body in _functions(text):
            groups = {}
            for var, parent, sub in RE_GROUP_ASSIGN.findall(body):
                groups[var] = None if var in groups else (parent, sub)
            by_name[name].append({'name': name, 'params': params, 'body': body, 'groups': groups})
    fns = [f for defs in by_name.values() for f in defs]
    calls = defaultdict(list)                         # uniquely-named func → [(caller, args)]
    for fn in fns:
        for m in RE_CALL.finditer(fn['body']):
            if len(by_name.get(m.group(1), ())) == 1:
                calls[m.group(1)].append((fn, _call_args(fn['body'], m.end())))
    for fn in fns:
        for rm in RE_ROUTE.finditer(fn['body']):
            hm = RE_HANDLER.match(rm.group(4).strip())
            if hm or RE_CLOSURE.match(rm.group(4)):   # x.Method or an inline handler closure
                for prefix in sorted(_prefixes(fn, rm.group(1), calls)):
                    routes.append({'method': rm.group(2).upper(), 'path': _join(prefix, rm.group(3)),
                                   'handler': hm.group(1) if hm else None})
    return (structs if found else None), routes, dup_names


def resolve_serializable(struct_name, structs, _seen=None):
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


def compute_mo(field, is_request):
    """M/O from struct tags: a request field is M only when tagged required; a response field
       is O when it can be absent (pointer or omitempty)."""
    if is_request:
        return 'M' if field['required'] else 'O'
    return 'O' if field['pointer'] or field['omitempty'] else 'M'


def map_names_to_struct(field_names, name_sets, resolved):
    """Reverse-lookup the TIGHTEST Go struct whose serializable json names ⊇ field_names.
       Returns (name, fields) when confident; else (None, reason) to degrade to NOTE."""
    if name_sets is None:
        return None, 'no-source'
    if not field_names:
        return None, 'empty-group'
    want = set(field_names)
    hits = sorted((n for n, names in name_sets.items() if want <= names),
                  key=lambda n: len(name_sets[n]))
    if not hits:
        return None, 'unmatched'
    best = hits[0]
    if len(hits) > 1 and len(name_sets[hits[1]]) == len(name_sets[best]):
        return None, 'ambiguous'
    if len(name_sets[best]) - len(want) > max(2, len(want)):
        return None, 'loose'
    return best, resolved[best]


def match_for_drift(field_names, name_sets, resolved):
    """Pair a spec field group with the Go struct it describes, for drift comparison.
       Tier 1: the strict-subset rule above (want ⊆ struct, tight): highest confidence.
       Tier 2 (only when Tier 1 fails): a SAFE best-overlap fallback so a *stale* spec field
       (the struct lost a field the spec still lists) is still caught: but only when the
       overlap is a strong majority of the group AND the struct is tight around it (no giant
       superset), so two unrelated structs are never mis-paired. Returns (name, fields) when
       confident, else (None, reason) to degrade to NOTE."""
    sn, info = map_names_to_struct(field_names, name_sets, resolved)
    if sn is not None or name_sets is None or not field_names:
        return sn, info
    want = set(field_names)
    scored = sorted(name_sets.items(),
                    key=lambda kv: (len(want & kv[1]), -len(kv[1])), reverse=True)
    best, bnames = scored[0]
    overlap = len(want & bnames)
    if overlap < max(2, (len(want) + 1) // 2):
        return None, 'weak-overlap'
    if overlap < len(bnames) - 2:                     # struct much bigger than the overlap
        return None, 'loose'
    if len(scored) > 1 and len(want & scored[1][1]) == overlap and len(scored[1][1]) == len(bnames):
        return None, 'ambiguous'
    return best, resolved[best]


def go_to_spec_type(gotype):
    """Map a Go field type to the docs `type` vocab (String/Number/Boolean/Object/Array).
       Returns None for anything not confidently mappable (named struct, custom type, time.Time,
       interface, json.RawMessage) so type drift NEVER false-positives on those."""
    t = gotype.lstrip('*')
    if t.startswith('[]'):
        return 'Array'
    if t.startswith('map['):
        return 'Object'
    if t == 'bool':
        return 'Boolean'
    if t == 'string':
        return 'String'
    if re.match(r'^(u?int(8|16|32|64)?|float(32|64)|byte|rune)$', t):
        return 'Number'
    return None


def type_compatible(go_t, spec_t):
    """True when a go→spec-type and the spec's declared `type` agree (Number≈Integer)."""
    if go_t is None or not spec_t:
        return True                                  # can't decide → no drift
    spec_t = str(spec_t).strip().capitalize()
    if go_t == 'Number' and spec_t in ('Number', 'Integer'):
        return True
    return go_t == spec_t


# ═════════════════════ Bruno collection parsing ═════════════════════

def norm_path(p):
    """Normalise a URL path template for comparison: params → {}, trailing slash off."""
    p = re.sub(r'\{[^}]+\}', '{}', p)     # {id}  → {}
    p = re.sub(r':[^/]+', '{}', p)        # :id   → {}
    return ('/' + p.strip('/')) if p.strip('/') else '/'


_MANDATORY = {'Yes': 'M', 'No': 'O'}


def _rows(rows):
    """Bruno table rows -> [{name, type, mandatory M|O}] (leaf name already applied)."""
    return [{'name': r['name'], 'type': r.get('type'),
             'mandatory': _MANDATORY.get(r.get('mandatory'))} for r in rows]


def load_bruno(root, notes=None):
    """Parse the Bruno collection's request docs -> (endpoints, extra_set).
       endpoints = [{file, method, npath, request_fields, response_objects{parent:[rows]},
                     has_envelope, has_params}]; extra_set is always empty (a Bruno request
                     file exists for every documented route, health probes included)."""
    root = pathlib.Path(root)
    endpoints = []
    notes = [] if notes is None else notes
    for fp in sorted(root.rglob('*.yml')):
        rel = fp.relative_to(root)
        if rel.parts[0] == 'environments' or fp.name in ('folder.yml', 'opencollection.yml'):
            continue
        try:
            req = docsparse.parse_request(fp)
        except docsparse.ParseError as exc:
            notes.append((str(rel), f'request file did not parse ({exc}); needs fresh-eyes'))
            continue
        docs = req['docs']
        if not docs['endpoint']:
            notes.append((str(rel), 'no `METHOD /path` under Request > Endpoint; skipped; '
                                    'needs fresh-eyes'))
            continue
        method, path = docs['endpoint']
        response_objects, has_envelope = {}, False
        for status, resp in docs['responses'].items():
            if status >= 400:
                continue
            groups = docsparse.group_by_parent(resp['fields'])
            has_envelope = has_envelope or bool(groups.get(''))
            for parent, rows in groups.items():
                if parent:
                    response_objects.setdefault(parent, _rows(rows))
        tables = docs['tables']
        body = docsparse.group_by_parent(tables['body'])
        endpoints.append({
            'file': str(rel),
            'method': method.upper(),
            'npath': norm_path(path),
            'request_fields': _rows(body.get('') or body.get('[]', [])),  # `[].x` = top-level array body
            'response_objects': response_objects,
            'has_envelope': has_envelope,
            'has_params': bool(tables['query'] or tables['path']),
        })
    return endpoints, set()


# ═════════════════════ drift checks ═════════════════════

def _path_match(a, b):
    """method-equal paths match base-URL-suffix-tolerantly (the '/' prefix guards boundaries)."""
    return a == b or a.endswith(b) or b.endswith(a)


def check_route_drift(routes, endpoints, extra_set, drift, notes):
    """D1: bidirectional route presence (matched by method + normalised path)."""
    go_set = sorted({(r['method'], norm_path(r['path'])) for r in routes})
    spec_cover = {(e['method'], e['npath']) for e in endpoints} | extra_set

    # Go route with no spec endpoint = undocumented (or intentionally-skipped) route
    for gm, gp in go_set:
        if not any(gm == sm and _path_match(gp, sp) for sm, sp in spec_cover):
            drift.append(('(routes)', 'DRIFT',
                          f'Go route {gm} {gp} has no request in bruno/ '
                          f'(undocumented route: add a request file, or confirm it is '
                          f'intentionally undocumented and skip)'))

    # spec endpoint (a real file) with no Go route = unimplemented / removed
    for e in endpoints:
        if not any(e['method'] == gm and _path_match(e['npath'], gp) for gm, gp in go_set):
            drift.append(('(routes)', 'DRIFT',
                          f'spec endpoint {e["method"]} {e["npath"]} ({e["file"]}) has no '
                          f'matching Go route (unimplemented [documented first, pending] or a '
                          f'removed route: confirm)'))


def _compare_group(loc, kind, spec_fields, go_fields, is_request, drift):
    """Field-level drift for one matched group (request body / a response object)."""
    spec_by_name = {f['name']: f for f in spec_fields}
    go_by_json = {f['json']: f for f in go_fields}

    # presence: Go field with no spec row (undocumented)
    for jn in go_by_json:
        if jn not in spec_by_name:
            drift.append((loc, 'DRIFT',
                          f'{kind}: Go field `{jn}` is serializable but has no spec row '
                          f'(undocumented field)'))
    # presence: spec row with no Go field (stale)
    for nm in spec_by_name:
        if nm not in go_by_json:
            drift.append((loc, 'DRIFT',
                          f'{kind}: spec documents `{nm}` but the Go struct has no such field '
                          f'(stale spec field)'))
    # M/O + type on fields present on both sides
    for nm, sf in spec_by_name.items():
        gf = go_by_json.get(nm)
        if not gf:
            continue
        expect = compute_mo(gf, is_request)
        if sf.get('mandatory') in ('M', 'O') and sf['mandatory'] != expect:
            drift.append((loc, 'DRIFT',
                          f'{kind}: `{nm}`: Go tags → {expect} but spec says '
                          f'{sf["mandatory"]} (M/O drift)'))
        go_t = go_to_spec_type(gf['type'])
        if not type_compatible(go_t, sf.get('type')):
            drift.append((loc, 'DRIFT',
                          f'{kind}: `{nm}`: Go type {gf["type"]} (→ {go_t}) but spec says '
                          f'{sf.get("type")} (type drift)'))


def _match(field_names, name_sets, shadow, resolved):
    """match_for_drift, unless a struct name defined more than once (so left out of name_sets)
       fits the group at least as tightly as the match: then (None, reason) to degrade to NOTE."""
    sn, info = match_for_drift(field_names, name_sets, resolved)
    want = set(field_names)
    bound = len(name_sets[sn]) if sn is not None and want <= name_sets[sn] else float('inf')
    for key, names in shadow.items():
        if want <= names and len(names) - len(want) <= max(2, len(want)) and len(names) <= bound:
            return None, f'{key.split("#")[0]} is defined more than once'
    return sn, info


def check_field_drift(endpoints, routes, name_sets, shadow, resolved, drift, notes):
    """D2: per matched endpoint, reverse-lookup the Go struct for each spec field group
       and compare presence / M-O / type. Unconfident matches degrade to NOTE."""
    go_set = {(r['method'], norm_path(r['path'])) for r in routes}
    saw_envelope = saw_params = False
    for e in endpoints:
        if not any(e['method'] == gm and _path_match(e['npath'], gp) for gm, gp in go_set):
            continue                                  # unmatched route → D1 already flagged it
        saw_envelope = saw_envelope or e['has_envelope']
        saw_params = saw_params or e['has_params']
        # request body
        if e['request_fields']:
            sn, info = _match([f['name'] for f in e['request_fields']],
                              name_sets, shadow, resolved)
            if sn is None:
                notes.append((e['file'], f'request body: no confident Go struct match '
                                         f'({info}); field drift needs fresh-eyes'))
            else:
                _compare_group(f'{e["file"]} request_body', f'request ({sn})',
                               e['request_fields'], info, True, drift)
        # each named response object
        for oname, ofields in e['response_objects'].items():
            sn, info = _match([f['name'] for f in ofields], name_sets, shadow, resolved)
            if sn is None:
                notes.append((e['file'], f'response object {oname}: no confident Go struct '
                                         f'match ({info}); field drift needs fresh-eyes'))
            else:
                _compare_group(f'{e["file"]} {oname}', f'response ({sn})',
                               ofields, info, False, drift)
    if saw_envelope:
        notes.append(('(global)', 'response envelope wrapper fields (status/data/message/…) '
                                  'are not drift-checked: fresh-eyes confirms the wrapper'))
    if saw_params:
        notes.append(('(global)', 'query/path params are handler-inline (c.Query/c.Params), '
                                  'not struct fields: fresh-eyes verifies them'))


# ═════════════════════ main ═════════════════════

def parse_args(argv):
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
    api_dir = pathlib.Path(positional[0]) if positional else pathlib.Path('bruno')
    return api_dir, src


def _bucket():
    return {'DRIFT': [], 'NOTE': []}


def main():
    api_dir, src = parse_args(sys.argv[1:])
    if not api_dir.exists():
        print(f"driftcheck: {api_dir} not found: author the collection with the bruno skill first")
        sys.exit(2)

    structs, routes, dup_names = parse_go(src)
    if structs is None:
        print(f"driftcheck: no Go source under --src {src!r}: drift needs the implementation "
              f"to compare against; nothing to check")
        sys.exit(2)
    resolved = {n: resolve_serializable(n, structs) for n in structs}
    name_sets = {n: {f['json'] for f in ser}
                 for n, ser in resolved.items() if ser and n not in dup_names}
    shadow = {f'{n}#{i}': {f['json'] for f in resolve_serializable(n, {**structs, n: v}) or []}
              for n, variants in dup_names.items() for i, v in enumerate(variants)}

    drift, notes = [], []
    endpoints, extra_set = load_bruno(api_dir, notes)

    check_route_drift(routes, endpoints, extra_set, drift, notes)
    check_field_drift(endpoints, routes, name_sets, shadow, resolved, drift, notes)

    if not endpoints:
        notes.append(('(global)', f'no request files found under {api_dir}, '
                                  'nothing to compare; needs fresh-eyes'))
    if dup_names:
        notes.append(('(global)', f'struct name(s) defined differently in >1 file '
                                  f'({", ".join(sorted(dup_names))}): excluded; needs fresh-eyes'))

    # ---- report (grouped by location, lint.py-style) ----
    by_file = defaultdict(_bucket)
    for fname, _level, msg in drift:
        by_file[fname]['DRIFT'].append(msg)
    for fname, msg in notes:
        by_file[fname]['NOTE'].append(msg)

    # special "(...)" buckets first, then per-file, sorted
    for fname in sorted(by_file, key=lambda k: (not k.startswith('('), k)):
        rec = by_file[fname]
        ds, nts = rec['DRIFT'], rec['NOTE']
        status = f'{len(ds)} DRIFT' if ds else 'OK'
        extra = f' / {len(nts)} note' if nts else ''
        print(f"{'✗' if ds else '✓'} {fname:46} {status}{extra}")
        for d in ds:
            print(f"    DRIFT  {d}")
        for n in nts:
            print(f"    NOTE   {n}")

    total = len(drift)
    print(f"\n{'DRIFT FOUND' if total else 'PASS'}: {total} drift / {len(notes)} note(s) "
          f"across {len(endpoints)} spec endpoint(s) + {len(routes)} Go route(s)")
    sys.exit(1 if total else 0)


if __name__ == '__main__':
    main()
