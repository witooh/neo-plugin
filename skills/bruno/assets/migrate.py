#!/usr/bin/env python3
"""One-time converter from the legacy `docs/api/*.yaml` spec to Bruno request `docs:` blocks.

Usage: migrate.py <docs/api> <bruno-root> [--check]
Without --check it runs migrate() then roundtrip(); with --check only roundtrip(). Exit 1 iff the
round-trip finds a mismatch; exit 2, writing nothing, on a usage error (no `_meta.yaml` in <docs/api>,
no endpoint loaded) or missing PyYAML. Requests are matched by method + normalized path, not by file
name. An existing request keeps its `http` and `runtime` text (text-level block surgery), except that a
missing `http.body` gets the request example and a missing status test is added; `docs:` is replaced
and the top-level blocks reordered. Never deletes a file.
Stdlib + PyYAML only.
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
try:
    import yaml
    import docsparse as dp  # noqa: E402
except ModuleNotFoundError as e:
    if e.name != "yaml":
        raise
    sys.exit(print("migrate.py: needs PyYAML (pip install pyyaml)", file=sys.stderr) or 2)

TYPE_MAP = {"Integer": "Number"}
MANDATORY_MAP = {"M": "Yes", "O": "No"}
COMMON_LIB_BODY = {"responseCode", "errorCode", "errorMessage"}
COMMON_LIB_CODE = re.compile(r"[A-Z]{2,3}-[0-9]{4}")
NOT_DOCUMENTED = "Not documented in the source spec."
ERROR_BODY = [("responseCode", "Outcome class that determines the HTTP status"),
              ("errorCode", "Service-prefixed catalog code"),
              ("errorMessage", "Support/log message, not customer-facing wording")]
_TOP_KEY = re.compile(r"^([a-z]+):")
# Keys the round-trip accepts: the legacy api-spec template's keys, `headers` (rendered as `### Headers`), and the
# keys dropped on purpose (`covers_ac`, `permission_scopes` with a warning, `request_body.content_type/is_array`).
# Any other key is a MISMATCH, so a human normalizes the legacy YAML instead of losing it.
ENDPOINT_KEYS = {"endpoint", "domain", "method", "path", "auth", "covers_ac", "description", "path_params",
                 "query_params", "headers", "request_body", "responses", "business_logic", "errors", "notes",
                 "permission_scopes"}
REQUEST_BODY_KEYS = {"fields", "example", "objects", "content_type", "is_array"}
RESPONSE_KEYS = {"status", "description", "fields", "objects", "example"}
_STATUS_TEST = re.compile(r"res\.(status|getStatus\(\))")

# ── Audience filter, copied from the legacy Markdown renderer ──────────
# Keep wire + caller-visible behaviour. Drop ticket framing, evidence paths,
# ALIGN decision-log lines, internal renames, implementer changelog notes.
# Patterns are intentionally narrow: false positives hide caller-needed prose.

# Ticket keys / card refs only (case-sensitive: do not use re.I on [A-Z] classes).
_RE_TICKET = re.compile(
    r"\bGI-\d+(?:-AC\d+)?\b"       # GI-2226, GI-2226-AC01
    r"|\bAC-\d{2,4}\b"              # AC-001
    r"|\[[A-Z][A-Z0-9]*-(?:[A-Z0-9]+-)*[A-Z0-9]+\]"  # [PAY-BFID-02-A], not [transfer-confirm]
)
# Evidence / provenance: path tokens and "Evidence: …" clauses that cite them.
_RE_EVIDENCE = re.compile(
    r"(?i:\bEvidence\s*:\s*(?:`?docs/(?:knowledge|tasks|api)/[^\s`)\],;]+`?"
    r"(?:\s*[,;]\s*`?docs/(?:knowledge|tasks|api)/[^\s`)\],;]+`?)*))"
    r"|`?docs/(?:knowledge|tasks)/[^\s`)\],;]+`?"  # bare repo paths (not docs/api endpoint refs)
    r"|(?i:\bcommit\s+`?[0-9a-f]{7,40}`?)"
)
# Decision-log ALIGN is always uppercase in the legacy specs: do NOT match English "align".
_RE_ALIGN = re.compile(
    r"\bALIGN\b(?:\s+\d{4}-\d{2}-\d{2})?[^.;\n]*[.;]?"
    r"|(?i:\buser-confirmed\b[^.;\n]*[.;]?)"
    r"|(?i:\bspec\s+D\d+\b[^.;\n]*[.;]?)"
)
_RE_INTERNAL = re.compile(
    r"(?i:⚠\s*ADVISORY\b[^.;\n]*[.;]?)"
    r"|\bBFF\s+(?:renames?|maps?)\s+to\b[^.;\n]*[.;]?"
    r"|(?i:\bwire\s+was\s+camelCase\b[^.;\n]*[.;]?)"
    r"|(?i:\bAmended\s+\d{4}-\d{2}-\d{2}\b[^.;\n]*[.;]?)"
    r"|(?i:\bun-deferred\b[^.;\n]*[.;]?)"
    r"|(?i:\bDraft\s+proposal\b[^.;\n]*[.;]?)"
)
_RE_EMPTY_PARENS = re.compile(r"\(\s*\)")
# Collapse runs of spaces/tabs only between non-space chars: never eat list indent.
_RE_WS = re.compile(r"(?<=\S)[ \t]{2,}")
_RE_SPACE_PUNCT = re.compile(r" +([,.;:])")
# Whole-note drop: ALIGN is uppercase-only so English "align" notes survive.
_RE_NOTE_DROP = re.compile(
    r"(?i:^\s*Amended\b)"
    r"|\bdocs/(?:knowledge|tasks)/"
    r"|\bALIGN\b"
    r"|(?i:\bEvidence\s*:)"
    r"|(?i:\bPlan\b.*\bOpen Question)"
    r"|(?i:\bTBC with\b)"
)


def audience_text(s: str) -> str:
    """Strip Drop-column prose from a free-text field. Empty if nothing consumer-facing remains.

    Clean strings (no Drop-column hit) return **byte-identical**: no whitespace/list
    tidy, so nested business_logic bullets and remarks like ``-1 = unlimited`` survive.
    """
    if not s:
        return ""
    original = str(s)
    t = original
    for rx in (_RE_EVIDENCE, _RE_ALIGN, _RE_INTERNAL, _RE_TICKET):
        t = rx.sub("", t)
    if t == original:
        return original  # nothing dropped → never tidy
    # drop orphan "See" left after cutting a docs path ("See docs/tasks/…")
    t = re.sub(r"(?i)\bSee\s*$", "", t)
    t = re.sub(r"(?i)\bSee\s+([,.;)])", r"\1", t)
    t = _RE_EMPTY_PARENS.sub("", t)
    t = _RE_SPACE_PUNCT.sub(r"\1", t)
    t = _RE_WS.sub(" ", t)
    # tidy leftover punctuation/spacing after cuts only
    t = re.sub(r"\s*[, –-]\s*$", "", t)
    t = re.sub(r"^\s*[, –-]\s*", "", t)
    t = re.sub(r"\(\s*;\s*", "(", t)
    t = re.sub(r"\s*;\s*\)", ")", t)
    t = re.sub(r"\s*,\s*,+", ", ", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r" +\n", "\n", t)
    return t.strip(" \t\n;,-, –")


def audience_notes(notes) -> list:
    """Keep only caller-facing notes; drop implementer changelog / evidence notes."""
    out = []
    for n in notes or []:
        if not n:
            continue
        if _RE_NOTE_DROP.search(str(n)):
            continue
        cleaned = audience_text(str(n))
        if cleaned:
            out.append(cleaned)
    return out


# ── Rendering ──────────────────────────────────────────────────────────
def _plain(v):
    """A cell value on one line: newlines collapse to one space."""
    return re.sub(r"\s*\n\s*", " ", "" if v is None else str(v)).strip()


def _row(cells):
    return "| " + " | ".join(_plain(c).replace("|", "\\|") for c in cells) + " |"


def _table(header, rows):
    return "\n".join([_row(header), "|" + "---|" * len(header)] + [_row(r) for r in rows])


def _field_table(rows):
    return _table(dp.FIELD_HEADER, [[r[k] for k in ("name", "type", "mandatory", "description", "possible")]
                                    for r in rows])


def _error_table(errors):
    return _table(dp.ERROR_HEADER, [[e.get("status"), e.get("responseCode"), e.get("code"),
                                     audience_text(_plain(e.get("message"))),
                                     audience_text(_plain(e.get("description")))]
                                    for e in errors or [] if isinstance(e, dict)])


def _fence(text):
    return "```json\n" + str(text).strip("\n") + "\n```"


def _prose(v):
    return audience_text(str(v or "").strip())


def flatten_fields(fields, objects, prefix="", _seen=()):
    """Legacy field rows → docs rows with dot-paths; `object: X` rows are followed by X's rows."""
    out = []
    for f in fields or []:
        if not isinstance(f, dict):
            continue
        name = prefix + str(f.get("name", ""))
        typ = TYPE_MAP.get(f.get("type"), str(f.get("type") or ""))
        desc, remark = _prose(f.get("description")), _prose(f.get("remark"))
        obj = f.get("object")
        possible = "" if obj or "example" not in f else f"`{json.dumps(f['example'], ensure_ascii=False, default=str)}`"
        out.append({"name": name, "type": typ,
                    "mandatory": MANDATORY_MAP.get(f.get("mandatory"), str(f.get("mandatory") or "")),
                    "description": f"{desc} {remark}".strip() if remark else desc, "possible": possible})
        if obj in objects and obj not in _seen:
            child = name + ("[]." if typ == "Array" else ".")
            out += flatten_fields(objects[obj], objects, child, _seen + (obj,))
    return out


