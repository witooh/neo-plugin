#!/usr/bin/env python3
"""
speccheck.py — TRIPWIRE drift checker for the api-doc chain (Go code vs the custom-YAML
api-spec under docs/api/). Zero install: pure Python 3 (stdlib + PyYAML to parse the spec).
Layer-1 of the openapi-doc skill's three-layer verify.

WHY THIS EXISTS
  The custom-YAML api-spec at docs/api/ is the SOURCE OF TRUTH, authored spec-first (before
  code) by neo's Architect. openapi-doc no longer GENERATES anything — it scans the Go code
  and reports where the implementation has DRIFTED from that contract. This is the
  DETERMINISTIC, independent measure a machine CAN count, so the Architect's sync-back rests
  on evidence, not the writer's confidence. (It writes no file; it reads docs/api/*.yaml + Go.)

PHILOSOPHY: TRIPWIRE, NOT GROUND TRUTH
    • DRIFT = a Go-vs-spec mismatch the script is confident about (a route on one side only,
              a serializable field with no spec row, a spec field absent from the struct, an
              M/O or type that disagree on a confidently-matched field). The Architect
              confirms each before reconciling the YAML; a genuine false positive — e.g. a
              spec-first endpoint not built yet, or an intentionally-undocumented route — is
              confirmed + skipped, never blindly "fixed". Loop until DRIFT clears OR ~3 rounds
              stall, then escalate.
    • NOTE  = something the script deliberately CANNOT decide confidently (a field group it
              could not match to a Go struct, the response envelope wrapper, handler-inline
              query/path params, error-status tracing). Printed for the Layer-2 fresh-eyes
              verifier; each ends "needs fresh-eyes"; NOTEs never fail the run.
  Every uncertain case DEGRADES to a NOTE rather than a confident DRIFT.

WHAT IT CHECKS  (ordered high→low confidence)
  D1 Route drift     every Go route is documented by a spec endpoint, and every spec endpoint
                     is implemented by a Go route (matched by method + normalised path, base-
                     URL-suffix-tolerant). _meta.extra_endpoints (e.g. a health probe) count
                     as documented. A one-sided route = DRIFT.
  D2 Field drift     per matched endpoint, reverse-lookup the Go struct whose json names ⊇ the
                     spec field group (request_body.fields → request struct; each
                     responses[].objects.<Name> → that object's struct), then compare:
                       • presence — a serializable Go field with no spec row (undocumented) OR
                         a spec field absent from the struct (stale) = DRIFT;
                       • M/O      — compute_mo(tags) vs the spec `mandatory` (M|O) = DRIFT;
                       • type     — go→spec-type mapping vs the spec `type` (confident cases
                         only: bool/[]T/numeric; struct/map/custom/time → skipped) = DRIFT.
                     No confident struct match / envelope wrapper / inline params → NOTE.

USAGE
  python3 speccheck.py docs/api --src .          # spec dir + Go root (where go.mod lives)
  python3 speccheck.py            --src ./svc     # api-dir defaults to docs/api
  (--src also accepts --src=PATH; arg order is irrelevant.)
Exit code: 0 = no DRIFT (NOTEs/WARNINGs ok), 1 = at least one DRIFT.
"""
import re, sys, json, pathlib
from collections import defaultdict

try:
    import yaml                      # PyYAML — required to parse the custom-YAML spec
    HAVE_YAML = True
except Exception:
    HAVE_YAML = False                # no parser → cannot diff; degrade the whole run to a NOTE


# ═════════════════════ Go source parsing (the reused engine) ═════════════════════

RE_FIELD = re.compile(
    r'^\s*([A-Za-z_]\w*)\s+([\*\[\]\w.]+)\s*(?:`([^`]*)`)?\s*(?://.*)?$')
RE_EMBED = re.compile(r'^\s*(\*?[A-Za-z_][\w.]*)\s*(?://.*)?$')
RE_JSON_TAG = re.compile(r'json:"([^"]*)"')
RE_REQUIRED = re.compile(r'(?:validate|binding):"[^"]*\brequired\b[^"]*"')
RE_STRUCT = re.compile(r'type\s+(\w+)\s*(?:\[[^\]]*\])?\s+struct\s*\{')
RE_ROUTE = re.compile(
    r'\b\w+\.(Get|Post|Put|Patch|Delete|Options|Head)\s*\(\s*"([^"]*)"\s*,\s*([^)]+)\)',
    re.I)
RE_HANDLER = re.compile(r'^[\w.]+\.([A-Z]\w*)$')


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


