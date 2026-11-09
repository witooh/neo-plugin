#!/usr/bin/env python3
"""Shared parser for Bruno OpenCollection request files whose `docs:` block holds the endpoint contract.

Imported by brunocheck.py and driftcheck.py. Stdlib + PyYAML only.
"""
import json
import re
from pathlib import Path

import yaml

FIELD_HEADER = ["Field Name", "Type", "Mandatory", "Description", "Possible Value"]
ERROR_HEADER = ["Status", "Response Code", "Error Code", "Error Messages", "Description"]
TYPES = {"String", "Number", "Boolean", "Object", "Array"}
MANDATORY = {"Yes", "No"}
TOP_ORDER = ["info", "http", "runtime", "settings", "docs"]

_HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
_FENCE = re.compile(r"^\s*```")
_SEPARATOR_CELL = re.compile(r"^:?-+:?$")
_VAR = re.compile(r"\{\{[^{}]*\}\}")
_ENDPOINT = re.compile(r"`?\s*(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(\S+?)\s*`?\s*$")
_STATUS = re.compile(r"^HTTP Status:\s*(\d+)")
_TABLE_SECTIONS = {
    "headers": "headers",
    "path parameters": "path",
    "query parameters": "query",
    "body (json)": "body",
}
_KNOWN_TOP = {"Purpose", "Request", "Response"}


class ParseError(Exception):
    def __init__(self, file, line, msg):
        super().__init__(f"{file}:{line}: {msg}")
        self.file = file
        self.line = line
        self.msg = msg


def split_sections(md):
    sections = []
    current = None
    in_fence = False
    for number, line in enumerate(md.splitlines(), 1):
        if _FENCE.match(line):
            in_fence = not in_fence
        m = None if in_fence else _HEADING.match(line)
        if m:
            current = {"level": len(m.group(1)), "title": m.group(2), "body": "", "line": number}
            sections.append(current)
        elif current is not None:
            current["body"] += line + "\n"
    return sections


def _split_cells(line):
    cells = line.strip().replace("\\|", "\x00").split("|")
    if cells and cells[0] == "":
        cells = cells[1:]
    if cells and cells[-1] == "":
        cells = cells[:-1]
    return [c.replace("\x00", "|").strip() for c in cells]


def parse_table(text):
    block = []
    for line in text.splitlines():
        if line.lstrip().startswith("|"):
            block.append(line)
        elif block:
            break
    if not block:
        return None
    parsed = [_split_cells(line) for line in block]
    header, rest = parsed[0], parsed[1:]
    if rest and all(_SEPARATOR_CELL.match(c) for c in rest[0] if c):
        rest = rest[1:]
    return header, rest


def _cell(row, index):
    return row[index] if index < len(row) else ""


def field_rows(header, rows):
    return [{"name": _cell(r, 0).replace("`", ""), "type": _cell(r, 1), "mandatory": _cell(r, 2),
             "description": _cell(r, 3), "possible": _cell(r, 4)} for r in rows]


def error_rows(header, rows):
    out = []
    for r in rows:
        status = _cell(r, 0).replace("`", "")
        out.append({"status": int(status) if status.isdigit() else None,
                    "response_code": _cell(r, 1).replace("`", ""),
                    "error_code": _cell(r, 2).replace("`", ""),
                    "error_messages": _cell(r, 3).replace("`", ""),
                    "description": _cell(r, 4)})
    return out


def json_with_vars(text):
    out = []
    i = 0
    in_string = False
    while i < len(text):
        ch = text[i]
        if in_string:
            out.append(ch)
            if ch == "\\" and i + 1 < len(text):
                out.append(text[i + 1])
                i += 1
            elif ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
            out.append(ch)
        else:
            m = _VAR.match(text, i)
            if m:
                out.append("null")
                i = m.end()
                continue
            out.append(ch)
        i += 1
    return json.loads("".join(out))