def _reached(fields, objects, _seen=()):
    """Names of `objects:` entries that flatten_fields expands from these fields (same rules)."""
    out = set()
    for f in fields or []:
        obj = f.get("object") if isinstance(f, dict) else None
        if obj in objects and obj not in _seen:
            out |= {obj} | _reached(objects[obj], objects, _seen + (obj,))
    return out


def _objects(ep):
    """Every `objects:` map in the endpoint file; a response's own map wins over this union."""
    rb = ep.get("request_body") if isinstance(ep.get("request_body"), dict) else {}
    out = dict(rb.get("objects") or {})
    for r in ep.get("responses") or []:
        if isinstance(r, dict):
            for name, rows in (r.get("objects") or {}).items():
                out.setdefault(name, rows)
    return out


def _as_array(rows, example):
    """The legacy spec has no array marker: a body whose Example is a top-level JSON list gets `[].` rows."""
    try:
        is_list = isinstance(json.loads(example) if isinstance(example, str) else example, list)
    except ValueError:
        is_list = False
    if not is_list or any(r["name"].startswith("[]") for r in rows):
        return rows
    return [{**r, "name": "[]." + r["name"]} for r in rows]


def _tables(ep):
    rb = ep.get("request_body") if isinstance(ep.get("request_body"), dict) else {}
    return {"headers": flatten_fields(ep.get("headers"), {}),
            "path": flatten_fields(ep.get("path_params"), {}),
            "query": flatten_fields(ep.get("query_params"), {}),
            "body": _as_array(flatten_fields(rb.get("fields"), _objects(ep)), rb.get("example"))}


