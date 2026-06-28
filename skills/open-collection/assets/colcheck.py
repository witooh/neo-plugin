#!/usr/bin/env python3
"""
colcheck.py — TRIPWIRE cross-checker for `open-collection` output (Bruno OpenCollection ↔ the docs/api/ api-spec).
Zero install: pure Python 3 (stdlib only; uses PyYAML to read the spec, and imports the sibling
yaml2md.py to verify the embedded docs:). Layer-1 of the open-collection skill's three-layer verify.

WHY THIS EXISTS
  open-collection derives a *runnable*, self-documenting collection from the custom-YAML api-spec
  at docs/api/ (the single source of truth — the api-spec skill authors it, openapi-doc drift-checks
  it against Go). So this script verifies the collection against the API-SPEC — never against Go.
  What can silently drift is the transform: a request whose URL, method, path-params, runnable
  body, or embedded docs: no longer matches the endpoint it came from. This is the DETERMINISTIC,
  independent measure of that, so "verify passed" rests on evidence, not the writer's confidence
  (same principle as neo's lint.py/docverify.py).

PHILOSOPHY: TRIPWIRE, NOT GROUND TRUTH
  A flag RAISES A SIGNAL for a human/agent to inspect — it does not "prove" wrong:
    • ERROR = a mismatch the script is confident about (a spec operation with no request
              file, a method/path/body that diverges from the spec, a url path-param not
              declared, a {{var}} with no environment entry). The agent confirms each
              before fixing; a genuine false positive is skipped + noted, never blindly
              "fixed". Loop until ERRORs clear OR ~3 rounds stall.
    • NOTE  = something the script deliberately CANNOT verify confidently (auth
              semantic mapping, header completeness, env-var *values*). Printed for the
              Layer-2 fresh-eyes verifier; each ends in "needs fresh-eyes"; never fails.

WHAT IT CHECKS  (collection ↔ api-spec; ordered high→low confidence)
  K1 Coverage   every api-spec endpoint has a request .yml & vice versa (matched by
                (method, suffix-tolerant path); missing / orphan = ERROR); every group
                with endpoints has a folder.yml.
  K2 Method/Path  request http.method == the endpoint's method; http.url path (minus the
                {{...}} prefix) == the endpoint's path (matching already proved by K1).
  K3 Body       if the endpoint has a request_body.example, http.body.data must equal it
                (parsed JSON compare); body present on exactly one side = ERROR.
  K4 Structure  every request .yml has info.name + http.method + http.url · url path
                params (:name) ⇔ params(type: path) · http.body.data parses · seq unique
                per folder.
  K5 Env        every {{var}} a request references (excluding {{process.env.*}}) is
                defined in some environments/*.yml.
  K7 Docs       (Spec mode) each request's docs: equals yaml2md.render_endpoint(endpoint,
                nav=False) — the self-documenting collection stays faithful to the api-spec.
                Missing / divergent = ERROR; yaml2md unimportable → NOTE.

  NOTE sources: auth mapping (endpoint auth → folder/request auth) is judgment;
  no environments/ dir degrades K5 to a NOTE.

  AC-SCENARIO MODE (--mode scenario, auto when --design is given): one request per Ready AC
  (ac-<nnn>-*.yml) instead of one per endpoint. K1 coverage becomes "every Ready AC has a
  request" (a request for a Blocked / unknown AC = ERROR); K3 body equality is OFF (the body
  varies per scenario by design → NOTE); a new K6 requires a runtime.assertions res.status
  assertion; K7 is OFF (scenario requests carry no docs:); an unresolved endpoint degrades to a
  NOTE (the AC may target a rule / unbuilt endpoint). K2-method, K4, K5 are reused unchanged.
  Inputs: acceptance-criteria.html (required) + test-cases.html (optional enrichment: per-AC
  endpoint + expected HTTP status) under --design; the api-spec stays the contract anchor.

SOURCE
  open-collection derives the collection from the custom-YAML api-spec at docs/api/ (one
  <domain>/<endpoint>.yaml per endpoint; the api-spec skill's output). The collection is matched
  to the api-spec by (method, path) — hand-mapped request files are named by endpoint — so
  coverage + body fidelity compare endpoints, while the per-request structural (K4) and env (K5)
  checks are reused unchanged. K7 re-renders the endpoint via yaml2md.py. Needs PyYAML.

USAGE
  python3 colcheck.py <collection-root>          --spec docs/api  # vs the api-spec tree
  python3 colcheck.py <collection>/account/x.yml --spec docs/api  # one request file
  python3 colcheck.py <scenario-root> --spec docs/api --design docs/design/<usecase>  # AC-scenario
  (--spec/--design also accept =PATH; arg order is irrelevant. With no flag the spec defaults
   to docs/api. --mode scenario is implied by --design.)
Exit code: 0 = no ERROR (NOTEs/WARNINGs ok), 1 = at least one ERROR.
"""
import re, sys, json, pathlib, html
from collections import defaultdict

