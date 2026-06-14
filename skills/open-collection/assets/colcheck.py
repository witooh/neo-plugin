#!/usr/bin/env python3
"""
colcheck.py — TRIPWIRE cross-checker for `open-collection` output (Bruno OpenCollection ↔ docs/api markdown OR docs/openapi spec).
Zero install: pure Python 3 (stdlib only; uses PyYAML if present, else a safe fallback).
Layer-1 of the open-collection skill's three-layer verify.

WHY THIS EXISTS
  open-collection derives a *runnable* collection from the `docs/api/` markdown
  (the single source of truth, already verified against Go by the `api-doc` skill).
  So this script verifies the collection against the MARKDOWN — never against Go.
  The thing that can silently drift is the transform: a request whose URL, method,
  path-params, or runnable body no longer matches the markdown it came from. This is
  the DETERMINISTIC, independent measure of that, so "verify passed" rests on
  evidence, not the writer's confidence (same principle as neo's lint.py/docverify.py).

PHILOSOPHY: TRIPWIRE, NOT GROUND TRUTH
  A flag RAISES A SIGNAL for a human/agent to inspect — it does not "prove" wrong:
    • ERROR = a mismatch the script is confident about (a markdown endpoint with no
              request file, a method/path/body that diverges from the markdown, a url
              path-param not declared, a {{var}} with no environment entry). The agent
              confirms each before fixing; a genuine false positive is skipped + noted,
              never blindly "fixed". Loop until ERRORs clear OR ~3 rounds stall.
    • NOTE  = something the script deliberately CANNOT verify confidently (auth
              semantic mapping, header completeness, env-var *values*). Printed for the
              Layer-2 fresh-eyes verifier; each ends in "needs fresh-eyes"; never fails.

WHAT IT CHECKS  (collection ↔ markdown; ordered high→low confidence)
  K1 Coverage   every docs/api/<group>/<endpoint>.md has a request .yml & vice versa
                (missing / orphan = ERROR); every group with endpoints has a folder.yml.
  K2 Method/Path  request http.method == markdown **Method**; http.url path (minus the
                {{...}} prefix) == markdown **Path** (with {id} normalised to :id).
  K3 Body       if the markdown has a `## Request Example`, http.body.data must equal it
                (parsed JSON compare); body present on exactly one side = ERROR.
  K4 Structure  every request .yml has info.name + http.method + http.url · url path
                params (:name) ⇔ params(type: path) · http.body.data parses · seq unique
                per folder.
  K5 Env        every {{var}} a request references (excluding {{process.env.*}}) is
                defined in some environments/*.yml.

  NOTE sources: auth mapping (markdown **Auth** → folder/request auth) is judgment;
  a missing PyYAML/yq degrades the http-block checks to NOTE; no environments/ dir
  degrades K5 to a NOTE.

DUAL SOURCE
  open-collection can derive the collection from the `docs/api/` markdown OR a
  `docs/openapi/` OpenAPI 3.2 split spec (the openapi-doc skill's output). Pass --md or
  --spec to pick; with neither, the spec is preferred when `docs/openapi/openapi.yaml`
  exists, else markdown. In spec mode coverage + body fidelity match the collection to the
  spec by (method, path) — request files are named by operation, not by stem — while the
  per-request structure (K4) and env (K5) checks are reused unchanged. Spec mode needs PyYAML.

USAGE
  python3 colcheck.py <collection-root>          --md docs/api/        # vs markdown
  python3 colcheck.py <collection-root>          --spec docs/openapi/  # vs openapi spec
  python3 colcheck.py <collection>/consent/x.yml --md docs/api/        # one request file
  (--md / --spec also accept =PATH; arg order is irrelevant.)
Exit code: 0 = no ERROR (NOTEs/WARNINGs ok), 1 = at least one ERROR.
"""
import re, sys, json, pathlib
from collections import defaultdict

try:
    import yaml                      # PyYAML — full YAML structural checks when present
    HAVE_YAML = True
except Exception:
    HAVE_YAML = False                # fallback: degrade http-block checks to NOTE


