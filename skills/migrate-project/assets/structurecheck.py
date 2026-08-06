#!/usr/bin/env python3
"""L1 deterministic structure-conformance check for a migrate-project target.

Run against a service that has been migrated to the account-service hexagonal / DDD
blueprint. Proves — statically, without the Go toolchain — that the layout, the
inward-only dependency rule, and the installed architecture contract (.golangci.yaml)
match the blueprint, and that no old-dialect layout residue remains.

This is a TRIPWIRE, not the full gate: `go build` / `go test` / `golangci-lint` (run by
the Verifier role) are the authoritative behavior + lint gates. structurecheck needs no
Go installed and no build — it reads the file tree + imports, so it works pre-build and
catches structural drift a successful build would still hide.

Usage:
    structurecheck.py --target-dir DIR
Exit code 0 = conforms (NOTEs allowed), 1 = DRIFT found, 2 = bad invocation.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

SKIP_DIRS = {".git", "__pycache__", "node_modules", "vendor", ".idea", ".vscode"}
SENTINEL_MODULE = "example.com/neo/service"

# Required blueprint dirs (relative to target root). Missing → DRIFT.
REQUIRED_DIRS = [
    "cmd/api",
    "internal/core/domain",
    "internal/core/usecase",
    "internal/delivery/http",
    "internal/adapters",
    "config",
]

# Old-dialect residue: (relative path, needs_code, message). Present → DRIFT.
# The blueprint never has any of these — their presence means a layer was not relocated.
RESIDUE_DIRS = [
    ("app",              True,  "composition root should be cmd/api/ (structure.md)"),
    ("internal/adapter", True,  "singular internal/adapter/ → internal/delivery/http/ + internal/adapters/"),
    ("external",         True,  "outbound adapters belong in internal/adapters/gateway/ (integration.md)"),
    ("database",         True,  "persistence belongs in internal/adapters/repository/postgres/ (repository.md)"),
    ("internal/domain",  True,  "flat internal/domain/ → internal/core/domain/{entity,service,repository,event}/ (domain.md)"),
]

# Framework packages banned inside core (the depguard contract — structure.md / domain.md).
CORE_FRAMEWORK_BANS = [
    "github.com/gin-gonic/gin",
    "net/http",
    "database/sql",
    "github.com/jackc/pgx",
    "github.com/redis/go-redis",
    "github.com/segmentio/kafka-go",
]

DRIFT: list[tuple[str, str]] = []   # (where, message)
NOTE: list[tuple[str, str]] = []


def drift(where: str, msg: str) -> None:
    DRIFT.append((where, msg))


def note(where: str, msg: str) -> None:
    NOTE.append((where, msg))


def pruned_walk(base: Path):
    """os.walk with SKIP_DIRS pruned in-place; yields (dirpath, dirs, files)."""
    for dirpath, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        yield dirpath, dirs, files


def has_files_with_ext(d: Path, exts: set[str]) -> bool:
    return any(Path(f).suffix in exts for _, _, files in pruned_walk(d) for f in files)


def read_module_path(root: Path) -> str | None:
    for line in (root / "go.mod").read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if line.startswith("module "):
            return line[len("module "):].strip()
    return None


def go_files_under(root: Path, rel: str):
    base = root / rel
    if not base.is_dir():
        return
    for dirpath, _, files in pruned_walk(base):
        for name in files:
            if name.endswith(".go") and not name.endswith("_test.go"):
                p = Path(dirpath) / name
                try:
                    yield p, p.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue


def check_layout(root: Path) -> None:
    for rel in REQUIRED_DIRS:
        if not (root / rel).is_dir():
            drift("(layout)", f"missing blueprint dir {rel}/")


def check_residue(root: Path) -> None:
    for rel, needs_code, msg in RESIDUE_DIRS:
        d = root / rel
        if not d.is_dir():
            continue
        if rel == "internal/domain":
            # flat domain = .go files DIRECTLY in internal/domain (not a context subdir) — a shallow
            # check, deliberately not folded into the recursive has_files_with_ext table (only case)
            if any(p.suffix == ".go" for p in d.iterdir() if p.is_file()):
                drift(f"{rel}/", msg)
        elif not needs_code or has_files_with_ext(d, {".go", ".sql"}):
            drift(f"{rel}/", msg)


def check_nested_layers(root: Path) -> None:
    """usecase/ outside core, repository/ outside adapters+domain, any ports/ dir → NOTE (heuristic)."""
    internal = root / "internal"
    if not internal.is_dir():
        return
    for dirpath, _, _ in pruned_walk(internal):
        rel = Path(dirpath).relative_to(root).as_posix()
        name = Path(dirpath).name
        if name == "usecase" and not rel.startswith("internal/core/usecase"):
            note(f"{rel}/", "usecase package outside internal/core/usecase/ (usecase.md)")
        if name == "repository" and not rel.startswith("internal/adapters/repository") \
                and not rel.startswith("internal/core/domain/repository"):
            note(f"{rel}/", "repository package outside internal/adapters/repository/ or internal/core/domain/repository/ (repository.md)")
        if name in ("ports", "port"):
            note(f"{rel}/", "driven ports live in internal/core/domain/repository/ + event/, not a ports/ dir (domain.md)")


def check_group_case(root: Path) -> None:
    """Group dirs directly under core/usecase (bounded-context names) and core/domain (the fixed
    technical-layer names entity/service/repository/event/integration) must be lowercase — never
    Account/Entity. DRIFT (high-confidence structural fact)."""
    for layer in ("internal/core/usecase", "internal/core/domain"):
        base = root / layer
        if not base.is_dir():
            continue
        for p in sorted(base.iterdir()):
            if p.is_dir() and p.name not in SKIP_DIRS and p.name != p.name.lower():
                drift(f"{layer}/{p.name}/",
                      f"group dir must be lowercase (a <context> package under usecase / a layer "
                      f"name under domain) — rename to {p.name.lower()}/ (structure.md)")


def check_dependency_rule(root: Path, module: str | None) -> None:
    if not module:
        note("(imports)", "no module path in go.mod — dependency-rule check skipped")
        return
    def has_import(txt: str, path: str) -> bool:
        return f'"{path}' in txt  # matches "<path>" and "<path>/sub"

    def has_framework(txt: str, fw: str) -> bool:
        return f'"{fw}"' in txt or f'"{fw}/' in txt

    # Each core layer may not import the layers strictly outward of it (structure.md).
    layers = [
        ("internal/core/domain",
         [f"{module}/internal/core/usecase", f"{module}/internal/adapters", f"{module}/internal/delivery"],
         "domain imports outward ({imp}…) — imports point inward only (structure.md)"),
        ("internal/core/usecase",
         [f"{module}/internal/adapters", f"{module}/internal/delivery"],
         "usecase imports outward ({imp}…) — depend on the domain port instead (structure.md)"),
    ]
    for layer, outward, tail in layers:
        owner = layer.rsplit("/", 1)[1]
        for p, txt in go_files_under(root, layer):
            rel = p.relative_to(root).as_posix()
            for imp in outward:
                if has_import(txt, imp):
                    drift(rel, tail.format(imp=imp))
            for fw in CORE_FRAMEWORK_BANS:
                if has_framework(txt, fw):
                    drift(rel, f"{owner} imports framework {fw} — core stays framework-free (depguard)")


def check_ambient_calls(root: Path) -> None:
    """forbidigo contract: no time.Now()/uuid.New() in core — NOTE (golangci is authoritative)."""
    pat = re.compile(r"\b(time\.Now|uuid\.New(?:String)?)\s*\(")
    for layer in ("internal/core/domain", "internal/core/usecase"):
        for p, txt in go_files_under(root, layer):
            m = pat.search(txt)
            if m:
                note(p.relative_to(root).as_posix(),
                     f"ambient call {m.group(1)}() in core — inject clock.Clock/idgen.Generator "
                     f"(forbidigo; run golangci-lint to confirm)")


def check_contract(root: Path, module: str | None) -> None:
    gl = root / ".golangci.yaml"
    if not gl.is_file():
        gl = root / ".golangci.yml"
    if not gl.is_file():
        drift("(contract)", ".golangci.yaml not installed — the depguard/forbidigo contract is the "
                            "machine-checkable conformance gate (install per blueprint)")
    else:
        text = gl.read_text(encoding="utf-8", errors="ignore")
        if SENTINEL_MODULE in text:
            drift(gl.name, f"sentinel module {SENTINEL_MODULE} not substituted to the target module path")
        elif module and module not in text:
            note(gl.name, f"depguard does not reference the target module {module} — confirm the layer rules are wired")
    if not (root / ".kiro/steering/INDEX.md").is_file():
        drift("(contract)", ".kiro/steering/INDEX.md not installed — steering guides are not discoverable")
    if not (root / ".kiro/steering/structure.md").is_file():
        note("(contract)", ".kiro/steering/ not installed — blueprint convention guides (install per blueprint)")
    if not (root / "CLAUDE.md").is_file():
        note("(contract)", "CLAUDE.md not installed — steering index (install per blueprint)")


def check_compose_images(root: Path) -> None:
    """Flag non-standard compose image tags (tooling.md) as NOTE.

    DRIFT is reserved for high-confidence structural facts (layout/imports/
    golangci contract) — see migrate-project CLAUDE.md. Compose tags on
    brownfield targets (incl. account-service still on kafka 3.7.0) must not
    fail structurecheck's CONFORMS regression guard. Hard fail lives in
    initcheck (greenfield) + migrate-verifier L2 (slice-scoped)."""
    files = sorted(
        p for p in root.iterdir()
        if p.is_file() and p.name.startswith("docker-compose")
        and p.suffix in {".yaml", ".yml"}
    )
    if not files:
        return
    banned = [
        ("valkey/valkey:8-alpine", "use valkey/valkey-bundle:8-alpine (tooling.md)"),
        ("public.ecr.aws/docker/library/postgres", "use postgres:17-alpine Hub path (tooling.md)"),
        ("public.ecr.aws/docker/library/redis", "use valkey/valkey-bundle:8-alpine (tooling.md)"),
    ]
    for f in files:
        text = f.read_text(encoding="utf-8", errors="ignore")
        rel = f.name
        # Independent checks — never gate one ban behind another (multi-bad compose
        # must surface every hit).
        if "apache/kafka:" in text and "apache/kafka:4.1.0" not in text:
            note(rel, "kafka image must be apache/kafka:4.1.0 (tooling.md)")
        for bad, msg in banned:
            if bad in text:
                note(rel, msg)


def main() -> None:
    ap = argparse.ArgumentParser(description="Structure-conformance tripwire for a migrate-project target.")
    ap.add_argument("--target-dir", required=True)
    args = ap.parse_args()

    root = Path(args.target_dir).expanduser().resolve()
    if not root.is_dir():
        print(f"error: target {root} not found", file=sys.stderr)
        sys.exit(2)
    if not (root / "go.mod").is_file():
        print(f"error: {root} has no go.mod — not a Go module (greenfield? use the init-project skill)", file=sys.stderr)
        sys.exit(2)

    module = read_module_path(root)
    check_layout(root)
    check_residue(root)
    check_nested_layers(root)
    check_group_case(root)
    check_dependency_rule(root, module)
    check_ambient_calls(root)
    check_contract(root, module)
    check_compose_images(root)

    by_loc: dict[str, dict[str, list[str]]] = {}
    for where, msg in DRIFT:
        by_loc.setdefault(where, {"DRIFT": [], "NOTE": []})["DRIFT"].append(msg)
    for where, msg in NOTE:
        by_loc.setdefault(where, {"DRIFT": [], "NOTE": []})["NOTE"].append(msg)

    for where in sorted(by_loc, key=lambda k: (not k.startswith("("), k)):
        rec = by_loc[where]
        ds, nts = rec["DRIFT"], rec["NOTE"]
        status = f"{len(ds)} DRIFT" if ds else "OK"
        extra = f" / {len(nts)} note" if nts else ""
        print(f"{'✗' if ds else '✓'} {where:48} {status}{extra}")
        for d in ds:
            print(f"    DRIFT  {d}")
        for n in nts:
            print(f"    NOTE   {n}")

    verdict = "CONFORMS" if not DRIFT else "DRIFT"
    print(f"\nstructurecheck: {len(DRIFT)} drift, {len(NOTE)} note  ({verdict})")
    sys.exit(1 if DRIFT else 0)


if __name__ == "__main__":
    main()