def _is_error_body(r):
    return isinstance(r.get("status"), int) and r["status"] >= 400 and bool(r.get("fields"))


def _error_responses(ep):
    return [r for r in ep.get("responses") or [] if isinstance(r, dict) and _is_error_body(r)]


def _is_trio(r):
    return {f.get("name") for f in r.get("fields") or [] if isinstance(f, dict)} == COMMON_LIB_BODY


def _scope(ep, r):
    return {**_objects(ep), **(r.get("objects") or {})}


def _responses(ep):
    """[(response, rows)] for every response that gets an `### HTTP Status: N` section."""
    out = []
    for r in ep.get("responses") or []:
        if not isinstance(r, dict):
            continue
        if _is_error_body(r) and _is_trio(r):
            continue  # the common-lib error body is documented once, at the collection root
        out.append((r, _as_array(flatten_fields(r.get("fields"), _scope(ep, r)), r.get("example"))))
    return out


def _unreached_objects(ep):
    """`objects:` entries (request body or a rendered response) that no `object:` field reaches."""
    rb = ep.get("request_body") if isinstance(ep.get("request_body"), dict) else {}
    defined, reached = set(rb.get("objects") or {}), _reached(rb.get("fields"), _objects(ep))
    for r, _ in _responses(ep):
        defined |= set(r.get("objects") or {})
        reached |= _reached(r.get("fields"), _scope(ep, r))
    return sorted(defined - reached)


def render_request_docs(ep):
    tables = _tables(ep)
    parts = ["## Purpose", _prose(ep.get("description")), "## Request",
             "### Endpoint", f"`{str(ep.get('method', '')).upper()} {ep.get('path', '')}`",
             "### Auth", f"`{ep.get('auth') or 'None'}`"]
    for key, title in (("headers", "Headers"), ("path", "Path Parameters"), ("query", "Query Parameters")):
        if tables[key]:
            parts += [f"### {title}", _field_table(tables[key])]
    rb = ep.get("request_body") if isinstance(ep.get("request_body"), dict) else {}
    if rb:
        parts += ["### Body (JSON)", _field_table(tables["body"]) if tables["body"] else ""]
        if rb.get("example"):
            parts += ["### Example", _fence(rb["example"])]
    parts.append("## Response")
    for r, rows in _responses(ep):
        parts += [f"### HTTP Status: {r.get('status')}", _prose(r.get("description")),
                  _field_table(rows) if rows else ""]
        if r.get("example"):
            parts += ["### Example", _fence(r["example"])]
    if ep.get("errors"):
        parts += ["### Error Responses", _error_table(ep["errors"])]
    logic = _prose(ep.get("business_logic"))
    if logic:
        parts += ["## Business Logic", logic]
    notes = audience_notes(ep.get("notes"))
    if notes:
        parts += ["## Notes", "\n".join(f"- {n}" for n in notes)]
    return "\n\n".join(p for p in parts if p) + "\n"