RE_JSON_BLOCK = re.compile(r'```json\s*\n(.*?)```', re.S)
RE_LEADING_VAR = re.compile(r'^\{\{[^}]*\}\}')           # a leading {{baseUrl}}-style token in a url
RE_VAR = re.compile(r'\{\{\s*([^}]+?)\s*\}\}')           # any {{var}} reference
RE_MD_METHOD = re.compile(r'(?im)^\s*[-*]\s*\*\*Method:\*\*\s*`?([A-Za-z]+)`?')
RE_MD_PATH   = re.compile(r'(?im)^\s*[-*]\s*\*\*Path:\*\*\s*`([^`]+)`')
RE_MD_AUTH   = re.compile(r'(?im)^\s*[-*]\s*\*\*Auth:\*\*\s*(.+?)\s*$')


# ───────────────────────── markdown source reading ─────────────────────────

def split_sections(md):
    """{heading_text: section_body} split on `## ` (H2) headings; text before the first
       H2 is keyed ''. Heading text lowercased + trimmed."""
    parts = re.split(r'^##\s+(.+?)\s*$', md, flags=re.M)
    out = {'': parts[0]}
    for i in range(1, len(parts), 2):
        out[parts[i].strip().lower()] = parts[i + 1]
    return out


def read_md_endpoint(path):
    """Pull the runnable bits out of one docs/api endpoint markdown file."""
    text = path.read_text(encoding='utf-8', errors='replace')
    m, p, a = RE_MD_METHOD.search(text), RE_MD_PATH.search(text), RE_MD_AUTH.search(text)
    out = {'method': m.group(1).upper() if m else None,
           'path': p.group(1).strip() if p else None,
           'auth': a.group(1).strip().strip('`').strip() if a else None,
           'body_raw': None, 'body_json': None}
    secs = split_sections(text)
    if 'request example' in secs:
        blocks = RE_JSON_BLOCK.findall(secs['request example'])
        if blocks:
            out['body_raw'] = blocks[0].strip()
            try:
                out['body_json'] = json.loads(out['body_raw'])
            except Exception:
                out['body_json'] = '__INVALID__'
    return out


def collect_md_endpoints(md_root):
    """{ '<group>/<stem>': Path } for every endpoint markdown (index.md excluded)."""
    out = {}
    for f in sorted(md_root.rglob('*.md')):
        if f.name == 'index.md':
            continue
        out[f.relative_to(md_root).with_suffix('').as_posix()] = f
    return out


# ───────────────────────── OpenAPI spec source reading ─────────────────────────
# open-collection is dual-source: it can derive the collection from the `docs/api/`
# markdown (above) OR from a `docs/openapi/` OpenAPI 3.2 split spec. In spec mode the
# collection is matched to the spec by (method, path) — the request files Bruno's
# importer emits are named by operation, not by the markdown stem — so coverage + body
# fidelity compare operations, while the per-request structural (K4) and env (K5) checks
# are reused unchanged. Needs PyYAML; without it spec mode degrades to NOTE.

def norm_template(p):
    """A URL path template normalised for comparison: params → {}, single leading slash."""
    p = re.sub(r'\{[^}]+\}', '{}', p or '')      # {id} → {}
    p = re.sub(r':[^/]+', '{}', p)               # :id  → {}
    return '/' + p.strip('/') if p.strip('/') else '/'


def _url_path(url):
    """The path part of a server url ('http://h/api/v1' → '/api/v1'; '/api/v1' → '/api/v1')."""
    m = re.match(r'^[a-zA-Z][\w+.-]*://[^/]+(/.*)?$', url or '')
    return (m.group(1) or '') if m else (url or '')


def _spec_auth(op):
    """Operation security → the markdown-style **Auth** label, for the auth NOTE."""
    sec = op.get('security')
    if sec == []:
        return 'None'
    if isinstance(sec, list) and sec:
        names = [k for s in sec for k in (s or {}).keys()]
        low = ' '.join(names).lower()
        if 'bearer' in low:
            return 'Bearer token'
        if 'apikey' in low or 'api_key' in low or 'api-key' in low:
            return 'API Key'
        return names[0] if names else None
    return None


