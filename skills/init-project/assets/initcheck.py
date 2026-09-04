#!/usr/bin/env python3
"""L1 deterministic verify for an init-project scaffold.

Run against a freshly generated service. Proves it builds + vets, carries the
right identity, has zero business survivors, keeps the steering placeholders, and
serves /health via a best-effort (never-panicking) boot path.

Usage:
    initcheck.py --target-dir DIR --module-path PATH --service-name NAME --service-id ID [--schema SCHEMA]
Exit code 0 = all checks pass, 1 = a check failed, 2 = bad invocation.
"""
from __future__ import annotations

import argparse
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

SENTINELS = {"module": "example.com/neo/service", "name": "neo-service", "id": "NEOSVC", "schema": "neoschema"}
SKIP_DIRS = {".git", "__pycache__", "node_modules", "vendor"}

MANIFEST = [
    "cmd/api/main.go", "cmd/api/app.go", "cmd/api/http.go",
    "config/config.go", "config/config.yaml",
    "internal/delivery/http/router/router.go",
    "internal/delivery/http/middleware/middleware.go",
    "go.mod", "go.sum", "Dockerfile", "Makefile", "docker-compose.yaml",
    "scripts/check-coverage.sh",
    ".kiro/steering/INDEX.md", ".kiro/steering/structure.md",
    ".kiro/steering/repo-instance.md", "CLAUDE.md",
    "tools/sqlc/go.mod", "tools/mockery/go.mod", "tools/golang-migrate/go.mod",
    "tools/golangci-lint/go.mod", "tools/govulncheck/go.mod",
]

BUSINESS_ABSENT = [
    "internal/core/domain", "internal/core/usecase",
    "internal/adapters/gateway", "internal/adapters/eventbus",
    "internal/mocks", "pkg/messaging", "pkg/accountnumber",
]

RESULTS: list[tuple[bool, str, str]] = []


def check(ok: object, label: str, detail: str = "") -> None:
    RESULTS.append((bool(ok), label, detail))


def walk_texts(root: Path):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            path = Path(dirpath) / name
            try:
                yield path, path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue


def probe_health(t: Path) -> tuple[bool, str]:
    """Build cmd/api, boot it on an ephemeral port with no infrastructure, and
    confirm GET /health returns 200 with no panic — the runnable promise asserted
    behaviorally (best-effort boot), not by grepping the source for "panic"."""
    workdir = Path(tempfile.mkdtemp(prefix="initcheck-"))
    try:
        binpath = workdir / "svc"
        if subprocess.run(["go", "build", "-o", str(binpath), "./cmd/api"],
                          cwd=t, capture_output=True, text=True).returncode != 0:
            return False, "cmd/api failed to build"
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        logf = (workdir / "boot.log").open("w+")
        proc = subprocess.Popen([str(binpath)], cwd=t, stdout=logf, stderr=subprocess.STDOUT,
                                env={**os.environ, "SERVICE_PORT": str(port)})
        try:
            url = f"http://127.0.0.1:{port}/health"
            served = False
            for _ in range(40):
                if proc.poll() is not None:
                    break
                try:
                    with urllib.request.urlopen(url, timeout=1) as resp:
                        if resp.status == 200 and b"ok" in resp.read():
                            served = True
                            break
                except (urllib.error.URLError, OSError):
                    pass
                time.sleep(0.25)
            logf.seek(0)
            if "PANIC" in logf.read():
                return False, "boot log contains PANIC"
            if not served:
                return False, f"/health did not return 200 on :{port} (boot may have failed)"
            return True, f"served /health on :{port}, no panic"
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
            logf.close()
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--target-dir", required=True)
    ap.add_argument("--module-path", required=True)
    ap.add_argument("--service-name", required=True)
    ap.add_argument("--service-id", required=True)
    ap.add_argument("--schema", default=None,
                    help="postgres schema passed to scaffold.py (default: derived from --service-name)")
    args = ap.parse_args()
    if args.schema is None:
        args.schema = re.sub(r"-service$", "", args.service_name).replace("-", "_")

    t = Path(args.target_dir).expanduser().resolve()
    if not t.is_dir():
        print(f"error: target {t} not found", file=sys.stderr)
        sys.exit(2)
    texts = list(walk_texts(t))

    b = subprocess.run(["go", "build", "./..."], cwd=t, capture_output=True, text=True)
    check(b.returncode == 0, "go build ./...", b.stderr.strip()[:400])
    v = subprocess.run(["go", "vet", "./..."], cwd=t, capture_output=True, text=True)
    check(v.returncode == 0, "go vet ./...", v.stderr.strip()[:400])

    m = subprocess.run(["go", "list", "-m"], cwd=t, capture_output=True, text=True)
    check(m.stdout.strip() == args.module_path, "module identity", f"go list -m = {m.stdout.strip()!r}")

    mv = subprocess.run(["go", "mod", "verify"], cwd=t, capture_output=True, text=True)
    check(mv.returncode == 0, "go mod verify", (mv.stdout + mv.stderr).strip()[:200])

    user = {"module": args.module_path, "name": args.service_name, "id": args.service_id, "schema": args.schema}
    leftover = []
    for key, sent in SENTINELS.items():
        if user[key] == sent:
            continue  # the user chose the sentinel value itself — not a leftover
        hits = [str(p.relative_to(t)) for p, txt in texts if sent in txt]
        if hits:
            leftover.append(f"{sent} in {hits[:3]}")
    check(not leftover, "no leftover sentinels", "; ".join(leftover))

    struct = t / ".kiro/steering/structure.md"
    check(struct.is_file() and "{{MODULE_PATH}}" in struct.read_text(encoding="utf-8"),
          "steering placeholders preserved", "expected {{MODULE_PATH}} in structure.md")

    missing = [f for f in MANIFEST if not (t / f).exists()]
    check(not missing, "manifest present", f"missing: {missing}")

    present = [d for d in BUSINESS_ABSENT if (t / d).exists()]
    check(not present, "zero business survivors", f"present: {present}")

    outer = {("internal", "adapters"), ("internal", "delivery")}
    import_domain = re.compile(r'"[^"]*/internal/core/(?:domain|usecase)')
    dom = []
    for p, txt in texts:
        if p.suffix != ".go":
            continue
        parts = p.relative_to(t).parts
        if (parts[:2] in outer or parts[:1] == ("pkg",)) and import_domain.search(txt):
            dom.append(str(p.relative_to(t)))
    check(not dom, "no domain imports in outer layers", f"{dom[:3]}")

    router = t / "internal/delivery/http/router/router.go"
    rtext = router.read_text(encoding="utf-8") if router.is_file() else ""
    check('r.GET("/health"' in rtext and re.search(r"type Handlers struct\s*{\s*}", rtext) is not None,
          "/health route wired + empty Handlers", "")

    gomod = t / "go.mod"
    gtext = gomod.read_text(encoding="utf-8") if gomod.is_file() else ""
    check("gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2 v2.2.4" in gtext,
          "common-lib v2.2.4", "")

    mw = t / "internal/delivery/http/middleware/middleware.go"
    mwtext = mw.read_text(encoding="utf-8") if mw.is_file() else ""
    old_mw = [s for s in ("ServiceIdMiddleware", "ErrorLoggingMiddleware", "GetServiceId") if s in mwtext]
    has_new = all(s in mwtext for s in (
        "CorrelationIdMiddleware", "RequestIdMiddleware", "LoggingMiddleware",
        "GinErrorHandler", "Recovery",
    ))
    check(not old_mw and has_new, "common-lib v2.2.4 middleware chain",
          (f"removed symbols: {old_mw}; " if old_mw else "") +
          ("" if has_new else "missing RequestIdMiddleware/LoggingMiddleware"))

    cfg_yaml = t / "config/config.yaml"
    ytext = cfg_yaml.read_text(encoding="utf-8") if cfg_yaml.is_file() else ""
    check(f"service_name: {args.service_id}" in ytext,
          "logger.service_name matches service id", "")

    # Standard compose images (tooling.md — Docker Compose — standard images).
    compose = t / "docker-compose.yaml"
    ctext = compose.read_text(encoding="utf-8") if compose.is_file() else ""
    required_images = (
        "valkey/valkey-bundle:8-alpine",
        "postgres:17-alpine",
        "apache/kafka:4.1.0",
    )
    missing_img = [img for img in required_images if img not in ctext]
    banned = []
    for bad, why in (
        ("apache/kafka:3.7.0", "kafka must be 4.1.0"),
        ("valkey/valkey:8-alpine", "use valkey-bundle, not plain valkey"),
        ("public.ecr.aws/docker/library/postgres", "use Hub postgres:17-alpine"),
        ("public.ecr.aws/docker/library/redis", "use valkey-bundle, not ECR redis"),
    ):
        if bad in ctext:
            banned.append(why)
    check(not missing_img and not banned, "compose standard images",
          (f"missing {missing_img}; " if missing_img else "") + ("; ".join(banned) if banned else ""))

    ok, detail = probe_health(t)
    check(ok, "boots + serves /health without infra (no panic)", detail)

    passed = sum(1 for ok, _, _ in RESULTS if ok)
    for ok, label, detail in RESULTS:
        line = f"  [{'PASS' if ok else 'FAIL'}] {label}"
        if detail and not ok:
            line += f"  — {detail}"
        print(line)
    print(f"\ninitcheck: {passed}/{len(RESULTS)} checks passed")
    sys.exit(0 if passed == len(RESULTS) else 1)


if __name__ == "__main__":
    main()