def _trio(values):
    return [{"name": n, "type": "String", "mandatory": "Yes", "description": d,
             "possible": f"`{json.dumps(str(v), ensure_ascii=False)}`"} for (n, d), v in zip(ERROR_BODY, values)]


def error_body(meta, endpoints):
    """Root `## Error Response Body` rows (None = not documented) for the body the source documents, plus a warning."""
    errors = list(meta.get("common_errors") or []) + [e for ep in endpoints for e in ep.get("errors") or []]
    lib = next((e for e in errors if isinstance(e, dict) and COMMON_LIB_CODE.fullmatch(str(e.get("code", "")))), None)
    trio = next((r for ep in endpoints for r in _error_responses(ep) if _is_trio(r)), None)
    if lib:
        return _trio([lib.get("responseCode", "001"), lib["code"], lib.get("message", "")]), None
    if trio:
        ex = {f.get("name"): f.get("example", "") for f in trio["fields"] if isinstance(f, dict)}
        return _trio([ex["responseCode"], ex["errorCode"], ex["errorMessage"]]), None
    files, first = Counter(), {}  # field set -> number of distinct endpoint files that document it
    for ep in endpoints:
        sets = {}
        for r in _error_responses(ep):
            rows = flatten_fields(r["fields"], _scope(ep, r))
            sets.setdefault(tuple(_triples(rows)), rows)
        files.update(sets.keys())
        for key, rows in sets.items():
            first.setdefault(key, rows)
    key, count = (files.most_common(1) or [(None, 0)])[0]
    if count >= 2:
        return first[key], (f"opencollection.yml: Error Response Body documents the most frequent non-common-lib "
                            f"error body ({count} endpoint files): {[r['name'] for r in first[key]]}")
    return None, ("opencollection.yml: Error Response Body is not documented in the source spec; "
                  "fill it in by hand")


def render_root_docs(meta, body_rows=None):
    common = [e for e in meta.get("common_errors") or [] if isinstance(e, dict)]
    parts = ["## Overview", _prose(meta.get("overview"))]
    if meta.get("field_info"):
        parts.append("## Field Information")
        for name, rows in meta["field_info"].items():
            parts += [f"### {name}", _table(["Code", "Description"], [
                [f"`{r.get('code', '')}`", audience_text(_plain(r.get("description")))]
                for r in rows or [] if isinstance(r, dict)])]
    parts += ["## Error Response Body", NOT_DOCUMENTED if body_rows is None else _field_table(body_rows),
              "## Common Error Responses", _error_table(common)]
    return "\n\n".join(p for p in parts if p) + "\n"


def render_folder_docs(dmeta):
    dmeta = dmeta if isinstance(dmeta, dict) else {}
    parts = [f"## {_plain(dmeta['title'])}"] if dmeta.get("title") else []
    if _prose(dmeta.get("description")):
        parts.append(_prose(dmeta.get("description")))
    return "\n\n".join(parts) + "\n" if parts else None


# ── Text-level block surgery ───────────────────────────────────────────
def split_top_level(text):
    """Raw top-level blocks; a block starts at a `^[a-z]+:` line. Leading text gets key ''.

    Blank lines after a block are separators, not block text, so a moved block stays byte-identical.
    """
    blocks = []
    for line in text.splitlines(keepends=True):
        m = _TOP_KEY.match(line)
        if m or not blocks:
            blocks.append([m.group(1) if m else "", [line]])
        else:
            blocks[-1][1].append(line)
    out = []
    for key, lines in blocks:
        while len(lines) > 1 and not lines[-1].strip():
            lines.pop()
        if key or "".join(lines).strip():
            out.append((key, "".join(lines)))
    return out


def join_blocks(blocks):
    """Blocks separated by one blank line."""
    return "\n".join(text if text.endswith("\n") else text + "\n" for _, text in blocks)


def _docs_block(md):
    return "docs: |-\n" + "".join(("  " + line if line.strip() else "") + "\n"
                                  for line in md.rstrip("\n").split("\n"))


def _set_block(blocks, key, text):
    if any(k == key for k, _ in blocks):
        return [(k, text if k == key else t) for k, t in blocks]
    return blocks + [(key, text)]


def _child_indent(block):
    for line in block.splitlines()[1:]:
        if line.strip() and not line.lstrip().startswith("#"):
            return line[: len(line) - len(line.lstrip())]
    return "  "


def _append(block, lines):
    """Add lines at the end of a block, before its trailing blank lines."""
    body = block.rstrip("\n")
    return body + "\n" + lines + block[len(body) + 1:]


def _test_item(status, item):
    return (f"{item}- type: tests\n{item}  code: |-\n"
            f'{item}    test("status is {status}", function() {{ expect(res.status).to.equal({status}); }});\n')