try:
    import yaml                      # PyYAML — full YAML structural checks when present
    HAVE_YAML = True
except Exception:
    HAVE_YAML = False                # without it the api-spec cannot be read

try:                                 # sibling asset — renders the api-spec endpoint for K7 docs: fidelity
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
    import yaml2md
    HAVE_YAML2MD = True
except Exception:
    HAVE_YAML2MD = False


RE_LEADING_VAR = re.compile(r'^\{\{[^}]*\}\}')           # a leading {{baseUrl}}-style token in a url
RE_VAR = re.compile(r'\{\{\s*([^}]+?)\s*\}\}')           # any {{var}} reference


# ───────────────────────── api-spec source reading ─────────────────────────
# open-collection derives the collection from the custom-YAML api-spec at docs/api/ (one
# <domain>/<endpoint>.yaml per endpoint; the api-spec skill authors it, openapi-doc drift-checks
# it against Go). The collection is matched to the spec by (method, path) — hand-mapped request
# files are named by endpoint — so coverage + body fidelity compare endpoints, while the
# per-request structural (K4) and env (K5) checks are reused unchanged. Needs PyYAML; without it
# the spec cannot be read.

def norm_template(p):
    """A URL path template normalised for comparison: params → {}, single leading slash."""
    p = re.sub(r'\{[^}]+\}', '{}', p or '')      # {id} → {}
    p = re.sub(r':[^/]+', '{}', p)               # :id  → {}
    return '/' + p.strip('/') if p.strip('/') else '/'


def _url_path(url):
    """The path part of a server url ('http://h/api/v1' → '/api/v1'; '/api/v1' → '/api/v1')."""
    m = re.match(r'^[a-zA-Z][\w+.-]*://[^/]+(/.*)?$', url or '')
    return (m.group(1) or '') if m else (url or '')


def _yaml_auth(auth):
    """A custom-YAML endpoint `auth:` string → an auth label ('Bearer token'/'API Key'/'None')."""
    low = str(auth or '').strip().lower()
    if low in ('', 'none'):
        return 'None'
    if 'bearer' in low or 'jwt' in low:
        return 'Bearer token'
    if 'api' in low and 'key' in low:
        return 'API Key'
    return str(auth)


def _yaml_body(doc):
    """The runnable request body from a custom-YAML endpoint's request_body.example (a JSON
       string). Invalid JSON → '__INVALID__' (the existing K3 convention); none → None."""
    ex = (doc.get('request_body') or {}).get('example')
    if not ex:
        return {'body_json': None, 'body_raw': None}
    try:
        val = json.loads(ex)
        return {'body_json': val, 'body_raw': json.dumps(val)}
    except Exception:
        return {'body_json': '__INVALID__', 'body_raw': None}


