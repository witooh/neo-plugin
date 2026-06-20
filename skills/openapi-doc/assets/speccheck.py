#!/usr/bin/env python3
"""
speccheck.py — TRIPWIRE cross-checker for openapi-doc output (bruno/openapi.yaml vs Go code).
Zero install: pure Python 3 (stdlib only; uses PyYAML if present, else degrades the
spec-structure checks to NOTE). OPTIONALLY runs a real OpenAPI validator
(redocly / spectral / openapi-spec-validator) if one is on PATH. Layer-1 of the
openapi-doc skill's three-layer verify.

WHY THIS EXISTS
  openapi-doc emits a single-file OpenAPI 3.1 spec from Go source. This is the
  DETERMINISTIC, independent measure of the things a machine CAN count, so "verify
  passed" rests on evidence, not the writer's confidence.

PHILOSOPHY: TRIPWIRE, NOT GROUND TRUTH
    • ERROR = a mismatch the script is confident about (a route with no path operation,
              a dangling internal $ref, a struct field with no schema property, a required[]
              that contradicts the tags, a 2xx-less operation). The agent confirms each
              before fixing; a genuine false positive is skipped + noted, never blindly
              "fixed". Loop until ERRORs clear OR ~3 rounds stall.
    • NOTE  = something the script deliberately CANNOT verify confidently (error tracing
              + x-error-catalog, custom-type enums, a
              composed allOf schema, an ambiguous request/response context, a schema it
              could not match with confidence). Printed for the Layer-2 fresh-eyes
              verifier; each ends "needs fresh-eyes"; NOTEs never fail the run.
  Every uncertain case DEGRADES to a NOTE rather than a confident ERROR.

WHAT IT CHECKS  (ordered high→low confidence)
  S1 Structural-lite  root has openapi:3.* + info.title/version + paths; each operation
                      has >=1 response + well-formed parameters (name+in; in:path⇒required).
  S2 $ref resolution  every $ref is an INTERNAL pointer (#/components/...) that resolves to
                      a defined component; a file-path $ref (.yaml/.yml) is an ERROR — a
                      single-file spec must inline everything and use #/ pointers.
  S3 Coverage         every Go route path has a paths entry (missing=ERROR; orphan=NOTE).
  S4 Property count   per components.schemas entry, reverse-lookup the Go struct whose json
                      names ⊇ the schema's properties; flag a serializable field with no
                      property (undocumented) -> ERROR. allOf/no-match/ambiguous -> NOTE.
  S5 required[]       for mapped schemas, recompute M/O from tags vs required[] -> ERROR.
  S6 Status/security  each operation has a 2xx; security refs a defined scheme -> ERROR.
  + optional external OpenAPI validator (redocly/spectral → ERROR on fail;
    openapi-spec-validator → NOTE; a single-file spec resolves fully for all three).

  Example values are part of the YAML document, so "example validity" = the file parses
  (covered by S1 when PyYAML is present, and by the external validator when one is on PATH).

USAGE
  python3 speccheck.py bruno/openapi.yaml --src .       # the single-file spec directly
  python3 speccheck.py bruno/             --src ./svc   # a dir → resolves <dir>/openapi.yaml
  (--src also accepts --src=PATH; arg order is irrelevant. --src = repo root, where
   go.mod lives — usually ".")
Exit code: 0 = no ERROR (NOTEs/WARNINGs ok), 1 = at least one ERROR.
"""
import re, sys, json, pathlib, shutil, subprocess
from collections import defaultdict

try:
    import yaml                      # PyYAML — full spec-structure checks when present
    HAVE_YAML = True
except Exception:
    HAVE_YAML = False                # fallback: degrade S1/S2/S4/S5/S6 to NOTE


# ═════════════════════ Go source parsing ═════════════════════

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
        return None, 'empty-schema'
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


# ═════════════════════ Spec parsing (single-file) ═════════════════════