def _status_test(status, indent="  "):
    return f"{indent}scripts:\n" + _test_item(status, indent + "  ")


def _add_test_item(block, status, indent):
    """Append a status-test item to the `scripts:` list inside a runtime block; None if its shape is unknown."""
    lines = block.splitlines(keepends=True)
    at = next(i for i, line in enumerate(lines) if line.startswith(indent + "scripts:"))
    rest = lines[at].split(":", 1)[1].strip()
    if rest == "[]":
        lines[at] = f"{indent}scripts:\n"
    elif rest:
        return None
    end, item = at + 1, None
    for j in range(at + 1, len(lines)):
        text = lines[j].lstrip()
        depth = len(lines[j]) - len(text)
        if not text.strip() or text.startswith("#"):
            continue
        if depth > len(indent) or (depth == len(indent) and text.startswith("- ")):
            item = item or (lines[j][:depth] if text.startswith("- ") else None)
            end = j + 1
        else:
            break
    if not lines[end - 1].endswith("\n"):
        lines[end - 1] += "\n"
    lines.insert(end, _test_item(status, item or indent + "  "))
    return "".join(lines)


def _body_lines(indent, example):
    lines = [f"{indent}body:", f"{indent}  type: json", f"{indent}  data: |-"]
    lines += [f"{indent}    {line}" if line.strip() else "" for line in str(example).strip("\n").split("\n")]
    return "\n".join(lines) + "\n"


def _first_success(ep):
    statuses = [r.get("status") for r in ep.get("responses") or [] if isinstance(r, dict)]
    return next((s for s in statuses if isinstance(s, int) and 200 <= s < 300), 200)


def _has_status_test(runtime):
    scripts = runtime.get("scripts") if isinstance(runtime, dict) else None
    return isinstance(scripts, list) and any(
        isinstance(s, dict) and s.get("type") == "tests" and _STATUS_TEST.search(str(s.get("code") or ""))
        for s in scripts)


def _order(block):
    return dp.TOP_ORDER.index(block[0]) if block[0] in dp.TOP_ORDER else (-1 if block[0] == "" else len(dp.TOP_ORDER))


# ── Spec loading and matching ──────────────────────────────────────────
def _norm(path):
    p = re.split(r"[?#]", str(path or ""), maxsplit=1)[0].strip()
    p = re.sub(r"^\{\{[^}]*\}\}", "", p)
    p = re.sub(r"^[a-zA-Z][\w+.-]*://[^/]+", "", p)
    p = re.sub(r"\{\{[^}]*\}\}|\{[^}]+\}|(?<=/):[^/]+", "{}", p)
    return "/" + p.strip("/")


def _slug(text):
    return re.sub(r"[^a-z0-9]+", "-", str(text).lower()).strip("-") or "misc"


def _read_yaml(path, warnings):
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
        warnings.append(f"{path.name}: cannot read ({str(exc).splitlines()[0]}), skipped")
        return None


def _load_spec(api_dir, warnings, skipped=None):
    """(meta, endpoints); `skipped` collects a round-trip message per legacy file that is not migrated."""
    skipped = [] if skipped is None else skipped
    meta = _read_yaml(api_dir / "_meta.yaml", warnings)
    if not isinstance(meta, dict):
        skipped.append("_meta.yaml: unreadable, or not a mapping; not migrated")
        meta = {}
    base = re.sub(r"^[a-zA-Z][\w+.-]*://[^/]+", "", str(meta.get("base_url") or "")).rstrip("/")
    eps = []

    def add(ep, rel, folder, stem):
        eps.append({"ep": ep, "rel": rel, "dir": folder, "stem": stem,
                    "norms": (_norm(ep["path"]), _norm(base + str(ep["path"])))})

    for f in sorted(api_dir.rglob("*.yaml")):
        if f.name == "_meta.yaml":
            continue
        ep = _read_yaml(f, warnings)
        rel = f.relative_to(api_dir).as_posix()
        if not isinstance(ep, dict) or not ep.get("method") or not ep.get("path"):
            warnings.append(f"{rel}: not an endpoint (no method/path), skipped")
            skipped.append(f"{rel}: unreadable, or not an endpoint (no method/path); not migrated")
            continue
        add(ep, rel, f.parent.relative_to(api_dir).as_posix(), f.stem)
    dirs = {}
    for e in eps:
        dirs.setdefault(e["ep"].get("domain"), e["dir"])
    for x in meta.get("extra_endpoints") or []:
        if isinstance(x, dict) and x.get("method") and x.get("path"):
            method = str(x["method"]).upper()
            # status 200 matches the default status test the created request asserts (K2 needs a success section)
            ep = {"endpoint": f"{method} {x['path']}", "domain": x.get("domain"), "method": method,
                  "path": x["path"], "auth": x.get("auth", "None"), "description": x.get("description"),
                  "responses": [{"status": 200}]}
            add(ep, None, dirs.get(x.get("domain")) or _slug(x.get("domain") or ""), _slug(f"{method} {x['path']}"))
    return meta, eps