def collect_spec_ops(spec_root):
    """[{method, rel_path, full_path, auth, body_json, body_raw, _doc}] for every endpoint in the
       custom-YAML api-spec tree (docs/api/<domain>/*.yaml). `_doc` is the full parsed endpoint
       (K7 renders it). Returns None when PyYAML is absent or the tree is missing."""
    if not HAVE_YAML or not spec_root.exists():
        return None
    # path prefix from _meta.base_url (usually '/', i.e. no prefix)
    server_base = ''
    meta_f = spec_root / '_meta.yaml'
    if spec_root.is_dir() and meta_f.exists():
        try:
            meta = yaml.safe_load(meta_f.read_text(encoding='utf-8', errors='replace')) or {}
            server_base = _url_path(str(meta.get('base_url') or '')).rstrip('/')
        except Exception:
            server_base = ''
    files = sorted(spec_root.rglob('*.yaml')) if spec_root.is_dir() else [spec_root]
    ops = []
    for fp in files:
        if fp.name == '_meta.yaml':
            continue
        try:
            doc = yaml.safe_load(fp.read_text(encoding='utf-8', errors='replace'))
        except Exception:
            continue
        if not isinstance(doc, dict) or not doc.get('method') or not doc.get('path'):
            continue
        path = str(doc['path'])
        ops.append({'method': str(doc['method']).upper(), 'rel_path': path,
                    'full_path': server_base + path, 'auth': _yaml_auth(doc.get('auth')),
                    '_doc': doc, **_yaml_body(doc)})
    return ops


def _op_matches(op, method, req_norm):
    """True if a request (method, normalised path) matches a spec op (suffix-tolerant of
       the server base, since the request URL may or may not carry the /api/v1 prefix)."""
    if op['method'] != method:
        return False
    rel, full = norm_template(op['rel_path']), norm_template(op['full_path'])
    return req_norm in (rel, full) or req_norm.endswith(rel)


def match_spec_op(spec_ops, method, req_norm):
    """The unique spec op matching this request, shaped like an endpoint dict
       (path=None so the path-string compare is skipped — matching already proved it).
       `_doc` is the full parsed endpoint, passed through for K7 (yaml2md render)."""
    if not spec_ops:
        return None
    cand = [op for op in spec_ops if _op_matches(op, (method or '').upper(), req_norm)]
    if len(cand) == 1:
        op = cand[0]
        return {'method': op['method'], 'path': None, 'auth': op['auth'],
                'body_json': op['body_json'], 'body_raw': op['body_raw'],
                '_doc': op.get('_doc')}
    return None


# ───────────────────────── YAML request reading ─────────────────────────

def read_request_yaml(path):
    """Parse one request .yml. With PyYAML: structured read. Without: mark 'manual' so
       the caller degrades http-block checks to a NOTE."""
    text = path.read_text(encoding='utf-8', errors='replace')
    out = {'ok': True, 'mode': 'yaml' if HAVE_YAML else 'manual', 'text': text,
           'info': {}, 'http': {}, 'method': None, 'url': None,
           'body_type': None, 'body_data': None, 'params': [], 'runtime': {}, 'docs': None}
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
        rt = d.get('runtime')
        out['runtime'] = rt if isinstance(rt, dict) else {}      # surfaced for scenario-mode K6; spec mode ignores it
        out['docs'] = d.get('docs') if isinstance(d.get('docs'), str) else None   # K7 spec-mode docs: fidelity
    return out


def collect_requests(target):
    """[request .yml files] under a collection root — excludes opencollection.yml,
       folder.yml, and anything under environments/. Recursive so nested groups count
       (the api-spec source lives under docs/api/, outside the collection root)."""
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


# ───────────────────────── scenario-mode design-doc reading (AC / TC) ─────────────────────────
# AC-scenario mode joins the spec (contract anchor) with neo's docs/design/<usecase>/ HTML:
# acceptance-criteria.html → AC inventory + Ready/Blocked; test-cases.html (optional) → per-AC
# endpoint + expected HTTP status. Parsed from the AUTHORING form (<ac-card>/<tc-card> in the
# file, NOT the browser-expanded .card) by regex — no HTML-parser dependency.