def parse_go(src_root):
    """Return (structs, routes, dup_names). Skips _test.go and vendor/.
       Returns (None, [], set()) if no Go files found."""
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
                dup_names.add(name)
            structs[name] = fields
        for rm in RE_ROUTE.finditer(text):
            hm = RE_HANDLER.match(rm.group(3).strip())
            if hm:
                routes.append({'method': rm.group(1).upper(),
                               'path': rm.group(2), 'handler': hm.group(1)})
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
    """M/O from struct tags (openapi-doc-template.md § M/O Classification)."""
    if is_request:
        if field['required']:
            return 'M'
        if field['pointer'] or field['omitempty'] or field['bool']:
            return 'O'
        return 'M'
    return 'O' if field['pointer'] else 'M'


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
       Tier 1: the strict-subset rule above (want ⊆ struct, tight) — highest confidence.
       Tier 2 (only when Tier 1 fails): a SAFE best-overlap fallback so a *stale* spec field
       (the struct lost a field the spec still lists) is still caught — but only when the
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
    """Map a Go field type to the custom-YAML `type` vocab (String/Number/Boolean/Object/Array).
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


# ═════════════════════ custom-YAML api-spec parsing ═════════════════════

def norm_path(p):
    """Normalise a URL path template for comparison: params → {}, trailing slash off."""
    p = re.sub(r'\{[^}]+\}', '{}', p)     # {id}  → {}
    p = re.sub(r':[^/]+', '{}', p)        # :id   → {}
    return ('/' + p.strip('/')) if p.strip('/') else '/'


def _field_rows(rows):
    """Normalise a YAML field list → [{name, type, mandatory}] (drops malformed rows)."""
    out = []
    for r in rows or []:
        if isinstance(r, dict) and r.get('name'):
            out.append({'name': r['name'], 'type': r.get('type'),
                        'mandatory': r.get('mandatory')})
    return out


def load_spec(api_dir):
    """Parse the custom-YAML api-spec tree → (endpoints, extra_set).
       endpoints = [{file, method, npath, request_fields, response_objects{Name:[rows]},
                     has_envelope, has_params}]; extra_set = {(METHOD, npath)} from
                     _meta.extra_endpoints (documented index-only rows; Go-side allowance)."""
    root = pathlib.Path(api_dir)
    endpoints, extra_set = [], set()

    meta_path = root / '_meta.yaml'
    if meta_path.exists():
        meta = yaml.safe_load(meta_path.read_text(encoding='utf-8', errors='replace')) or {}
        for x in (meta.get('extra_endpoints') or []):
            if isinstance(x, dict) and x.get('method') and x.get('path'):
                extra_set.add((str(x['method']).upper(), norm_path(str(x['path']))))

    for fp in sorted(root.rglob('*.yaml')):
        if fp.name == '_meta.yaml':
            continue
        try:
            doc = yaml.safe_load(fp.read_text(encoding='utf-8', errors='replace'))
        except Exception:
            doc = None
        if not isinstance(doc, dict) or not doc.get('method') or not doc.get('path'):
            continue
        rel = str(fp.relative_to(root))
        rb = doc.get('request_body') or {}
        response_objects, has_envelope = {}, False
        for resp in (doc.get('responses') or []):
            if not isinstance(resp, dict):
                continue
            if resp.get('fields'):
                has_envelope = True
            for oname, ofields in (resp.get('objects') or {}).items():
                response_objects.setdefault(oname, _field_rows(ofields))
        endpoints.append({
            'file': rel,
            'method': str(doc['method']).upper(),
            'npath': norm_path(str(doc['path'])),
            'request_fields': _field_rows(rb.get('fields')),
            'response_objects': response_objects,
            'has_envelope': has_envelope,
            'has_params': bool(doc.get('query_params') or doc.get('path_params')),
        })
    return endpoints, extra_set


# ═════════════════════ drift checks ═════════════════════

def _path_match(a, b):
    """method-equal paths match base-URL-suffix-tolerantly (the '/' prefix guards boundaries)."""
    return a == b or a.endswith(b) or b.endswith(a)


def check_route_drift(routes, endpoints, extra_set, drift, notes):
    """D1 — bidirectional route presence (matched by method + normalised path)."""
    go_set = sorted({(r['method'], norm_path(r['path'])) for r in routes})
    spec_cover = {(e['method'], e['npath']) for e in endpoints} | extra_set

    # Go route with no spec endpoint = undocumented (or intentionally-skipped) route
    for gm, gp in go_set:
        if not any(gm == sm and _path_match(gp, sp) for sm, sp in spec_cover):
            drift.append(('(routes)', 'DRIFT',
                          f'Go route {gm} {gp} has no endpoint in docs/api/ '
                          f'(undocumented route — add a spec file, or confirm it is '
                          f'intentionally undocumented and skip)'))

    # spec endpoint (a real file) with no Go route = unimplemented / removed
    for e in endpoints:
        if not any(e['method'] == gm and _path_match(e['npath'], gp) for gm, gp in go_set):
            drift.append(('(routes)', 'DRIFT',
                          f'spec endpoint {e["method"]} {e["npath"]} ({e["file"]}) has no '
                          f'matching Go route (unimplemented [spec-first pending] or a '
                          f'removed route — confirm)'))


def _compare_group(loc, kind, spec_fields, go_fields, is_request, drift):
    """Field-level drift for one matched group (request body / a response object)."""
    spec_by_name = {f['name']: f for f in spec_fields}
    go_by_json = {f['json']: f for f in go_fields}

    # presence — Go field with no spec row (undocumented)
    for jn in go_by_json:
        if jn not in spec_by_name:
            drift.append((loc, 'DRIFT',
                          f'{kind}: Go field `{jn}` is serializable but has no spec row '
                          f'(undocumented field)'))
    # presence — spec row with no Go field (stale)
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
                          f'{kind}: `{nm}` — Go tags → {expect} but spec says '
                          f'{sf["mandatory"]} (M/O drift)'))
        go_t = go_to_spec_type(gf['type'])
        if not type_compatible(go_t, sf.get('type')):
            drift.append((loc, 'DRIFT',
                          f'{kind}: `{nm}` — Go type {gf["type"]} (→ {go_t}) but spec says '
                          f'{sf.get("type")} (type drift)'))


def check_field_drift(endpoints, routes, name_sets, resolved, drift, notes):
    """D2 — per matched endpoint, reverse-lookup the Go struct for each spec field group
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
            sn, info = match_for_drift([f['name'] for f in e['request_fields']],
                                       name_sets, resolved)
            if sn is None:
                notes.append((e['file'], f'request body: no confident Go struct match '
                                         f'({info}); field drift needs fresh-eyes'))
            else:
                _compare_group(f'{e["file"]} request_body', f'request ({sn})',
                               e['request_fields'], info, True, drift)
        # each named response object
        for oname, ofields in e['response_objects'].items():
            sn, info = match_for_drift([f['name'] for f in ofields], name_sets, resolved)
            if sn is None:
                notes.append((e['file'], f'response object {oname}: no confident Go struct '
                                         f'match ({info}); field drift needs fresh-eyes'))
            else:
                _compare_group(f'{e["file"]} {oname}', f'response ({sn})',
                               ofields, info, False, drift)
    if saw_envelope:
        notes.append(('(global)', 'response envelope wrapper fields (status/data/message/…) '
                                  'are not drift-checked — fresh-eyes confirms the wrapper'))
    if saw_params:
        notes.append(('(global)', 'query/path params are handler-inline (c.Query/c.Params), '
                                  'not struct fields — fresh-eyes verifies them'))


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
    api_dir = pathlib.Path(positional[0]) if positional else pathlib.Path('docs/api')
    return api_dir, src