def _spec_body(op):
    """The runnable request body example from an operation's requestBody, if any."""
    content = ((op.get('requestBody') or {}).get('content')) or {}
    media = content.get('application/json') or (next(iter(content.values()), {}) if content else {})
    val = None
    examples = (media or {}).get('examples') or {}
    if isinstance(examples, dict) and examples:
        default = examples.get('default') or next(iter(examples.values()), {})
        if isinstance(default, dict):
            val = default.get('value')
    if val is None and isinstance(media, dict):
        val = media.get('example')
    return {'body_json': val, 'body_raw': json.dumps(val) if val is not None else None}


def collect_spec_ops(spec_root):
    """[{method, rel_path, full_path, auth, body_json, body_raw}] for every operation in a
       docs/openapi split spec. Returns None when PyYAML is absent or the root is missing."""
    if not HAVE_YAML:
        return None
    root = spec_root if spec_root.is_file() else (spec_root / 'openapi.yaml')
    base = root.parent
    if not root.exists():
        return None
    try:
        rootdoc = yaml.safe_load(root.read_text(encoding='utf-8', errors='replace'))
    except Exception:
        return None
    if not isinstance(rootdoc, dict):
        return None
    servers = rootdoc.get('servers') or []
    server_base = _url_path(servers[0].get('url')) if servers and isinstance(servers[0], dict) else ''
    ops = []
    for pathkey, entry in (rootdoc.get('paths') or {}).items():
        pathdoc = None
        if isinstance(entry, dict) and '$ref' in entry:
            ref = entry['$ref'].split('#')[0]
            pf = (base / ref).resolve()
            if pf.exists():
                try:
                    pathdoc = yaml.safe_load(pf.read_text(encoding='utf-8', errors='replace'))
                except Exception:
                    pathdoc = None
        elif isinstance(entry, dict):
            pathdoc = entry
        if not isinstance(pathdoc, dict):
            continue
        for method in ('get', 'put', 'post', 'delete', 'patch', 'options', 'head'):
            op = pathdoc.get(method)
            if not isinstance(op, dict):
                continue
            ops.append({'method': method.upper(), 'rel_path': pathkey,
                        'full_path': server_base.rstrip('/') + pathkey,
                        'auth': _spec_auth(op), **_spec_body(op)})
    return ops


def _op_matches(op, method, req_norm):
    """True if a request (method, normalised path) matches a spec op (suffix-tolerant of
       the server base, since the request URL may or may not carry the /api/v1 prefix)."""
    if op['method'] != method:
        return False
    rel, full = norm_template(op['rel_path']), norm_template(op['full_path'])
    return req_norm in (rel, full) or req_norm.endswith(rel)


def match_spec_op(spec_ops, method, req_norm):
    """The unique spec op matching this request, shaped like a markdown endpoint dict
       (path=None so the path-string compare is skipped — matching already proved it)."""
    if not spec_ops:
        return None
    cand = [op for op in spec_ops if _op_matches(op, (method or '').upper(), req_norm)]
    if len(cand) == 1:
        op = cand[0]
        return {'method': op['method'], 'path': None, 'auth': op['auth'],
                'body_json': op['body_json'], 'body_raw': op['body_raw']}
    return None


# ───────────────────────── YAML request reading ─────────────────────────

def read_request_yaml(path):
    """Parse one request .yml. With PyYAML: structured read. Without: mark 'manual' so
       the caller degrades http-block checks to a NOTE."""
    text = path.read_text(encoding='utf-8', errors='replace')
    out = {'ok': True, 'mode': 'yaml' if HAVE_YAML else 'manual', 'text': text,
           'info': {}, 'http': {}, 'method': None, 'url': None,
           'body_type': None, 'body_data': None, 'params': []}
    if HAVE_YAML:
        try:
            d = yaml.safe_load(text)
        except Exception as e:
            out['ok'] = False
            out['error'] = type(e).__name__
            return out
        if not isinstance(d, dict):
            out['ok'] = False
            out['error'] = 'top level is not a mapping'
            return out
        out['info'] = d.get('info') if isinstance(d.get('info'), dict) else {}
        out['http'] = d.get('http') if isinstance(d.get('http'), dict) else {}
        out['method'] = out['http'].get('method')
        out['url'] = out['http'].get('url') if isinstance(out['http'].get('url'), str) else None
        body = out['http'].get('body') if isinstance(out['http'].get('body'), dict) else {}
        out['body_type'] = body.get('type')
        out['body_data'] = body.get('data') if isinstance(body.get('data'), str) else None
        params = out['http'].get('params')
        out['params'] = [p for p in params if isinstance(p, dict)] if isinstance(params, list) else []
    return out


