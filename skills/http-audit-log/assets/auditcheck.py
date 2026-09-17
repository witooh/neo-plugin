#!/usr/bin/env python3
"""Tripwire for the one-row HTTP audit pattern. Not ground truth."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

REQUIRED_COLUMNS = (
    "request_id",
    "http_method",
    "route",
    "status",
    "http_status",
    "response_code",
    "failure_reason",
    "metadata",
    "raw_request",
    "raw_response",
    "duration_ms",
    "created_at",
)

CHECKS = (
    "SUCCESS",
    "FAILED",
    "BETWEEN 100 AND 599",
    "duration_ms >= 0",
)

REQUIRED_FILES = (
    Path("internal/core/domain/audit/auditlog.go"),
    Path("internal/core/domain/audit/repository.go"),
    Path("internal/core/domain/audit/auditlog_test.go"),
    Path("internal/adapters/repository/postgres/audit_log.go"),
    Path("internal/adapters/repository/postgres/queries/audit_log.sql"),
    Path("internal/delivery/http/middleware/audit.go"),
    Path("internal/delivery/http/middleware/audit_test.go"),
)


def fail(msg: str) -> None:
    print(f"FAIL: {msg}", file=sys.stderr)


def ok(msg: str) -> None:
    print(f"PASS: {msg}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def arg_count(inside: str) -> int:
    text = inside.strip()
    if not text:
        return 0
    depth = 0
    n = 1
    for ch in text:
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            n += 1
    return n


def find_up_migration(root: Path) -> Path | None:
    hits = list(root.rglob("*create_audit_log.up.sql"))
    if hits:
        return hits[0]
    for p in root.rglob("*.up.sql"):
        if re.search(r'CREATE TABLE IF NOT EXISTS\s+"?audit_log"?', read(p), re.I):
            return p
    return None


def check_migration(root: Path) -> int:
    errors = 0
    path = find_up_migration(root)
    if path is None:
        fail("no audit_log up-migration found")
        return 1
    text = read(path)
    for col in REQUIRED_COLUMNS:
        if col not in text:
            fail(f"{path}: missing column {col}")
            errors += 1
    for needle in CHECKS:
        if needle not in text:
            fail(f"{path}: missing {needle!r}")
            errors += 1
    if "audit_log_route_created_idx" not in text or "audit_log_status_created_idx" not in text:
        fail(f"{path}: missing route/status indexes")
        errors += 1
    if errors == 0:
        ok(f"migration {path.relative_to(root)}")
    return errors


def check_files(root: Path) -> int:
    errors = 0
    for rel in REQUIRED_FILES:
        path = root / rel
        if not path.is_file():
            fail(f"missing {rel}")
            errors += 1
        else:
            ok(str(rel))
    query = root / "internal/adapters/repository/postgres/queries/audit_log.sql"
    if query.is_file() and "InsertAuditLog" not in read(query):
        fail("queries/audit_log.sql missing InsertAuditLog")
        errors += 1
    return errors


def first_use_is_audit(setup_src: str) -> bool:
    uses = re.findall(r"r\.Use\(([^)]*)\)", setup_src)
    if not uses:
        return False
    return uses[0].strip().startswith("Audit(")


def check_middleware(root: Path) -> int:
    errors = 0
    setup = root / "internal/delivery/http/middleware/middleware.go"
    audit = root / "internal/delivery/http/middleware/audit.go"
    if not setup.is_file():
        fail("missing middleware.go")
        return 1
    setup_src = read(setup)
    if "AuditLogRepository" not in setup_src:
        fail("Setup does not take an AuditLogRepository")
        errors += 1
    if not first_use_is_audit(setup_src):
        fail("Audit is not the first r.Use in Setup (must be outermost)")
        errors += 1
    else:
        ok("Audit is outermost in Setup")

    if not audit.is_file():
        return errors + 1
    src = read(audit)
    persist = src
    m = re.search(r"func persistAuditLog\([\s\S]*?\n\}", src)
    if m:
        persist = m.group(0)
    if "if writer == nil" not in persist:
        fail("persistAuditLog missing nil-writer no-op")
        errors += 1
    else:
        ok("nil writer is a no-op")
    if "Abort(" in persist:
        fail("persistAuditLog aborts the request")
        errors += 1
    if "failed to persist audit log" not in src:
        fail("persist failure is not logged")
        errors += 1
    if "uuid.New()" not in src:
        fail("request_id is not uuid.New()")
        errors += 1
    else:
        ok("request_id is uuid.New()")
    return errors


def check_call_arity(root: Path) -> int:
    errors = 0
    patterns = (
        ("middleware.Setup(", 3),
        ("router.New(", 3),
    )
    found = {needle: 0 for needle, _ in patterns}
    for path in root.rglob("*.go"):
        if "/sqlc/" in path.as_posix() or path.name.endswith("_gen.go"):
            continue
        text = read(path)
        rel = path.relative_to(root)
        for needle, want in patterns:
            start = 0
            while True:
                i = text.find(needle, start)
                if i < 0:
                    break
                found[needle] += 1
                open_paren = i + len(needle) - 1
                depth = 0
                j = open_paren
                while j < len(text):
                    if text[j] == "(":
                        depth += 1
                    elif text[j] == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    j += 1
                inside = text[open_paren + 1 : j]
                n = arg_count(inside)
                if n != want:
                    fail(f"{rel}: {needle[:-1]} has {n} arg(s), want {want}")
                    errors += 1
                start = j + 1
    for needle, _want in patterns:
        if found[needle] == 0:
            fail(f"no {needle[:-1]} callsite")
            errors += 1
    if errors == 0:
        ok("Setup/New callsites take the audit repo")
    return errors


def check_composition_root(root: Path) -> int:
    cmd = root / "cmd"
    if not cmd.is_dir():
        fail("missing cmd/")
        return 1
    texts = [read(p) for p in cmd.rglob("*.go")]
    if not any("NewAuditLogRepository" in t for t in texts):
        fail("cmd/ never constructs NewAuditLogRepository")
        return 1
    ok("cmd/ constructs NewAuditLogRepository")
    return 0


def check_placeholders(root: Path) -> int:
    errors = 0
    needles = ("__MODULE__", "__SCHEMA__", "__FAILED_PATH__", "__SUCCESS_PATH__")
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix not in {".go", ".ts", ".sql"}:
            continue
        text = read(path)
        hit = [n for n in needles if n in text]
        if hit:
            fail(f"unsubstituted {', '.join(hit)} in {path.relative_to(root)}")
            errors += 1
    if errors == 0:
        ok("no leftover template placeholders")
    return errors


def check_sqlc_overrides(root: Path) -> int:
    path = root / "sqlc.yaml"
    if not path.is_file():
        fail("missing sqlc.yaml")
        return 1
    text = read(path)
    errors = 0
    if "uuid" not in text:
        fail("sqlc.yaml missing uuid override")
        errors += 1
    if "jsonb" not in text:
        fail("sqlc.yaml missing jsonb override")
        errors += 1
    if errors == 0:
        ok("sqlc.yaml has uuid + jsonb overrides")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("root", nargs="?", default=".", help="service root (default: cwd)")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if not (root / "go.mod").is_file():
        fail(f"no go.mod under {root}")
        return 1

    errors = 0
    errors += check_migration(root)
    errors += check_files(root)
    errors += check_sqlc_overrides(root)
    errors += check_middleware(root)
    errors += check_composition_root(root)
    errors += check_call_arity(root)
    errors += check_placeholders(root)
    if errors:
        print(f"FAIL: {errors} error(s)", file=sys.stderr)
        return 1
    print("PASS: 0 error(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