def _request_files(root):
    for p in sorted(root.rglob("*.yml")):
        rel = p.relative_to(root)
        if rel.parts[0] != "environments" and p.name not in ("folder.yml", "opencollection.yml"):
            yield p


def _match(eps, root, warnings):
    """({endpoint index: [(path, parsed request)]}, [orphan rel paths]); exact path beats suffix."""
    groups, orphans = {}, []
    for p in _request_files(root):
        rel = p.relative_to(root).as_posix()
        try:
            req = dp.parse_request(p)
        except dp.ParseError as exc:
            warnings.append(f"{rel}: {exc.msg}; left untouched")
            continue
        http = req["http"] if isinstance(req["http"], dict) else {}
        method, norm = str(http.get("method", "")).upper(), _norm(http.get("url"))
        same = [i for i, e in enumerate(eps) if str(e["ep"]["method"]).upper() == method]
        pick = [i for i in same if norm in eps[i]["norms"]]
        if not pick:
            suffix = [i for i in same if norm.endswith(eps[i]["norms"][0])]
            longest = max((len(eps[i]["norms"][0]) for i in suffix), default=0)
            pick = [i for i in suffix if len(eps[i]["norms"][0]) == longest]
        if len(pick) == 1:
            groups.setdefault(pick[0], []).append((p, req))
        elif pick:
            warnings.append(f"{rel}: matches several endpoints {[eps[i]['rel'] for i in pick]}; left untouched")
        else:
            orphans.append(rel)
    return groups, orphans


# ── Writing ────────────────────────────────────────────────────────────
def _q(value):
    return json.dumps("" if value is None else str(value), ensure_ascii=False)


def _param_value(p):
    ex = p.get("example", "")
    return ex if isinstance(ex, str) else json.dumps(ex, default=str)


def _max_seq(folder):
    seqs = []
    for p in folder.glob("*.yml"):
        if p.name != "folder.yml":
            data = _read_yaml(p, [])
            info = data.get("info") if isinstance(data, dict) else None
            if isinstance(info, dict) and isinstance(info.get("seq"), int):
                seqs.append(info["seq"])
    return max(seqs, default=0)


def _new_request(ep, seq):
    params = [(p, "path") for p in ep.get("path_params") or [] if isinstance(p, dict)]
    params += [(p, "query") for p in ep.get("query_params") or [] if isinstance(p, dict)]
    url = "{{baseUrl}}" + re.sub(r"\{([^}]+)\}", r":\1", str(ep["path"]))
    query = [f"{p.get('name')}={_param_value(p)}" for p, kind in params if kind == "query"]
    url += "?" + "&".join(query) if query else ""
    lines = ["info:", f"  name: {_q(ep.get('endpoint'))}", "  type: http", f"  seq: {seq}", "",
             "http:", f"  method: {str(ep['method']).upper()}", f"  url: {_q(url)}"]
    if params:
        lines.append("  params:")
        for p, kind in params:
            lines += [f"    - name: {_q(p.get('name'))}", f"      value: {_q(_param_value(p))}", f"      type: {kind}"]
    text = "\n".join(lines) + "\n"
    example = (ep.get("request_body") or {}).get("example") if isinstance(ep.get("request_body"), dict) else None
    if example:
        text += _body_lines("  ", example)
    return (text + "  auth: inherit\n\nruntime:\n" + _status_test(_first_success(ep)) +
            "\nsettings:\n  encodeUrl: true\n\n" + _docs_block(render_request_docs(ep)))


def _update_request(path, req, ep, rel, report):
    blocks = split_top_level(path.read_text(encoding="utf-8"))
    keys = [k for k, _ in blocks]
    http = req["http"] if isinstance(req["http"], dict) else {}
    example = (ep.get("request_body") or {}).get("example") if isinstance(ep.get("request_body"), dict) else None
    if example and "body" not in http and "http" in keys:
        blocks = [(k, _append(t, _body_lines(_child_indent(t), example)) if k == "http" else t) for k, t in blocks]
    status, runtime = _first_success(ep), req["runtime"]
    scripts = runtime.get("scripts") if isinstance(runtime, dict) else None
    if "runtime" not in keys:
        blocks.append(("runtime", "runtime:\n" + _status_test(status)))
    elif not isinstance(runtime, dict) or "scripts" not in runtime:
        blocks = [(k, _append(t, _status_test(status, _child_indent(t))) if k == "runtime" else t)
                  for k, t in blocks]
    elif not any(isinstance(x, dict) and x.get("type") == "tests" for x in scripts or []):
        block = dict(blocks)["runtime"]
        new = _add_test_item(block, status, _child_indent(block)) if scripts is None or isinstance(scripts, list) else None
        if new is None:
            report["warnings"].append(f"{rel}: runtime.scripts has an unexpected shape; add a status test by hand")
        else:
            blocks = [(k, new if k == "runtime" else t) for k, t in blocks]
    elif not _has_status_test(runtime):
        report["warnings"].append(f"{rel}: runtime tests script does not assert res.status; add one by hand")
    blocks = sorted(_set_block(blocks, "docs", _docs_block(render_request_docs(ep))), key=_order)
    path.write_text(join_blocks(blocks), encoding="utf-8")
    report["updated"].append(rel)