def collect_requests(target):
    """[request .yml files] under a collection root — excludes opencollection.yml,
       folder.yml, and anything under environments/. Recursive so nested groups count."""
    if target.is_file():
        return [target]
    files = []
    for f in sorted(target.rglob('*.yml')):
        if f.name in ('opencollection.yml', 'folder.yml'):
            continue
        if 'environments' in f.relative_to(target).parts:
            continue
        files.append(f)
    return files


def collect_env_vars(root):
    """Set of variable names defined across environments/*.yml, or None if no env dir."""
    env_dir = root / 'environments'
    if not env_dir.is_dir():
        return None
    names = set()
    for f in sorted(env_dir.glob('*.yml')):
        text = f.read_text(encoding='utf-8', errors='replace')
        parsed = False
        if HAVE_YAML:
            try:
                d = yaml.safe_load(text)
            except Exception:
                d = None
            if isinstance(d, dict) and isinstance(d.get('variables'), list):
                for v in d['variables']:
                    if isinstance(v, dict) and v.get('name'):
                        names.add(str(v['name']))
                parsed = True
        if not parsed:                                   # fallback: grep "- name: X"
            for m in re.finditer(r'^\s*-\s*name:\s*([^\s#]+)', text, re.M):
                names.add(m.group(1).strip().strip('"\''))
    return names


# ───────────────────────── path helpers ─────────────────────────

def norm_yaml_path(url):
    """A request URL minus its leading {{baseUrl}}-style token: '/api/v1/x/:id'."""
    return RE_LEADING_VAR.sub('', (url or '').strip()).strip()


def md_path_to_colon(p):
    """Markdown documented path ({id}) → Bruno URL form (:id)."""
    return re.sub(r'\{([A-Za-z_]\w*)\}', r':\1', (p or '').strip())


# ───────────────────────── checks ─────────────────────────

def check_coverage(md_keys, yml_keys, col_root, errors):
    for k in sorted(md_keys - yml_keys):
        errors.append((k + '.yml', 'ERROR',
                       f'markdown endpoint "{k}.md" has no request file in the collection'))
    for k in sorted(yml_keys - md_keys):
        errors.append((k + '.yml', 'ERROR',
                       f'request file has no matching markdown endpoint "{k}.md" (orphan)'))
    groups = {k.rsplit('/', 1)[0] for k in md_keys if '/' in k}
    for g in sorted(groups):
        if not (col_root / g / 'folder.yml').exists():
            errors.append((g + '/folder.yml', 'ERROR',
                           f'group "{g}" has endpoints but no folder.yml'))


def check_coverage_spec(spec_ops, request_files, col_root, errors):
    """Spec-mode coverage: every spec operation has a request file, and no request file
       matches no operation. Matched by (method, suffix-tolerant path)."""
    reqs = []
    for f in request_files:
        r = read_request_yaml(f)
        if r['ok'] and r['mode'] == 'yaml' and r['method'] and r['url']:
            reqs.append(((r['method'] or '').upper(),
                         norm_template(norm_yaml_path(r['url'])),
                         f.relative_to(col_root).as_posix()))
    for op in spec_ops:
        if not any(_op_matches(op, m, n) for m, n, _ in reqs):
            errors.append(('(coverage)', 'ERROR',
                           f'spec operation {op["method"]} {op["rel_path"]} has no request file'))
    for m, n, rel in reqs:
        if not any(_op_matches(op, m, n) for op in spec_ops):
            errors.append((rel, 'ERROR', f'request {m} {n} matches no spec operation (orphan)'))