RE_AC_CARD     = re.compile(r'<ac-card\b([^>]*)>', re.I)
RE_TC_CARD     = re.compile(r'<tc-card\b([^>]*)>(.*?)</tc-card>', re.I | re.S)
RE_ATTR_ID     = re.compile(r'\bid\s*=\s*"(AC-\d+)"', re.I)
RE_ATTR_STATUS = re.compile(r'\bstatus\s*=\s*"(ready|blocked)"', re.I)
RE_ATTR_TRACES = re.compile(r'\btraces\s*=\s*"([^"]*)"', re.I)
RE_ATTR_ENDPT  = re.compile(r'\bendpoint\s*=\s*"([^"]*)"', re.I)
RE_RES_BLOCK   = re.compile(r'<res\b[^>]*>(.*?)</res>', re.I | re.S)
RE_HTTP_STATUS = re.compile(r'HTTP\s+(\d{3})')
RE_AC_DIGITS   = re.compile(r'(\d+)')
RE_AC_IN_NAME  = re.compile(r'^ac-(\d+)', re.I)
RE_AC_ID       = re.compile(r'AC-\d+', re.I)           # an AC-ID token anywhere (e.g. inside a traces= list)


def _ac_num(ac):
    """The integer in an AC-ID string ('AC-007' → 7), or None."""
    m = RE_AC_DIGITS.search(ac or '')
    return int(m.group(1)) if m else None


def _ac_num_from_name(name):
    """The AC number from a scenario request filename ('ac-007-foo.yml' → 7), or None."""
    m = RE_AC_IN_NAME.match(name or '')
    return int(m.group(1)) if m else None


def _read_design(design_dir, name):
    """Text of design_dir/<name>, or None when it is missing/unreadable."""
    f = design_dir / name
    if not f.exists():
        return None
    try:
        return f.read_text(encoding='utf-8', errors='replace')
    except Exception:
        return None


def parse_ac_inventory(design_dir):
    """{ 'AC-NNN': 'ready'|'blocked' } from acceptance-criteria.html. Captures each <ac-card>
       opening tag, then reads id/status as independent attributes (order-insensitive).
       Returns None when the file is missing/unreadable (it is the required scenario input)."""
    text = _read_design(design_dir, 'acceptance-criteria.html')
    if text is None:
        return None
    inv = {}
    for m in RE_AC_CARD.finditer(text):
        attrs = m.group(1)
        mid = RE_ATTR_ID.search(attrs)
        if not mid:
            continue
        mst = RE_ATTR_STATUS.search(attrs)
        inv[mid.group(1)] = (mst.group(1).lower() if mst else 'ready')
    return inv


def parse_tc_scenarios(design_dir):
    """{ ac_num: {'endpoint': 'METHOD /path'|None, 'http_status': 'NNN'|None} } from the optional
       test-cases.html. A <tc-card traces=...> may trace several AC-IDs. Returns {} when absent."""
    text = _read_design(design_dir, 'test-cases.html')
    if text is None:
        return {}
    out = {}
    for m in RE_TC_CARD.finditer(text):
        attrs, inner = m.group(1), m.group(2)
        mtr = RE_ATTR_TRACES.search(attrs)
        if not mtr:
            continue
        mep = RE_ATTR_ENDPT.search(attrs)
        endpoint = html.unescape(mep.group(1)).strip() if mep else None
        mres = RE_RES_BLOCK.search(inner)
        mh = RE_HTTP_STATUS.search(html.unescape(mres.group(1))) if mres else None
        http_status = mh.group(1) if mh else None
        for ac in RE_AC_ID.findall(mtr.group(1)):
            n = _ac_num(ac)
            if n is not None:
                out[n] = {'endpoint': endpoint, 'http_status': http_status}
    return out


# ───────────────────────── path helpers ─────────────────────────

def norm_yaml_path(url):
    """A request URL minus its leading {{baseUrl}}-style token: '/api/v1/x/:id'."""
    return RE_LEADING_VAR.sub('', (url or '').strip()).strip()


# ───────────────────────── checks ─────────────────────────

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