def key_paths(obj):
    paths = set()

    def walk(value, prefix):
        if isinstance(value, dict):
            for key, child in value.items():
                path = f"{prefix}.{key}" if prefix else key
                paths.add(path)
                walk(child, path)
        elif isinstance(value, list):
            for item in value:
                walk(item, prefix + "[]")

    walk(obj, "")
    return paths


def group_by_parent(rows):
    tree = {}
    for row in rows:
        parent, _, leaf = row["name"].rpartition(".")
        tree.setdefault(parent, []).append({**row, "name": leaf})
    return tree


def _first_fence(body):
    m = re.search(r"```[^\n]*\n(.*?)```", body, re.S)
    return m.group(1).strip() if m else None


def _fields(body):
    t = parse_table(body)
    return field_rows(*t) if t else []


def parse_request_docs(md):
    out = {"headings": [], "endpoint": None, "auth": None,
           "tables": {"headers": [], "path": [], "query": [], "body": []},
           "request_example": None, "responses": {}, "duplicate_statuses": [], "errors": [], "free": []}
    top = None
    status = None
    last_was_body = False
    for sec in split_sections(md):
        title, body = sec["title"], sec["body"]
        out["headings"].append(title)
        if sec["level"] == 2:
            top = title
            status = None
            last_was_body = False
            if title not in _KNOWN_TOP:
                out["free"].append(title)
            continue
        key = title.lower()
        if top == "Request":
            if key == "endpoint":
                m = _ENDPOINT.search(next((l for l in body.splitlines() if l.strip()), ""))
                out["endpoint"] = (m.group(1), m.group(2)) if m else None
            elif key == "auth":
                line = next((l for l in body.splitlines() if l.strip()), "")
                out["auth"] = line.strip().strip("`") or None
            elif key in _TABLE_SECTIONS:
                out["tables"][_TABLE_SECTIONS[key]] = _fields(body)
            elif key == "example" and last_was_body:
                out["request_example"] = _first_fence(body)
            last_was_body = key == "body (json)"
        elif top == "Response":
            m = _STATUS.match(title)
            if m:
                status = int(m.group(1))
                if status in out["responses"]:
                    out["duplicate_statuses"].append(status)
                out["responses"][status] = {"fields": _fields(body), "example": None}
            elif key == "example" and status is not None:
                out["responses"][status]["example"] = _first_fence(body)
            elif key == "error responses":
                t = parse_table(body)
                if t:
                    out["errors"].extend(error_rows(*t))
    return out


def load_yaml_with_order(path):
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise ParseError(str(path), 0, f"cannot read file: {exc}") from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        raise ParseError(str(path), mark.line + 1 if mark else 0, str(exc).splitlines()[0]) from exc
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise ParseError(str(path), 1, "top level is not a mapping")
    order = []
    for line in text.splitlines():
        m = re.match(r"^([a-z]+):", line)
        if m and m.group(1) not in order:
            order.append(m.group(1))
    return data, order


def parse_request(path):
    data, order = load_yaml_with_order(path)
    docs_raw = data.get("docs") or ""
    if not isinstance(docs_raw, str):
        raise ParseError(str(path), 0, f"`docs` must be a string, got {type(docs_raw).__name__}")
    return {"file": str(path), "order": order, "info": data.get("info"), "http": data.get("http"),
            "runtime": data.get("runtime"), "settings": data.get("settings"),
            "docs_raw": docs_raw, "docs": parse_request_docs(docs_raw)}


def parse_root_docs(md):
    out = {"headings": [], "error_body": [], "common_errors": []}
    for sec in split_sections(md):
        out["headings"].append(sec["title"])
        if sec["title"] == "Error Response Body":
            out["error_body"] = _fields(sec["body"])
        elif sec["title"] == "Common Error Responses":
            t = parse_table(sec["body"])
            out["common_errors"] = error_rows(*t) if t else []
    return out


def _env_vars(data):
    variables = data.get("variables") or []
    if isinstance(variables, dict):
        return dict(variables)
    return {v["name"]: v.get("value") for v in variables if isinstance(v, dict) and "name" in v}