HTTP_METHODS = ('get', 'put', 'post', 'delete', 'patch', 'options', 'head', 'trace')
RE_REF = re.compile(r'\$ref:\s*["\']?([^"\'\s]+)')      # the FULL $ref target (internal #/... or, if wrongly present, a file path)
RE_PATHKEY = re.compile(r'^\s{2}(/\S*?):\s*$')          # a root paths key (2-space indent)
RE_OPENAPI_VER = re.compile(r'^openapi:\s*["\']?(\d+\.\d+(?:\.\d+)?)', re.M)


def load_yaml(path):
    """Parse one YAML file → Python object, or None on failure / no PyYAML."""
    if not HAVE_YAML:
        return None
    try:
        return yaml.safe_load(path.read_text(encoding='utf-8', errors='replace'))
    except Exception:
        return None


def resolve_root(target):
    """The single-file spec path: the openapi.yaml itself, or <dir>/openapi.yaml."""
    return target if target.is_file() else (target / 'openapi.yaml')


def schema_basename(ref):
    """'#/components/schemas/ConsentResponse' → 'ConsentResponse'."""
    return pathlib.PurePosixPath(ref).stem


def norm_path(p):
    """Normalise a URL path template for comparison: params → {}, trailing slash off."""
    p = re.sub(r'\{[^}]+\}', '{}', p)     # {id}  → {}
    p = re.sub(r':[^/]+', '{}', p)        # :id   → {}
    return ('/' + p.strip('/')) if p.strip('/') else '/'


def schema_props_required(data):
    """(own property names, required set, composed?) from a loaded schema object.
       Handles flat `properties`/`required` and inline `allOf` object members; an allOf
       member that is a $ref means the schema COMPOSES a base → composed=True."""
    props, required, composed = [], set(), False
    if not isinstance(data, dict):
        return props, required, composed

    def absorb(obj):
        nonlocal props, required
        if isinstance(obj.get('properties'), dict):
            props.extend(obj['properties'].keys())
        if isinstance(obj.get('required'), list):
            required.update(obj['required'])

    absorb(data)
    for member in data.get('allOf', []) or []:
        if isinstance(member, dict) and '$ref' in member:
            composed = True
        elif isinstance(member, dict):
            absorb(member)
    return props, required, composed


def _content_schema_refs(obj):
    """Yield every schema $ref under an object's content.*.schema (request body / response)."""
    out = []
    content = (obj or {}).get('content') or {}
    for media in content.values():
        sch = (media or {}).get('schema') or {}
        if isinstance(sch, dict) and '$ref' in sch:
            out.append(sch['$ref'])
        # array-of: items.$ref
        items = sch.get('items') if isinstance(sch, dict) else None
        if isinstance(items, dict) and '$ref' in items:
            out.append(items['$ref'])
    return out


# ═════════════════════ checks ═════════════════════

def check_internal_refs(root, data, errors, notes):
    """S2 — every $ref is an internal pointer (#/...) that resolves against the document.
       A file-path $ref (.yaml/.yml or any non-#/ path) is an ERROR in a single-file spec.
       Works by regex over the raw text (so it runs without PyYAML); pointer RESOLUTION
       needs the parsed `data` (degrades to NOTE when absent)."""
    text = root.read_text(encoding='utf-8', errors='replace') if root.exists() else ''
    for m in RE_REF.finditer(text):
        ref = m.group(1)
        if not ref.startswith('#/'):
            errors.append(('openapi.yaml', 'ERROR',
                           f'$ref "{ref}" is not an internal pointer — a single-file spec '
                           f'must inline everything and use "#/components/..."'))
            continue
        if data is None:
            continue                         # cannot resolve the target without a parser
        node, ok = data, True
        for part in ref[2:].split('/'):      # '#/components/schemas/X' → components, schemas, X
            part = part.replace('~1', '/').replace('~0', '~')
            if isinstance(node, dict) and part in node:
                node = node[part]
            else:
                ok = False
                break
        if not ok:
            errors.append(('openapi.yaml', 'ERROR',
                           f'$ref "{ref}" does not resolve to a defined component'))
    if data is None and '$ref' in text:
        notes.append(('openapi.yaml', 'no PyYAML — internal $ref targets not resolved '
                                      '(only the #/ form was checked); needs fresh-eyes'))