def check_request(path, col_root, resolve_source, env_vars, errors, notes, seq_seen):
    rel = path.relative_to(col_root).as_posix()
    key = rel[:-4] if rel.endswith('.yml') else rel
    r = read_request_yaml(path)
    if not r['ok']:
        errors.append((rel, 'ERROR', f'request YAML did not parse ({r.get("error")})'))
        return

    if r['mode'] == 'yaml':
        info, http = r['info'], r['http']
        if not info.get('name'):
            errors.append((rel, 'ERROR', 'info.name missing'))
        method = (r['method'] or '').upper()
        url = r['url'] or ''
        if not method:
            errors.append((rel, 'ERROR', 'http.method missing'))
        if not url:
            errors.append((rel, 'ERROR', 'http.url missing'))

        seq = info.get('seq')
        if seq is not None:
            seq_seen[path.parent.as_posix()].setdefault(seq, []).append(rel)

        # K4 — url path params (:name) ⇔ params(type: path)
        url_params = set(re.findall(r':([A-Za-z_]\w*)', url))
        decl_path = {p.get('name') for p in r['params'] if p.get('type') == 'path' and p.get('name')}
        for up in sorted(url_params - decl_path):
            errors.append((rel, 'ERROR', f'path param ":{up}" in url not declared in params (type: path)'))
        for dp in sorted(decl_path - url_params):
            errors.append((rel, 'ERROR', f'params declares path param "{dp}" absent from http.url'))

        # K4 — runnable body JSON validity
        if r['body_type'] == 'json' and r['body_data']:
            try:
                json.loads(r['body_data'])
            except json.JSONDecodeError as e:
                errors.append((rel, 'ERROR', f'http.body.data invalid JSON ({e.msg} line {e.lineno})'))

        # K2/K3 — compare against the source (markdown endpoint or openapi spec operation)
        ep = resolve_source(key, method, norm_template(norm_yaml_path(url)))
        if ep is not None:
            if ep['method'] and method and ep['method'] != method:
                errors.append((rel, 'ERROR',
                               f'http.method {method} ≠ source method {ep["method"]}'))
            if ep['path']:
                want, got = md_path_to_colon(ep['path']), norm_yaml_path(url)
                if want and got and want != got:
                    errors.append((rel, 'ERROR',
                                   f'http.url path "{got}" ≠ source path "{want}"'))
            # K3 body fidelity
            md_has = ep['body_json'] is not None
            yml_has = r['body_type'] == 'json' and bool(r['body_data'])
            if ep['body_json'] == '__INVALID__':
                notes.append((rel, 'source request example is not valid JSON — '
                                   'body fidelity unchecked; needs fresh-eyes'))
            elif md_has and not yml_has:
                errors.append((rel, 'ERROR',
                               'the source has a request example but the request has no http.body'))
            elif yml_has and not md_has:
                errors.append((rel, 'ERROR',
                               'request has an http.body but the source has no request example'))
            elif md_has and yml_has:
                try:
                    if json.loads(r['body_data']) != ep['body_json']:
                        errors.append((rel, 'ERROR',
                                       'http.body.data differs from the source request example'))
                except json.JSONDecodeError:
                    pass                                 # already reported above
            # auth mapping is judgment → fresh-eyes
            if ep['auth']:
                notes.append((rel, f'source auth = "{ep["auth"]}" — confirm the request/'
                                   'folder auth matches; needs fresh-eyes'))

        # K5 — every {{var}} (non process.env) is defined in some environment
        if env_vars is not None:
            for v in sorted({m.strip() for m in RE_VAR.findall(r['text'])}):
                if v.startswith('process.env.'):
                    continue
                if v not in env_vars:
                    errors.append((rel, 'ERROR',
                                   f'references {{{{{v}}}}} but no environments/*.yml defines it'))
    else:
        notes.append((rel, 'no YAML parser (PyYAML/yq absent) — http-block, path-param, body, '
                           'seq and env checks skipped for this file; needs fresh-eyes'))


# ───────────────────────── main ─────────────────────────

