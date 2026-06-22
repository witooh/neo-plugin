#!/usr/bin/env python3
"""Scaffold a new Go hexagonal/DDD service from the bundled frozen template.

Copies ``assets/template/`` into a target directory, substitutes the template
sentinels with the new service's identity, then (best-effort) tidies, git-inits,
and builds so the result compiles and serves ``GET /health`` immediately.

The frozen template is a real, compilable service under a sentinel module path
(``example.com/neo/service``) — it is CI-verifiable as-is. Generation is a single
deterministic string substitution; generic steering placeholders ({{MODULE_PATH}},
<Domain>, …) are NOT sentinels and are left untouched for neo to fill per-domain.

Usage:
    scaffold.py --target-dir DIR --module-path PATH --service-name NAME --service-id ID
                [--force] [--no-build] [--no-git] [--no-tidy]
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

# Sentinels baked into assets/template/. Each maps to the new service's identity.
SENTINEL_MODULE = "example.com/neo/service"
SENTINEL_NAME = "neo-service"
SENTINEL_ID = "NEOSVC"

SKIP_DIRS = {".git", "__pycache__", "node_modules", "vendor"}
AUTH_NEEDLES = (
    "could not read Username", "terminal prompts disabled", "410 Gone",
    "authentication required", "fatal: could not read", "Authentication failed",
)


def log(msg: str) -> None:
    print(msg, flush=True)


def fail(msg: str) -> None:
    print(f"error: {msg}", file=sys.stderr, flush=True)
    sys.exit(1)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Scaffold a new Go service from the bundled template.")
    p.add_argument("--target-dir", required=True, help="where to create the new project")
    p.add_argument("--module-path", required=True, help="Go module path, e.g. gitlab.example.com/org/foo-service")
    p.add_argument("--service-name", required=True, help="kebab-case service name, e.g. foo-service")
    p.add_argument("--service-id", required=True, help="UPPER service id, e.g. NEOFOO")
    p.add_argument("--force", action="store_true", help="allow a non-empty target dir")
    p.add_argument("--no-build", action="store_true", help="skip the final go build")
    p.add_argument("--no-git", action="store_true", help="skip git init")
    p.add_argument("--no-tidy", action="store_true", help="skip go mod tidy")
    return p.parse_args()


def validate(args: argparse.Namespace) -> None:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.\-/_~]+", args.module_path):
        fail(f"--module-path looks invalid: {args.module_path!r}")
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", args.service_name):
        fail(f"--service-name must be kebab-case [a-z0-9-]: {args.service_name!r}")
    if not re.fullmatch(r"[A-Z0-9_]+", args.service_id):
        fail(f"--service-id must be UPPER [A-Z0-9_]: {args.service_id!r}")


def preflight(target: Path, force: bool) -> None:
    if (target / ".git").exists():
        fail(f"{target} already contains a .git/ — refusing to scaffold over an existing repo")
    if target.exists() and any(target.iterdir()) and not force:
        fail(f"{target} is not empty (pass --force to scaffold into it anyway)")


def copy_template(src: Path, target: Path) -> None:
    def ignore(_dir: str, names: list[str]) -> list[str]:
        return [n for n in names if n in SKIP_DIRS or n.endswith(".pyc") or n == ".DS_Store"]
    shutil.copytree(src, target, ignore=ignore, dirs_exist_ok=True)


def walk_texts(root: Path):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            path = Path(dirpath) / name
            try:
                yield path, path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue  # binary or unreadable — leave as copied


def substitute(target: Path, mapping: dict[str, str]) -> dict[str, int]:
    """Single-pass replace of every sentinel via one regex, so a replacement's
    text is never re-scanned (e.g. a module path that itself contains the name
    sentinel). Returns files-touched per sentinel."""
    sentinels = sorted(mapping, key=len, reverse=True)
    pattern = re.compile("|".join(re.escape(s) for s in sentinels))
    counts = {s: 0 for s in sentinels}
    for path, text in walk_texts(target):
        present = [s for s in sentinels if s in text]
        if not present:
            continue
        path.write_text(pattern.sub(lambda m: mapping[m.group(0)], text), encoding="utf-8")
        for s in present:
            counts[s] += 1
    return counts


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def indent(s: str) -> str:
    return "\n".join("          " + line for line in s.splitlines())


def main() -> None:
    args = parse_args()
    validate(args)

    src = Path(__file__).resolve().parent / "template"
    if not src.is_dir():
        fail(f"bundled template not found at {src}")
    target = Path(args.target_dir).expanduser().resolve()

    preflight(target, args.force)
    copy_template(src, target)
    log(f"created:  {target} (from frozen template)")

    counts = substitute(target, {
        SENTINEL_MODULE: args.module_path,
        SENTINEL_NAME: args.service_name,
        SENTINEL_ID: args.service_id,
    })
    log(f"rewrote:  module path  {SENTINEL_MODULE} -> {args.module_path}   ({counts[SENTINEL_MODULE]} files)")
    log(f"rewrote:  service name  {SENTINEL_NAME} -> {args.service_name}   ({counts[SENTINEL_NAME]} files)")
    log(f"rewrote:  service id    {SENTINEL_ID} -> {args.service_id}   ({counts[SENTINEL_ID]} files)")

    if not args.no_tidy:
        r = run(["go", "mod", "tidy"], target)
        if r.returncode == 0:
            log("tidied:   go.mod / go.sum")
        else:
            log("warning:  go mod tidy failed (continuing — the frozen go.sum is already complete):")
            log(indent((r.stderr or r.stdout).strip()))
            if any(n in r.stderr for n in AUTH_NEEDLES):
                log("          hint: set GOPRIVATE=<host>/* and configure git credentials for the private module host.")

    if not args.no_git:
        r = run(["git", "init", "-q"], target)
        log("git:      initialized" if r.returncode == 0 else "warning:  git init failed (continuing)")

    if not args.no_build:
        r = run(["go", "build", "./..."], target)
        if r.returncode != 0:
            log("built:    FAILED")
            print(r.stderr, file=sys.stderr)
            if any(n in r.stderr for n in AUTH_NEEDLES):
                print("hint: set GOPRIVATE=<host>/* and configure git credentials for the private module host.", file=sys.stderr)
            sys.exit(1)
        log("built:    go build ./... OK")

    log(f"next:     cd {target} && go run ./cmd/api   then curl localhost:8080/health")
    log(f"done: scaffolded {args.service_name} at {target}")


if __name__ == "__main__":
    main()