def load_root(root, errors, notes):
    """Load the single-file spec → (data, set of normalised path keys, securityScheme names).
       data is None when PyYAML is absent or the doc fails to parse (deep checks degrade)."""
    text = root.read_text(encoding='utf-8', errors='replace')

    # S1 root essentials (regex-cheap, works without PyYAML)
    mver = RE_OPENAPI_VER.search(text)
    if not mver:
        errors.append(('openapi.yaml', 'ERROR', 'missing/!malformed `openapi:` version'))
    elif not mver.group(1).startswith('3.'):
        errors.append(('openapi.yaml', 'ERROR', f'openapi version {mver.group(1)} is not 3.x'))

    data = load_yaml(root)
    if data is None:
        keys = {norm_path(m.group(1)) for m in RE_PATHKEY.finditer(text)}
        if HAVE_YAML:
            errors.append(('openapi.yaml', 'ERROR', 'openapi.yaml failed to parse as YAML'))
        else:
            notes.append(('openapi.yaml', 'no PyYAML — info/paths/components checks degraded; '
                                          'paths read by regex; needs fresh-eyes'))
        return None, keys, set()

    info = data.get('info') or {}
    if not info.get('title'):
        errors.append(('openapi.yaml', 'ERROR', 'info.title missing'))
    if not info.get('version'):
        errors.append(('openapi.yaml', 'ERROR', 'info.version missing'))
    paths = data.get('paths') or {}
    if not paths:
        errors.append(('openapi.yaml', 'ERROR', 'paths is empty'))
    keys = {norm_path(k) for k in paths.keys()}
    schemes = set((data.get('components', {}) or {}).get('securitySchemes', {}) or {})
    return data, keys, schemes


def check_coverage(routes, path_keys, errors, notes):
    """S3 — every Go route path is covered by a spec path key (suffix-tolerant of the
       server base). Missing route doc = ERROR; orphan spec path = NOTE (best-effort)."""
    if not routes:
        return
    route_norms = {norm_path(r['path']) for r in routes}
    for rn in sorted(route_norms):
        if not any(rn == k or rn.endswith(k) for k in path_keys):
            errors.append(('(coverage)', 'ERROR',
                           f'route path "{rn}" has no entry in the root `paths:`'))
    for k in sorted(path_keys):
        if not any(rn == k or rn.endswith(k) for rn in route_norms):
            notes.append(('(coverage)', f'spec path "{k}" matches no parsed route — '
                                       'verify the route exists (needs fresh-eyes)'))


