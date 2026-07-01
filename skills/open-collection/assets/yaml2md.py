#!/usr/bin/env python3
"""
yaml2md.py — render a custom-YAML api-spec endpoint (docs/api/<domain>/<endpoint>.yaml)
into create.md-style Markdown, for the OpenCollection `docs:` field (Spec mode).

open-collection owns this renderer: the runnable Bruno collection embeds the human-readable
doc as each request's `docs:` (and the `_meta` index as the collection/folder `docs:`), so the
collection is self-documenting. `colcheck.py` imports `render_endpoint` to verify each request's
`docs:` exactly matches this render (K7).

Navigation (the markdown-hub breadcrumb + relative endpoint-table links) is **off by default** —
those links don't resolve inside Bruno's docs panel. Pass `nav=True` (CLI `--nav`) for the
faithful markdown-hub form (the frozen Phase-0 prototype at docs/api-spec-redesign/samples/
remains the byte-identical reference for that form).

Usage:
  python3 yaml2md.py <endpoint.yaml>             # render one endpoint -> stdout (no nav)
  python3 yaml2md.py --index <_meta.yaml> <dir>  # render the INDEX -> stdout (no nav)
  python3 yaml2md.py --nav <endpoint.yaml>       # faithful markdown-hub form (breadcrumb/links)
"""
import sys
import json
import glob
import os
import yaml

FIELD_HEADER = "| Field Name | Description | Type | Mandatory | Example | Remark |"
FIELD_SEP    = "| ---------- | ----------- | ---- | --------- | ------- | ------ |"


def lit(v):
    """Render an example value exactly as the .md shows it inside backticks."""
    return json.dumps(v)


def row(cells):
    """A markdown table row — empty cells collapse to a single space (` | |`)."""
    return "|" + "|".join(f" {c} " if str(c) != "" else " " for c in cells) + "|"


def fmt_code(c):
    """Backtick an error code token; leave prose phrases plain; split a `/`-list."""
    parts = [p.strip() for p in c.split("/")]
    if len(parts) > 1:
        return " / ".join(f"`{p}`" for p in parts)
    return c if " " in c else f"`{c}`"


def field_row(f):
    name = f.get("name", "")
    desc = f.get("description", "") or ""
    typ = f.get("type", "") or ""
    mand = f.get("mandatory", "") or ""
    if "object" in f:
        example = ""
        remark = f.get("remark") or f"See {f['object']} Object below"
    else:
        example = f"`{lit(f['example'])}`" if "example" in f else ""
        remark = f.get("remark", "") or ""
    return row([f"`{name}`", desc, typ, mand, example, remark])


def field_table(fields):
    out = [FIELD_HEADER, FIELD_SEP]
    out += [field_row(f) for f in fields]
    return "\n".join(out)


def error_table(errors):
    has_code = any("code" in e for e in errors)
    has_msg = any("message" in e for e in errors)
    cols = ["Status"]
    if has_code:
        cols.append("Error Code")
    if has_msg:
        cols.append("Error Message")
    cols.append("Description")
    # dash widths match the header word lengths (cosmetic parity with the source)
    sep = "| " + " | ".join("-" * len(c) for c in cols) + " |"
    out = [row(cols), sep]
    for e in errors:
        cells = [str(e.get("status", ""))]
        if has_code:
            c = e.get("code", "")
            cells.append(fmt_code(c) if c else "")
        if has_msg:
            cells.append(e.get("message", "") or "")
        cells.append(e.get("description", "") or "")
        out.append(row(cells))
    return "\n".join(out)


def code_block(s):
    return "```json\n" + s.rstrip("\n") + "\n```"


