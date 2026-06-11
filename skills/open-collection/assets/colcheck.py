#!/usr/bin/env python3
"""
colcheck.py — TRIPWIRE cross-checker for `open-collection` output (Bruno OpenCollection ↔ docs/api markdown).
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

USAGE
  python3 colcheck.py <collection-root>          --md docs/api/   # whole collection vs markdown
  python3 colcheck.py <collection>/consent/x.yml --md docs/api/   # one request file
  (--md also accepts --md=PATH; arg order is irrelevant. --md = the docs/api root.)
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


def check_request(path, col_root, md_endpoints, env_vars, errors, notes, seq_seen):
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

        # K2/K3 — compare against the markdown source
        md = md_endpoints.get(key)
        if md is not None:
            ep = read_md_endpoint(md)
            if ep['method'] and method and ep['method'] != method:
                errors.append((rel, 'ERROR',
                               f'http.method {method} ≠ markdown **Method** {ep["method"]}'))
            if ep['path']:
                want, got = md_path_to_colon(ep['path']), norm_yaml_path(url)
                if want and got and want != got:
                    errors.append((rel, 'ERROR',
                                   f'http.url path "{got}" ≠ markdown **Path** "{want}"'))
            # K3 body fidelity
            md_has = ep['body_json'] is not None
            yml_has = r['body_type'] == 'json' and bool(r['body_data'])
            if ep['body_json'] == '__INVALID__':
                notes.append((rel, 'markdown ## Request Example is not valid JSON — '
                                   'body fidelity unchecked; needs fresh-eyes'))
            elif md_has and not yml_has:
                errors.append((rel, 'ERROR',
                               'markdown has a ## Request Example but the request has no http.body'))
            elif yml_has and not md_has:
                errors.append((rel, 'ERROR',
                               'request has an http.body but the markdown has no ## Request Example'))
            elif md_has and yml_has:
                try:
                    if json.loads(r['body_data']) != ep['body_json']:
                        errors.append((rel, 'ERROR',
                                       'http.body.data differs from the markdown ## Request Example'))
                except json.JSONDecodeError:
                    pass                                 # already reported above
            # auth mapping is judgment → fresh-eyes
            if ep['auth']:
                notes.append((rel, f'**Auth** = "{ep["auth"]}" in markdown — confirm the request/'
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
    """(collection-target, md-root). --md consumes its value (space or =); the first bare
       token is the collection target."""
    positional, md = [], 'docs/api'
    it = iter(argv)
    for a in it:
        if a == '--md':
            md = next(it, 'docs/api')
        elif a.startswith('--md='):
            md = a[len('--md='):]
        elif a.startswith('--'):
            continue
        else:
            positional.append(a)
    target = pathlib.Path(positional[0]) if positional else pathlib.Path('.')
    return target, pathlib.Path(md)


def _bucket():
    return {'ERROR': [], 'NOTE': []}


def main():
    target, md_root = parse_args(sys.argv[1:])

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

    if not md_root.exists():
        print(f"colcheck: markdown source {md_root} not found — open-collection needs the "
              f"docs/api/ markdown (run the api-doc skill first). Pass --md <path> if it lives elsewhere.")
        sys.exit(1)

    md_endpoints = collect_md_endpoints(md_root)
    env_vars = collect_env_vars(col_root)

    errors, notes, seq_seen = [], [], defaultdict(dict)

    # coverage only makes sense over the whole collection
    if target.is_dir():
        yml_keys = {f.relative_to(col_root).with_suffix('').as_posix() for f in request_files}
        check_coverage(set(md_endpoints), yml_keys, col_root, errors)

    if not HAVE_YAML:
        notes.append(('(global)', 'PyYAML not installed — YAML structural checks (http block, '
                                  'path params, body, seq, env) degraded to per-file NOTEs; install '
                                  'PyYAML or yq for the full open-collection verify (needs fresh-eyes)'))
    if env_vars is None:
        notes.append(('(global)', 'no environments/ directory — {{var}} reference checks (K5) '
                                  'skipped; needs fresh-eyes'))

    for f in request_files:
        try:
            check_request(f, col_root, md_endpoints, env_vars, errors, notes, seq_seen)
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