def parse_args(argv):
    """(collection-target, md-arg, spec-arg). --md / --spec each consume a value (space or
       =); the first bare token is the collection target. Either source flag may be omitted
       — main resolves the default (prefer the openapi spec when present)."""
    positional, md_arg, spec_arg = [], None, None
    it = iter(argv)
    for a in it:
        if a == '--md':
            md_arg = next(it, 'docs/api')
        elif a.startswith('--md='):
            md_arg = a[len('--md='):]
        elif a == '--spec':
            spec_arg = next(it, 'docs/openapi')
        elif a.startswith('--spec='):
            spec_arg = a[len('--spec='):]
        elif a.startswith('--'):
            continue
        else:
            positional.append(a)
    target = pathlib.Path(positional[0]) if positional else pathlib.Path('.')
    return target, md_arg, spec_arg


def _bucket():
    return {'ERROR': [], 'NOTE': []}


def main():
    target, md_arg, spec_arg = parse_args(sys.argv[1:])

    if not target.exists():
        print(f"colcheck: {target} not found — nothing to check")
        sys.exit(0)

    # collection root: the file's parent-most dir holding opencollection.yml, else target
    if target.is_file():
        col_root = target.parent
        p = target.parent
        while p != p.parent:
            if (p / 'opencollection.yml').exists():
                col_root = p
                break
            p = p.parent
    else:
        col_root = target

    request_files = collect_requests(target)
    if not request_files and not (col_root / 'opencollection.yml').exists():
        print("colcheck: no request .yml files or opencollection.yml — nothing to check")
        sys.exit(0)

    # ---- resolve the source: openapi spec (preferred) or markdown ----
    errors, notes, seq_seen = [], [], defaultdict(dict)
    md_root = pathlib.Path(md_arg) if md_arg else pathlib.Path('docs/api')
    spec_root = pathlib.Path(spec_arg) if spec_arg else pathlib.Path('docs/openapi')
    if spec_arg:
        source = 'spec'
    elif md_arg:
        source = 'md'
    elif (spec_root / 'openapi.yaml').exists():
        source = 'spec'                                  # auto: prefer the openapi spec
    else:
        source = 'md'
    print(f"colcheck: source = {source} "
          f"({'spec ' + str(spec_root) if source == 'spec' else 'markdown ' + str(md_root)})")

    if source == 'spec':
        spec_ops = collect_spec_ops(spec_root)
        if spec_ops is None:
            if not HAVE_YAML:
                print("colcheck: --spec source needs PyYAML to read the OpenAPI spec — install "
                      "pyyaml, or verify against the markdown with --md docs/api/.")
            else:
                print(f"colcheck: openapi spec {spec_root} not found or unreadable — run the "
                      f"openapi-doc skill first, or pass --spec <path>.")
            sys.exit(1)
        resolve_source = lambda key, method, npath: match_spec_op(spec_ops, method, npath)
        if target.is_dir():
            check_coverage_spec(spec_ops, request_files, col_root, errors)
    else:
        if not md_root.exists():
            print(f"colcheck: markdown source {md_root} not found — open-collection needs the "
                  f"docs/api/ markdown (run the api-doc skill first). Pass --md <path> if it lives elsewhere.")
            sys.exit(1)
        md_endpoints = collect_md_endpoints(md_root)
        resolve_source = lambda key, method, npath: (
            read_md_endpoint(md_endpoints[key]) if key in md_endpoints else None)
        if target.is_dir():
            yml_keys = {f.relative_to(col_root).with_suffix('').as_posix() for f in request_files}
            check_coverage(set(md_endpoints), yml_keys, col_root, errors)

    env_vars = collect_env_vars(col_root)

    if not HAVE_YAML:
        notes.append(('(global)', 'PyYAML not installed — YAML structural checks (http block, '
                                  'path params, body, seq, env) degraded to per-file NOTEs; install '
                                  'PyYAML or yq for the full open-collection verify (needs fresh-eyes)'))
    if env_vars is None:
        notes.append(('(global)', 'no environments/ directory — {{var}} reference checks (K5) '
                                  'skipped; needs fresh-eyes'))

    for f in request_files:
        try:
            check_request(f, col_root, resolve_source, env_vars, errors, notes, seq_seen)
        except Exception as e:                           # one bad file can't blank the run
            errors.append((f.name, 'ERROR', f'colcheck crashed on this file ({e!r})'))

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

    request_rels = [f.relative_to(col_root).as_posix() for f in request_files]
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