def scan_operations(paths, security_schemes, errors, notes):
    """S1 (operation shape) + S6 (status/security) over every inline
       operation, and build schema→context(request/response) for S4/S5.
       `paths` = the document's `paths` dict. Returns {schema_name: set(['request','response'])}."""
    context = defaultdict(set)
    for pathkey, item in (paths or {}).items():
        if not isinstance(item, dict):
            continue
        ops = {m: item[m] for m in HTTP_METHODS if isinstance(item.get(m), dict)}
        if not ops:
            notes.append((f'paths {pathkey}', 'no HTTP-method operation under this path; needs fresh-eyes'))
        for method, op in ops.items():
            loc = f'paths {pathkey} [{method.upper()}]'
            # S1 parameters well-formed
            for p in op.get('parameters', []) or []:
                if not (isinstance(p, dict) and p.get('name') and p.get('in')):
                    errors.append((loc, 'ERROR', 'a parameter is missing name/in'))
                elif p.get('in') == 'path' and p.get('required') is not True:
                    errors.append((loc, 'ERROR', f'path param "{p.get("name")}" must be required:true'))
            # S6 responses + 2xx
            responses = op.get('responses') or {}
            if not responses:
                errors.append((loc, 'ERROR', 'operation has no responses'))
            elif not any(str(code).startswith('2') for code in responses):
                errors.append((loc, 'ERROR', 'operation has no 2xx success response'))
            # S6 security refs a defined scheme
            for sec in op.get('security', []) or []:
                for scheme in (sec or {}).keys():
                    if security_schemes and scheme not in security_schemes:
                        errors.append((loc, 'ERROR', f'security "{scheme}" not in components.securitySchemes'))
            # error-tracing NOTE when an x-error-catalog is present
            if any('x-error-catalog' in (r or {}) for r in responses.values() if isinstance(r, dict)):
                notes.append((loc, 'x-error-catalog present — sentinel tracing needs fresh-eyes'))
            # context for S4/S5
            for ref in _content_schema_refs(op.get('requestBody') or {}):
                context[schema_basename(ref)].add('request')
            for code, r in responses.items():
                for ref in _content_schema_refs(r if isinstance(r, dict) else {}):
                    context[schema_basename(ref)].add('response')
    return context


def check_schemas(schemas, context, name_sets, resolved, errors, notes):
    """S4 (property count vs struct) + S5 (required[] vs tags) per components.schemas entry.
       allOf-composed / no-confident-match / ambiguous-context all degrade to NOTE."""
    for name, sch in (schemas or {}).items():
        if not isinstance(sch, dict):
            continue
        loc = f'components.schemas.{name}'
        props, required, composed = schema_props_required(sch)
        if composed:
            notes.append((loc, 'allOf composition — embedded-field coverage + required[] '
                              'need fresh-eyes'))
            continue
        if not props:
            continue   # enum-only / scalar / pure-$ref schema — nothing to count
        struct_name, info = map_names_to_struct(props, name_sets, resolved)
        if struct_name is None:
            notes.append((loc, f'no confident struct match ({info}); property count + '
                              'required[] need fresh-eyes'))
            continue
        ctx = context.get(name) or context.get(struct_name) or set()
        # S4 — every serializable struct field must have a property
        prop_set = set(props)
        for f in info:
            if f['json'] not in prop_set:
                errors.append((loc, 'ERROR',
                               f'{struct_name}.{f["json"]} is serializable but has no property '
                               f'(undocumented field)'))
        # S5 — required[] membership vs tags (needs a known request/response context)
        if ctx == {'request'} or ctx == {'response'}:
            is_req = ctx == {'request'}
            by_json = {f['json']: f for f in info}
            for jn, f in by_json.items():
                if jn not in prop_set:
                    continue
                expect = compute_mo(f, is_req)
                listed = jn in required
                if expect == 'M' and not listed:
                    errors.append((loc, 'ERROR', f'`{jn}`: tags → M but not in required[]'))
                elif expect == 'O' and listed:
                    errors.append((loc, 'ERROR', f'`{jn}`: tags → O but listed in required[]'))
        else:
            notes.append((loc, f'request/response context ambiguous ({sorted(ctx) or "unknown"}) '
                              '— required[] M/O needs fresh-eyes'))


# ═════════════════════ optional external validator ═════════════════════