def render_endpoint(ep, nav=False):
    """One endpoint -> Markdown. `nav` adds the markdown-hub breadcrumb (off for Bruno docs:)."""
    domain = ep.get("domain", "")
    name = ep.get("endpoint", "")
    P = []  # parts joined by a blank line
    if nav:
        P.append(f"> [API Documentation](../index.md) > [{domain}](./) > {name}")
    P.append(f"# {name}")
    if ep.get("description"):
        P.append(ep["description"].rstrip("\n"))
    P.append(
        f"- **Method:** `{ep.get('method','')}`\n"
        f"- **Path:** `{ep.get('path','')}`\n"
        f"- **Auth:** `{ep.get('auth','')}`"
    )
    if ep.get("path_params"):
        P.append("## Path Parameters")
        P.append(field_table(ep["path_params"]))
    if ep.get("query_params"):
        P.append("## Query Parameters")
        P.append(field_table(ep["query_params"]))
    rb = ep.get("request_body")
    if rb:
        P.append("## Request Body")
        P.append(field_table(rb["fields"]))
        if rb.get("example"):
            P.append("## Request Example")
            P.append(code_block(rb["example"]))
    for resp in ep.get("responses", []):
        head = f"Response ({resp.get('status','')}"
        if resp.get("description"):
            head += f" {resp['description']}"
        head += ")"
        P.append(f"## {head}")
        P.append(field_table(resp["fields"]))
        for obj_name, obj_fields in (resp.get("objects") or {}).items():
            P.append(f"**{obj_name} Object:**")
            P.append(field_table(obj_fields))
        if resp.get("example"):
            P.append("## Response Example")
            P.append(code_block(resp["example"]))
    if ep.get("business_logic"):
        P.append("## Business Logic")
        P.append(ep["business_logic"].rstrip("\n"))
    if ep.get("errors"):
        P.append("## Error Responses")
        P.append(error_table(ep["errors"]))
    if ep.get("notes"):
        P.append("## Notes")
        P.append("\n".join(f"- {n}" for n in ep["notes"]))
    return "\n\n".join(P) + "\n"


def render_index(meta, ddir, nav=False):
    """The api-spec INDEX -> Markdown (collection-root docs:). `nav` adds per-endpoint file links."""
    P = []
    P.append(f"# {meta.get('title','')}")
    P.append(f"**Version:** {meta.get('version','')}\n**Base URL:** `{meta.get('base_url','')}`")
    if meta.get("overview"):
        P.append("## Overview")
        P.append(meta["overview"].rstrip("\n"))
    if meta.get("field_info"):
        P.append("## Field Information")
        for key, rows in meta["field_info"].items():
            P.append(f"### {key}")
            t = ["| Code | Description |", "| ---- | ----------- |"]
            t += [f"| `{r['code']}` | {r['description']} |" for r in rows]
            P.append("\n".join(t))
    # group endpoints by domain
    eps = []
    for fp in sorted(glob.glob(os.path.join(ddir, "**", "*.yaml"), recursive=True)):
        if os.path.basename(fp) == "_meta.yaml":
            continue
        ep = yaml.safe_load(open(fp, encoding="utf-8"))
        ep["_file"] = os.path.relpath(fp, ddir)
        eps.append(ep)
    domains = {}
    for ep in eps:
        domains.setdefault(ep.get("domain", ""), []).append(ep)
    dmeta = meta.get("domains", {})
    ordered = sorted(domains, key=lambda d: dmeta.get(d, {}).get("seq", 999))
    P.append("## Endpoints")
    for d in ordered:
        P.append(f"### {dmeta.get(d, {}).get('title', d)}")
        if dmeta.get(d, {}).get("description"):
            P.append(dmeta[d]["description"].rstrip("\n"))
        if nav:
            t = ["| Method | Path | Endpoint | File |", "| ------ | ---- | -------- | ---- |"]
            for ep in domains[d]:
                f = ep["_file"]
                stem = os.path.splitext(os.path.basename(f))[0]
                t.append(f"| `{ep.get('method','')}` | `{ep.get('path','')}` | {ep.get('endpoint','')} | [{stem}]({f}) |")
        else:
            t = ["| Method | Path | Endpoint |", "| ------ | ---- | -------- |"]
            for ep in domains[d]:
                t.append(f"| `{ep.get('method','')}` | `{ep.get('path','')}` | {ep.get('endpoint','')} |")
        P.append("\n".join(t))
    if meta.get("common_errors"):
        P.append("## Common Error Responses")
        ce = ["| Status | Code | Error Message | Description |",
              "| ------ | ---- | ------------- | ----------- |"]
        for e in meta["common_errors"]:
            ce.append(f"| {e.get('status','')} | `{e.get('code','')}` | {e.get('message','')} | {e.get('description','')} |")
        P.append("\n".join(ce))
    return "\n\n".join(P) + "\n"


def main():
    args = sys.argv[1:]
    nav = "--nav" in args
    args = [a for a in args if a != "--nav"]
    if args and args[0] == "--index":
        meta = yaml.safe_load(open(args[1], encoding="utf-8"))
        sys.stdout.write(render_index(meta, args[2], nav=nav))
    else:
        ep = yaml.safe_load(open(args[0], encoding="utf-8"))
        sys.stdout.write(render_endpoint(ep, nav=nav))


if __name__ == "__main__":
    main()