def check_coverage_scenario(ac_inventory, request_files, col_root, errors):
    """Scenario coverage (matched by the AC number in the filename `ac-<nnn>-*.yml`): every Ready
       AC has >=1 request; no request maps to a Blocked or unknown AC-ID. N requests : 1 endpoint
       is fine (no by-endpoint orphan check in this direction)."""
    num_status, num_label = {}, {}
    for ac, st in ac_inventory.items():
        n = _ac_num(ac)
        if n is not None:
            num_status[n], num_label[n] = st, ac
    seen = set()
    for f in request_files:
        rel = f.relative_to(col_root).as_posix()
        n = _ac_num_from_name(f.name)
        if n is None:
            errors.append((rel, 'ERROR',
                           'scenario request filename carries no AC-ID (expected ac-<nnn>-*.yml)'))
            continue
        seen.add(n)
        if n not in num_status:
            errors.append((rel, 'ERROR',
                           f'request maps to AC-{n:03d}, absent from acceptance-criteria.html (orphan/stale AC)'))
        elif num_status[n] == 'blocked':
            errors.append((rel, 'ERROR',
                           f'request generated for Blocked {num_label[n]} — Blocked ACs are excluded (list + skip)'))
    for n in sorted(num_status):
        if num_status[n] == 'ready' and n not in seen:
            errors.append(('(coverage)', 'ERROR', f'Ready {num_label[n]} has no scenario request file'))


def check_request(path, col_root, resolve_source, env_vars, errors, notes, seq_seen,
                  src_mode='spec', tc_scenarios=None):
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

        # K2/K3 — compare against the api-spec endpoint
        ep = resolve_source(key, method, norm_template(norm_yaml_path(url)))
        if ep is None:
            if src_mode == 'scenario':
                notes.append((rel, 'request endpoint not found in the spec — the AC may target a '
                                   'rule or an endpoint not yet in the spec; needs fresh-eyes'))
        else:
            if ep['method'] and method and ep['method'] != method:
                errors.append((rel, 'ERROR',
                               f'http.method {method} ≠ source method {ep["method"]}'))
            if src_mode == 'scenario':
                # K3 equality is NOT an ERROR in scenario mode (bodies vary per scenario by design);
                # surface only the bodies that actually diverge from the base example for fresh-eyes.
                if (r['body_type'] == 'json' and bool(r['body_data'])
                        and ep['body_json'] not in (None, '__INVALID__')):
                    try:
                        if json.loads(r['body_data']) != ep['body_json']:
                            notes.append((rel, 'scenario body differs from the base example by design — '
                                               'confirm it matches the AC GIVEN/WHEN; needs fresh-eyes'))
                    except json.JSONDecodeError:
                        pass                                 # K4 already flags invalid JSON
            else:
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
                # K7 — docs: fidelity: the request's docs: must equal the yaml2md render
                # of the api-spec endpoint (the self-documenting collection stays faithful).
                if not HAVE_YAML2MD:
                    notes.append((rel, 'yaml2md unavailable — docs: fidelity (K7) unchecked; '
                                       'needs fresh-eyes'))
                elif ep.get('_doc'):
                    try:
                        expected = yaml2md.render_endpoint(ep['_doc'], nav=False)
                    except Exception:
                        expected = None
                    if expected is None:
                        notes.append((rel, 'yaml2md could not render this endpoint — docs: '
                                           'fidelity (K7) unchecked; needs fresh-eyes'))
                    elif not r.get('docs'):
                        errors.append((rel, 'ERROR', 'Spec-mode request has no docs: block '
                                       '(expected the api-spec endpoint render)'))
                    elif r['docs'].rstrip('\n') != expected.rstrip('\n'):
                        errors.append((rel, 'ERROR', 'docs: differs from the yaml2md render of '
                                       'the api-spec endpoint'))

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

        # K6 — scenario assertion presence (scenario mode only): a res.status assertion is mandatory
        if src_mode == 'scenario':
            assertions = r['runtime'].get('assertions')
            assertions = assertions if isinstance(assertions, list) else []
            sa = next((a for a in assertions
                       if isinstance(a, dict) and a.get('expression') == 'res.status'), None)
            sval = str(sa.get('value')).strip() if sa else ''
            if not (sval.isdigit() and len(sval) == 3):
                errors.append((rel, 'ERROR',
                               'scenario request has no runtime.assertions res.status assertion '
                               'with a 3-digit value'))
            elif tc_scenarios:
                n = _ac_num_from_name(path.name)
                tc = tc_scenarios.get(n) if n is not None else None
                if tc and tc.get('http_status') and tc['http_status'] != sval:
                    notes.append((rel, f'asserted res.status {sval} differs from the test case '
                                       f'expected HTTP {tc["http_status"]}; needs fresh-eyes'))
    else:
        notes.append((rel, 'no YAML parser (PyYAML/yq absent) — http-block, path-param, body, '
                           'seq and env checks skipped for this file; needs fresh-eyes'))