def run_external_validator(root, errors, notes):
    """If a real OpenAPI validator is on PATH, run it against the spec. A single-file spec
       resolves fully for all three. redocly/spectral → ERROR on failure;
       openapi-spec-validator → NOTE on failure (kept advisory)."""
    candidates = [
        ('redocly', ['redocly', 'lint', str(root)], 'ERROR'),
        ('spectral', ['spectral', 'lint', str(root)], 'ERROR'),
        ('openapi-spec-validator', ['openapi-spec-validator', str(root)], 'NOTE'),
    ]
    for name, cmd, sev in candidates:
        if not shutil.which(cmd[0]):
            continue
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except Exception as e:
            notes.append(('(validator)', f'{name} could not be run ({e!r}); needs fresh-eyes'))
            return
        if proc.returncode == 0:
            notes.append(('(validator)', f'{name}: clean'))
        else:
            tail = (proc.stdout or proc.stderr or '').strip().splitlines()[-8:]
            snippet = ' | '.join(tail)[:500]
            if sev == 'ERROR':
                errors.append(('(validator)', 'ERROR', f'{name} reported issues: {snippet}'))
            else:
                notes.append(('(validator)', f'{name} reported issues (advisory): {snippet}'))
        return   # only the first available validator runs
    notes.append(('(validator)', 'no OpenAPI validator on PATH (redocly/spectral/'
                                 'openapi-spec-validator) — structural validation is tripwire-only'))


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
    target = pathlib.Path(positional[0]) if positional else pathlib.Path('bruno/openapi.yaml')
    return target, src


def _bucket():
    return {'ERROR': [], 'NOTE': []}


def main():
    target, src = parse_args(sys.argv[1:])
    if not target.exists():
        print(f"speccheck: {target} not found — nothing to check")
        sys.exit(0)

    root = resolve_root(target)
    if not root.exists():
        print("speccheck: no openapi.yaml — nothing to check")
        sys.exit(0)

    structs, routes, dup_names = parse_go(src)
    if structs is None:
        name_sets = resolved = None
    else:
        resolved = {n: resolve_serializable(n, structs) for n in structs}
        name_sets = {n: {f['json'] for f in ser}
                     for n, ser in resolved.items() if ser and n not in dup_names}

    errors, notes = [], []

    # S1 root essentials + paths/security
    data, path_keys, security_schemes = load_root(root, errors, notes)

    # S2 internal $ref resolution (regex over the text; resolution needs the parsed doc)
    check_internal_refs(root, data, errors, notes)

    # S3 coverage
    if name_sets is None:
        notes.append(('(global)', f'no Go source under --src {src!r} — coverage/property/'
                                  'required checks skipped; needs fresh-eyes'))
    else:
        check_coverage(routes, path_keys, errors, notes)
    if dup_names:
        notes.append(('(global)', f'struct name(s) defined differently in >1 file '
                                  f'({", ".join(sorted(dup_names))}) — excluded; needs fresh-eyes'))
    if not HAVE_YAML:
        notes.append(('(global)', 'PyYAML not installed — structure checks degraded to '
                                 'regex/NOTE; install pyyaml or a validator for full L1'))

    # S1 operation shape + S6 + context for S4/S5, then S4 + S5 schemas
    n_ops = n_schemas = 0
    if data is not None:
        paths = data.get('paths') or {}
        schemas = (data.get('components', {}) or {}).get('schemas') or {}
        n_ops = sum(1 for item in paths.values() if isinstance(item, dict)
                    for m in HTTP_METHODS if isinstance(item.get(m), dict))
        n_schemas = len(schemas)
        context = scan_operations(paths, security_schemes, errors, notes)
        if name_sets is not None:
            check_schemas(schemas, context, name_sets, resolved, errors, notes)

    # optional external validator
    run_external_validator(root, errors, notes)

    # ---- report (grouped by location, lint.py-style) ----
    by_file = defaultdict(_bucket)
    for fname, _level, msg in errors:
        by_file[fname]['ERROR'].append(msg)
    for fname, msg in notes:
        by_file[fname]['NOTE'].append(msg)

    # special "(...)" buckets first, then openapi.yaml / paths / components, sorted
    for fname in sorted(by_file, key=lambda k: (not k.startswith('('), k)):
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
          f"across {n_ops} operation(s) + {n_schemas} schema(s)")
    sys.exit(1 if total_err else 0)


if __name__ == '__main__':
    main()