def _replace_docs(path, md, root, report):
    blocks = _set_block(split_top_level(path.read_text(encoding="utf-8")), "docs", _docs_block(md))
    path.write_text(join_blocks(blocks), encoding="utf-8")
    report["updated"].append(path.relative_to(root).as_posix())


def _sync_folders(root, meta, eps, report):
    domains = meta.get("domains") if isinstance(meta.get("domains"), dict) else {}
    taken = []
    for f in root.rglob("folder.yml"):
        data = _read_yaml(f, [])
        info = data.get("info") if isinstance(data, dict) else None
        taken.append(info["seq"] if isinstance(info, dict) and isinstance(info.get("seq"), int) else 0)
    by_dir = {}
    for e in eps:
        by_dir.setdefault(e["dir"], []).append(e["ep"])
    for folder_dir, members in by_dir.items():
        if folder_dir == "." or not (root / folder_dir).is_dir():
            continue
        domain = members[0].get("domain")
        dmeta = domains.get(domain) if isinstance(domains.get(domain), dict) else {}
        docs = render_folder_docs(dmeta)
        folder = root / folder_dir / "folder.yml"
        if folder.exists():
            if docs:
                _replace_docs(folder, docs, root, report)
            continue
        raw = {str(m.get("auth") or "None") for m in members}
        auth = "none" if {a.strip().lower() for a in raw} == {"none"} else "inherit"
        if auth != "none":
            report["warnings"].append(f"{folder_dir}/folder.yml: auth {sorted(raw)} has no Bruno mapping; "
                                      "set request.auth by hand")
        seq = dmeta.get("seq") if isinstance(dmeta.get("seq"), int) else (max(taken, default=0) // 10 + 1) * 10
        taken.append(seq)
        text = (f"info:\n  name: {_q(dmeta.get('title') or domain)}\n  type: folder\n  seq: {seq}\n\n"
                f"request:\n  auth: {auth}\n")
        folder.write_text(text + ("\n" + _docs_block(docs) if docs else ""), encoding="utf-8")
        report["created"].append(folder.relative_to(root).as_posix())


def migrate(api_dir, bruno_root):
    api_dir, root = Path(api_dir), Path(bruno_root)
    report = {"updated": [], "created": [], "orphans": [], "warnings": []}
    root.mkdir(parents=True, exist_ok=True)
    meta, eps = _load_spec(api_dir, report["warnings"])
    for e in eps:
        scopes = e["ep"].get("permission_scopes")
        if e["rel"] and scopes:
            report["warnings"].append(f"{e['rel']}: permission_scopes not rendered: "
                                      + ", ".join(map(str, scopes if isinstance(scopes, list) else [scopes])))
    groups, report["orphans"] = _match(eps, root, report["warnings"])
    for i, e in enumerate(eps):
        if i in groups:
            if e["rel"]:  # a request that matches an extra endpoint is left as is
                for path, req in groups[i]:
                    _update_request(path, req, e["ep"], path.relative_to(root).as_posix(), report)
            continue
        target = root / e["dir"] / f"{e['stem']}.yml"
        rel = target.relative_to(root).as_posix()
        if target.exists():
            report["warnings"].append(f"{rel}: exists but does not match {e['ep']['method']} {e['ep']['path']}; "
                                      "not overwritten")
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(_new_request(e["ep"], _max_seq(target.parent) + 10), encoding="utf-8")
        report["created"].append(rel)
    _sync_folders(root, meta, eps, report)
    rows, warning = error_body(meta, [e["ep"] for e in eps if e["rel"]])
    report["warnings"] += [warning] if warning else []
    oc, root_md = root / "opencollection.yml", render_root_docs(meta, rows)
    if oc.exists():
        _replace_docs(oc, root_md, root, report)
    else:
        oc.write_text(f"opencollection: 1.0.0\n\ninfo:\n  name: {_q(meta.get('title') or root.parent.name)}\n\n"
                      f"bundled: false\n\n{_docs_block(root_md)}", encoding="utf-8")
        report["created"].append("opencollection.yml")
    for rel in report["orphans"]:
        report["warnings"].append(f"{rel}: no endpoint in the legacy spec matches this request; left untouched")
    for p in sorted(root.glob("openapi*.yaml")):
        report["warnings"].append(f"{p.name}: OpenAPI file left untouched")
    return report


# ── Round-trip ─────────────────────────────────────────────────────────
def _triples(rows):
    return [(_plain(r["name"]).replace("`", ""), _plain(r["type"]), _plain(r["mandatory"])) for r in rows]


def _status(v):
    return int(v) if str(v).strip().isdigit() else None


def _delta(label, want, got):
    missing, extra = Counter(want) - Counter(got), Counter(got) - Counter(want)
    if missing or extra:
        return f"{label}: missing {sorted(missing, key=repr)}, unexpected {sorted(extra, key=repr)}"
    return None


def _unmigrated_keys(ep):
    """Endpoint, request_body and response keys outside the allowlist: migrate renders none of them."""
    rb = ep.get("request_body") if isinstance(ep.get("request_body"), dict) else {}
    keys = [str(k) for k in ep if k not in ENDPOINT_KEYS]
    keys += [f"request_body.{k}" for k in rb if k not in REQUEST_BODY_KEYS]
    keys += sorted({f"responses[].{k}" for r in ep.get("responses") or [] if isinstance(r, dict)
                    for k in r if k not in RESPONSE_KEYS})
    return keys


def _diff(ep, req):
    diffs = [_delta(key, _triples(rows), _triples(req["docs"]["tables"][key])) for key, rows in _tables(ep).items()]
    want = [(_status(r.get("status")), _triples(rows)) for r, rows in _responses(ep)]
    got = []
    for sec in dp.split_sections(req["docs_raw"]):
        m = re.match(r"HTTP Status:\s*(\d+)", sec["title"])
        if sec["level"] == 3 and m:
            table = dp.parse_table(sec["body"])
            got.append((int(m.group(1)), _triples(dp.field_rows(*table) if table else [])))

    def items(pairs):
        return [(s,) for s, _ in pairs] + [(s,) + t for s, rows in pairs for t in rows]

    diffs.append(_delta("responses", items(want), items(got)))
    diffs.append(_delta("errors",
                        [(_status(e.get("status")), _plain(e.get("responseCode")).replace("`", ""),
                          _plain(e.get("code")).replace("`", "")) for e in ep.get("errors") or [] if isinstance(e, dict)],
                        [(e["status"], e["response_code"], e["error_code"]) for e in req["docs"]["errors"]]))
    unreached = _unreached_objects(ep)
    if unreached:
        diffs.append(f"objects {unreached} are never referenced by an `object:` field, so their rows are not in docs")
    return [d for d in diffs if d]


def roundtrip(api_dir, bruno_root):
    """Re-parse every matched request and compare its docs tables with the flattened source."""
    out = []
    _, eps = _load_spec(Path(api_dir), [], out)
    groups, _ = _match(eps, Path(bruno_root), [])
    for i, e in enumerate(eps):
        if not e["rel"]:
            continue
        out += [f"{e['rel']}: key {k} not migrated" for k in _unmigrated_keys(e["ep"])]
        if i not in groups:
            out.append(f"{e['rel']}: no request matches {str(e['ep']['method']).upper()} {e['ep']['path']}")
        for path, req in groups.get(i, []):
            diffs = _diff(e["ep"], req)
            if diffs:
                out.append(f"{e['rel']} -> {path.relative_to(bruno_root).as_posix()}: " + "; ".join(diffs))
    return out


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    args = [a for a in argv if a != "--check"]
    usage = "usage: migrate.py <docs/api> <bruno-root> [--check]"
    if len(args) != 2 or not Path(args[0]).is_dir():
        print(usage, file=sys.stderr)
        return 2
    api_dir, root = Path(args[0]), Path(args[1])
    if not (api_dir / "_meta.yaml").is_file():
        print(f"migrate.py: {api_dir / '_meta.yaml'} not found; the first argument is the legacy docs/api "
              f"directory\n{usage}", file=sys.stderr)
        return 2
    if not _load_spec(api_dir, [])[1]:
        print(f"migrate.py: no endpoint loaded from {api_dir}\n{usage}", file=sys.stderr)
        return 2
    if "--check" not in argv:
        report = migrate(api_dir, root)
        for key in ("updated", "created", "orphans", "warnings"):
            print(f"{key}: {len(report[key])}")
            for item in report[key]:
                print(f"  {item}")
    problems = roundtrip(api_dir, root)
    for p in problems:
        print(f"MISMATCH {p}")
    print(f"FAIL: {len(problems)} round-trip mismatch(es)" if problems else "PASS: round-trip clean")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