def _bucket():
    return {'DRIFT': [], 'NOTE': []}


def main():
    api_dir, src = parse_args(sys.argv[1:])
    if not api_dir.exists():
        print(f"speccheck: {api_dir} not found — author the api-spec (run neo) first")
        sys.exit(0)
    if not HAVE_YAML:
        print("speccheck: PyYAML not installed — cannot parse the api-spec, drift not checked\n"
              "    NOTE   install pyyaml to enable the L1 drift check; needs fresh-eyes")
        sys.exit(0)

    structs, routes, dup_names = parse_go(src)
    if structs is None:
        print(f"speccheck: no Go source under --src {src!r} — drift needs the implementation "
              f"to compare against; nothing to check")
        sys.exit(0)
    resolved = {n: resolve_serializable(n, structs) for n in structs}
    name_sets = {n: {f['json'] for f in ser}
                 for n, ser in resolved.items() if ser and n not in dup_names}

    endpoints, extra_set = load_spec(api_dir)
    drift, notes = [], []

    check_route_drift(routes, endpoints, extra_set, drift, notes)
    check_field_drift(endpoints, routes, name_sets, resolved, drift, notes)

    if not endpoints:
        notes.append(('(global)', f'no endpoint YAML files found under {api_dir} — '
                                  'nothing to compare; needs fresh-eyes'))
    if dup_names:
        notes.append(('(global)', f'struct name(s) defined differently in >1 file '
                                  f'({", ".join(sorted(dup_names))}) — excluded; needs fresh-eyes'))

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
    print(f"\n{'DRIFT FOUND' if total else 'PASS'} — {total} drift / {len(notes)} note(s) "
          f"across {len(endpoints)} spec endpoint(s) + {len(routes)} Go route(s)")
    sys.exit(1 if total else 0)


if __name__ == '__main__':
    main()