# ───────────────────────── main ─────────────────────────

def parse_args(argv):
    """(collection-target, spec-arg, design-arg, mode). --spec/--design consume a value (space
       or =); the first bare token is the collection target. --mode is spec|scenario (default
       spec; auto scenario when --design is given). --spec may be omitted — main defaults to
       the docs/api api-spec tree."""
    positional, spec_arg, design_arg, mode = [], None, None, None
    it = iter(argv)
    for a in it:
        if a == '--spec':
            spec_arg = next(it, 'docs/api')
        elif a.startswith('--spec='):
            spec_arg = a[len('--spec='):]
        elif a == '--design':
            design_arg = next(it, None)
        elif a.startswith('--design='):
            design_arg = a[len('--design='):]
        elif a == '--mode':
            mode = next(it, None)
        elif a.startswith('--mode='):
            mode = a[len('--mode='):]
        elif a.startswith('--'):
            continue
        else:
            positional.append(a)
    target = pathlib.Path(positional[0]) if positional else pathlib.Path('.')
    if mode not in ('spec', 'scenario'):
        mode = 'scenario' if design_arg else 'spec'
    return target, spec_arg, design_arg, mode


def _bucket():
    return {'ERROR': [], 'NOTE': []}


def main():
    target, spec_arg, design_arg, mode = parse_args(sys.argv[1:])

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

    # ---- source: the api-spec at docs/api/ ----
    errors, notes, seq_seen = [], [], defaultdict(dict)
    spec_root = pathlib.Path(spec_arg) if spec_arg else pathlib.Path('docs/api')
    design_dir = pathlib.Path(design_arg) if design_arg else pathlib.Path('docs/design')
    if mode == 'scenario':
        print(f"colcheck: source = api-spec {spec_root} + design {design_dir} (scenario mode)")
    else:
        print(f"colcheck: source = api-spec {spec_root}")

    spec_ops = collect_spec_ops(spec_root)
    if spec_ops is None:
        if not HAVE_YAML:
            print("colcheck: reading the api-spec needs PyYAML — install pyyaml (or yq).")
        else:
            print(f"colcheck: api-spec {spec_root} not found or unreadable — run the api-spec skill "
                  f"first (it authors docs/api/), or pass --spec <path>.")
        sys.exit(1)
    resolve_source = lambda key, method, npath: match_spec_op(spec_ops, method, npath)

    ac_inventory, tc_scenarios = None, None
    if mode == 'scenario':
        ac_inventory = parse_ac_inventory(design_dir)
        if ac_inventory is None:
            print(f"colcheck: scenario mode needs acceptance-criteria.html under {design_dir} — "
                  f"run the neo skill first, or pass --design <usecase-dir>.")
            sys.exit(1)
        tc_scenarios = parse_tc_scenarios(design_dir)

    if target.is_dir():
        if mode == 'scenario':
            check_coverage_scenario(ac_inventory, request_files, col_root, errors)
        else:
            check_coverage_spec(spec_ops, request_files, col_root, errors)

    env_vars = collect_env_vars(col_root)

    if env_vars is None:
        notes.append(('(global)', 'no environments/ directory — {{var}} reference checks (K5) '
                                  'skipped; needs fresh-eyes'))

    for f in request_files:
        try:
            check_request(f, col_root, resolve_source, env_vars, errors, notes, seq_seen,
                          mode, tc_scenarios)
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
