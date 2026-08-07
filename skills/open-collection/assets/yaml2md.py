#!/usr/bin/env python3
"""
yaml2md.py — render a custom-YAML api-spec endpoint (docs/api/<domain>/<endpoint>.yaml)
into create.md-style Markdown, for the OpenCollection `docs:` field (Spec mode).

open-collection owns this renderer: the runnable Bruno collection embeds the human-readable
doc as each request's `docs:` (and the `_meta` index as the collection/folder `docs:`), so the
collection is self-documenting. `colcheck.py` imports `render_endpoint` to verify each request's
`docs:` exactly matches this render (K7).

Audience (non-negotiable): Bruno `docs:` is for **other teams that call this API**. The
renderer applies the Audience filter (same Keep/Drop spirit as confluence-api-doc) so ticket
framing, evidence paths, ALIGN logs, internal renames, and pure-dev notes never land in the
collection. Wire fields / examples / error codes stay verbatim.

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
import re
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
    desc = audience_text(f.get("description", "") or "")
    typ = f.get("type", "") or ""
    mand = f.get("mandatory", "") or ""
    if "object" in f:
        example = ""
        raw_remark = f.get("remark") or f"See {f['object']} Object below"
        remark = audience_text(raw_remark) if f.get("remark") else raw_remark
        if f.get("remark") and not remark:
            remark = f"See {f['object']} Object below"
    else:
        example = f"`{lit(f['example'])}`" if "example" in f else ""
        remark = audience_text(f.get("remark", "") or "")
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
            # public error message stays (caller sees it); only strip framing tails
            cells.append(audience_text(e.get("message", "") or ""))
        cells.append(audience_text(e.get("description", "") or ""))
        out.append(row(cells))
    return "\n".join(out)


def code_block(s):
    return "```json\n" + s.rstrip("\n") + "\n```"

# ── Audience filter (consumer docs — not a neo dump) ──────────────
# Keep wire + caller-visible behaviour. Drop ticket framing, evidence paths,
# ALIGN decision-log lines, internal renames, implementer changelog notes.
# Patterns are intentionally narrow — false positives hide caller-needed prose.

# Ticket keys / card refs only (case-sensitive — do not use re.I on [A-Z] classes).
_RE_TICKET = re.compile(
    r"\bGI-\d+(?:-AC\d+)?\b"       # GI-2226, GI-2226-AC01
    r"|\bAC-\d{2,4}\b"              # AC-001
    r"|\[[A-Z][A-Z0-9]*-(?:[A-Z0-9]+-)*[A-Z0-9]+\]"  # [PAY-BFID-02-A], not [transfer-confirm]
)
# Evidence / provenance — path tokens and "Evidence: …" clauses that cite them.
_RE_EVIDENCE = re.compile(
    r"(?i:\bEvidence\s*:\s*(?:`?docs/(?:knowledge|tasks|api)/[^\s`)\],;]+`?"
    r"(?:\s*[,;]\s*`?docs/(?:knowledge|tasks|api)/[^\s`)\],;]+`?)*))"
    r"|`?docs/(?:knowledge|tasks)/[^\s`)\],;]+`?"  # bare repo paths (not docs/api endpoint refs)
    r"|(?i:\bcommit\s+`?[0-9a-f]{7,40}`?)"
)
# Decision-log ALIGN is always uppercase in our api-specs — do NOT match English "align".
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
# Collapse runs of spaces/tabs only between non-space chars — never eat list indent.
_RE_WS = re.compile(r"(?<=\S)[ \t]{2,}")
_RE_SPACE_PUNCT = re.compile(r" +([,.;:])")
# Whole-note drop — ALIGN is uppercase-only so English "align" notes survive.
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

    Clean strings (no Drop-column hit) return **byte-identical** — no whitespace/list
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
    t = re.sub(r"\s*[—–-]\s*$", "", t)
    t = re.sub(r"^\s*[—–-]\s*", "", t)
    t = re.sub(r"\(\s*;\s*", "(", t)
    t = re.sub(r"\s*;\s*\)", ")", t)
    t = re.sub(r"\s*,\s*,+", ", ", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = re.sub(r" +\n", "\n", t)
    return t.strip(" \t\n;,-—–")


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


def render_endpoint(ep, nav=False):
    """One endpoint -> Markdown (Audience-filtered). `nav` adds the markdown-hub breadcrumb."""
    domain = ep.get("domain", "")
    name = ep.get("endpoint", "")
    P = []  # parts joined by a blank line
    if nav:
        P.append(f"> [API Documentation](../index.md) > [{domain}](./) > {name}")
    P.append(f"# {name}")
    # never emit covers_ac
    if ep.get("description"):
        desc = audience_text(ep["description"].rstrip("\n"))
        if desc:
            P.append(desc)
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
            head += f" {audience_text(resp['description'])}"
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
        bl = audience_text(ep["business_logic"].rstrip("\n"))
        if bl:
            P.append("## Business Logic")
            P.append(bl)
    if ep.get("errors"):
        P.append("## Error Responses")
        P.append(error_table(ep["errors"]))
    notes = audience_notes(ep.get("notes"))
    if notes:
        P.append("## Notes")
        P.append("\n".join(f"- {n}" for n in notes))
    return "\n\n".join(P) + "\n"


def render_index(meta, ddir, nav=False):
    """The api-spec INDEX -> Markdown (collection-root docs:). Audience-filtered overview."""
    P = []
    P.append(f"# {meta.get('title','')}")
    P.append(f"**Version:** {meta.get('version','')}\n**Base URL:** `{meta.get('base_url','')}`")
    if meta.get("overview"):
        ov = audience_text(meta["overview"].rstrip("\n"))
        if ov:
            P.append("## Overview")
            P.append(ov)
    if meta.get("field_info"):
        P.append("## Field Information")
        for key, rows in meta["field_info"].items():
            P.append(f"### {key}")
            t = ["| Code | Description |", "| ---- | ----------- |"]
            t += [f"| `{r['code']}` | {audience_text(r.get('description',''))} |" for r in rows]
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
            gd = audience_text(dmeta[d]["description"].rstrip("\n"))
            if gd:
                P.append(gd)
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
            ce.append(
                f"| {e.get('status','')} | `{e.get('code','')}` | "
                f"{audience_text(e.get('message',''))} | {audience_text(e.get('description',''))} |"
            )
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
