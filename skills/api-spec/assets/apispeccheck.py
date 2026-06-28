#!/usr/bin/env python3
"""
apispeccheck.py — L1 tripwire for the custom-YAML API spec under docs/api/.

Validates every endpoint file + _meta.yaml against the api-spec schema
(references/api-spec-template.md), and (re)generates the navigation index.md
from the spec so it can never drift.

  python3 apispeccheck.py <api-dir>            # validate + regenerate <api-dir>/index.md
  python3 apispeccheck.py <api-dir> --check    # validate + assert index.md is in sync (no write)

Exit 0 = PASS (0 errors); exit 1 = at least one ERROR. NOTE lines never fail.
Requires PyYAML (same dependency as the openapi-doc / open-collection assets).
"""
import sys
import os
import re
import json
import glob

try:
    import yaml
except ImportError:
    sys.stderr.write("apispeccheck: PyYAML is required (pip install pyyaml)\n")
    sys.exit(2)

ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"}
ALLOWED_MANDATORY = {"M", "O"}
KNOWN_TYPES = {"String", "Number", "Boolean", "Object", "Array", "Integer"}

errors = []
notes = []


def err(msg):
    errors.append(msg)


def note(msg):
    notes.append(msg)


def load_yaml(path):
    try:
        return yaml.safe_load(open(path, encoding="utf-8")) or {}
    except Exception as e:  # noqa: BLE001
        err(f"{os.path.basename(path)}: YAML parse error — {e}")
        return None


# ---- field / error / endpoint validation ---------------------------------

def check_fields(fields, ctx, objects_defined):
    if not isinstance(fields, list):
        err(f"{ctx}: expected a list of fields")
        return
    for f in fields:
        if not isinstance(f, dict):
            err(f"{ctx}: each field must be a mapping, got {type(f).__name__}")
            continue
        name = f.get("name", "?")
        for k in ("name", "type", "mandatory"):
            if k not in f:
                err(f"{ctx}: field '{name}' is missing '{k}'")
        if "mandatory" in f and f["mandatory"] not in ALLOWED_MANDATORY:
            err(f"{ctx}: field '{name}' mandatory must be M|O, got {f['mandatory']!r}")
        if f.get("type") and f["type"] not in KNOWN_TYPES:
            note(f"{ctx}: field '{name}' has unusual type {f['type']!r} — needs fresh-eyes")
        if "object" in f and f["object"] not in objects_defined:
            err(f"{ctx}: field '{name}' references object '{f['object']}' not defined in objects:")


def check_errors(errs, ctx):
    if not isinstance(errs, list):
        err(f"{ctx}: errors must be a list")
        return
    for e in errs:
        if not isinstance(e, dict):
            err(f"{ctx}: each error must be a mapping")
            continue
        if "status" not in e:
            err(f"{ctx}: an error is missing 'status'")
        if "description" not in e and "message" not in e:
            err(f"{ctx}: error {e.get('status','?')} needs a 'description' or 'message'")


def check_json(s, ctx):
    try:
        json.loads(s)
    except Exception as e:  # noqa: BLE001
        err(f"{ctx}: example is not valid JSON — {e}")


def check_endpoint(path, doc):
    fn = os.path.relpath(path)
    if not isinstance(doc, dict):
        err(f"{fn}: top level must be a mapping")
        return None
    for k in ("endpoint", "domain", "method", "path"):
        if k not in doc:
            err(f"{fn}: missing required key '{k}'")
    method = str(doc.get("method", "")).upper()
    if method and method not in ALLOWED_METHODS:
        err(f"{fn}: method '{doc.get('method')}' is not a valid HTTP method")
    # path placeholders must be documented in path_params
    placeholders = set(re.findall(r"\{([^}]+)\}", str(doc.get("path", ""))))
    pp_names = {p.get("name") for p in (doc.get("path_params") or []) if isinstance(p, dict)}
    for ph in placeholders - pp_names:
        err(f"{fn}: path param '{{{ph}}}' has no entry in path_params")
    # params
    for key in ("path_params", "query_params"):
        if doc.get(key):
            check_fields(doc[key], f"{fn} {key}", set())
    # request body
    rb = doc.get("request_body")
    if rb:
        if "fields" in rb:
            check_fields(rb["fields"], f"{fn} request_body", set())
        if rb.get("example"):
            check_json(rb["example"], f"{fn} request_body.example")
    # responses
    for r in (doc.get("responses") or []):
        if "status" not in r:
            err(f"{fn}: a response is missing 'status'")
        objs = r.get("objects") or {}
        if not isinstance(objs, dict):
            err(f"{fn}: response {r.get('status','?')} objects: must be a mapping")
            objs = {}
        check_fields(r.get("fields") or [], f"{fn} response {r.get('status','?')}", set(objs.keys()))
        for oname, ofields in objs.items():
            check_fields(ofields, f"{fn} object {oname}", set(objs.keys()))
        if r.get("example"):
            check_json(r["example"], f"{fn} response {r.get('status','?')}.example")
    if doc.get("errors"):
        check_errors(doc["errors"], fn)
    if "notes" in doc and not isinstance(doc["notes"], list):
        err(f"{fn}: notes must be a list (omit the key when empty)")
    return doc


def check_meta(meta):
    if meta is None:
        return
    for k in ("title", "version", "base_url"):
        if k not in meta:
            err(f"_meta.yaml: missing '{k}'")
    if meta.get("common_errors"):
        check_errors(meta["common_errors"], "_meta.yaml common_errors")


# ---- index.md generation (from _meta + endpoint files) -------------------

def render_index(meta, endpoints):
    P = []
    P.append(f"# {meta.get('title','')}")
    P.append(f"**Version:** {meta.get('version','')}\n**Base URL:** `{meta.get('base_url','')}`")
    if meta.get("overview"):
        P.append("## Overview")
        P.append(str(meta["overview"]).rstrip("\n"))
    if meta.get("field_info"):
        P.append("## Field Information")
        for key, rows in meta["field_info"].items():
            P.append(f"### {key}")
            t = ["| Code | Description |", "| ---- | ----------- |"]
            t += [f"| `{r.get('code','')}` | {r.get('description','')} |" for r in rows]
            P.append("\n".join(t))
    # group endpoints by domain
    by_domain = {}
    for ep, rel in endpoints:
        by_domain.setdefault(ep.get("domain", ""), []).append((ep, rel))
    extra = meta.get("extra_endpoints") or []
    for x in extra:
        by_domain.setdefault(x.get("domain", ""), [])
    dmeta = meta.get("domains", {}) or {}
    ordered = sorted(by_domain, key=lambda d: dmeta.get(d, {}).get("seq", 999))
    P.append("## Endpoints")
    for d in ordered:
        P.append(f"### {dmeta.get(d, {}).get('title', d)}")
        if dmeta.get(d, {}).get("description"):
            P.append(str(dmeta[d]["description"]).rstrip("\n"))
        rows = ["| Method | Path | Endpoint | File |", "| ------ | ---- | -------- | ---- |"]
        for ep, rel in by_domain[d]:
            stem = os.path.splitext(os.path.basename(rel))[0]
            rows.append(f"| `{ep.get('method','')}` | `{ep.get('path','')}` | {ep.get('endpoint','')} | [{stem}]({rel}) |")
        for x in extra:
            if x.get("domain") == d:
                rows.append(f"| `{x.get('method','')}` | `{x.get('path','')}` | {x.get('description','')} | — |")
        P.append("\n".join(rows))
    if meta.get("common_errors"):
        P.append("## Common Error Responses")
        ce = ["| Status | Code | Error Message | Description |",
              "| ------ | ---- | ------------- | ----------- |"]
        for e in meta["common_errors"]:
            ce.append(f"| {e.get('status','')} | `{e.get('code','')}` | {e.get('message','')} | {e.get('description','')} |")
        P.append("\n".join(ce))
    return "\n\n".join(P) + "\n"


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    check_only = "--check" in sys.argv
    if not args:
        sys.stderr.write("usage: apispeccheck.py <api-dir> [--check]\n")
        sys.exit(2)
    api_dir = args[0]
    if not os.path.isdir(api_dir):
        sys.stderr.write(f"apispeccheck: {api_dir} is not a directory\n")
        sys.exit(2)

    meta_path = os.path.join(api_dir, "_meta.yaml")
    meta = load_yaml(meta_path) if os.path.exists(meta_path) else None
    if meta is None and not os.path.exists(meta_path):
        err("_meta.yaml: missing (the global metadata file is required)")
        meta = {}
    check_meta(meta)

    endpoints = []  # (doc, relpath-from-api_dir)
    for fp in sorted(glob.glob(os.path.join(api_dir, "**", "*.yaml"), recursive=True)):
        if os.path.basename(fp) == "_meta.yaml":
            continue
        doc = load_yaml(fp)
        if doc is None:
            continue
        checked = check_endpoint(fp, doc)
        if checked is not None:
            endpoints.append((checked, os.path.relpath(fp, api_dir)))

    if not endpoints:
        note("no endpoint YAML files found under " + api_dir)

    # index.md — regenerate or check-sync
    index_path = os.path.join(api_dir, "index.md")
    new_index = render_index(meta or {}, endpoints)
    if check_only:
        old = open(index_path, encoding="utf-8").read() if os.path.exists(index_path) else ""
        if old != new_index:
            err("index.md is out of sync with the spec — re-run without --check to regenerate")
    elif not errors:
        with open(index_path, "w", encoding="utf-8") as fh:
            fh.write(new_index)

    for n in notes:
        print("NOTE:", n)
    for e in errors:
        print("ERROR:", e)
    if errors:
        print(f"FAIL — {len(errors)} error(s)")
        sys.exit(1)
    action = "checked" if check_only else "validated + index.md regenerated"
    print(f"PASS — 0 error(s) ({len(endpoints)} endpoint(s) {action})")


if __name__ == "__main__":
    main()
