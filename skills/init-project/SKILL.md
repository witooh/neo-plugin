---
name: init-project
description: >
  Scaffold a brand-new Go hexagonal / DDD microservice from a bundled, frozen template — an
  empty-but-runnable account-service snapshot (clean layers, tooling, infra, `.kiro/` steering)
  with ZERO business domains. It builds and serves `GET /health` immediately, ready for
  `using-neo` (or Kiro) to add the first domain. Asks the service identity (Go
  module path, name, id, postgres schema, target dir), runs `scaffold.py` (copy +
  sentinel-substitute + go mod tidy + git init + build), then verifies (L1 `initcheck.py` + L2
  fresh-eyes). Trigger on:
  "init project", "/init-project", "scaffold a service", "new service from template",
  "bootstrap a Go service", "สร้าง project ใหม่", "สร้าง service ใหม่", "scaffold service ใหม่",
  "โครง service เปล่า", "ตั้งโปรเจกต์ใหม่ตาม account-service", "ทำ boilerplate", "new Go service
  skeleton". Needs Go >= 1.26 and GOPRIVATE access to the org `common-lib` the template needs.
  NOTE: only CREATES the empty skeleton — adding domains / AC / endpoints / tests is the `using-neo`
  skill.
compatibility:
  environment: claude-code
  tools:
    - Read
    - Bash
    - AskUserQuestion
    - Agent
---

# init-project

Scaffold a **new Go hexagonal / DDD microservice** from a bundled, frozen template — an
empty-but-runnable snapshot of the `account-service` architecture (clean layers + tooling + infra
wiring + `.kiro/` steering + `CLAUDE.md`) with **zero business domains**. The generated project
builds and serves `GET /health` immediately and is ready for `using-neo` (or Kiro) to add the first domain
with no setup.

> This skill **only creates the empty skeleton**. Authoring domains / AC / endpoints / tests is the
> **`using-neo`** skill — point the user there once the project exists.

## What it produces

A complete service skeleton under the target dir:

- **Layers** — `cmd/api` (composition root), `config`, `internal/delivery/http/{router,middleware}`
  (with `/health`), `internal/adapters/repository/{postgres,redis,cache}`,
  `pkg/{clock,idgen,cache/valkey,lib/kafka}`.
- **Tooling** — `Makefile`, `Dockerfile`, `docker-compose.yaml` (postgres + valkey + kafka),
  `.gitlab-ci.yml`, `.golangci.yaml`, `.mockery.yaml`, `sqlc.yaml`, pinned `tools/*` modules.
- **Agentic context** — `.kiro/steering/*` (architecture guides) + `.kiro/{skills,agents}` (Kiro neo
  port) + `CLAUDE.md`, so `using-neo` / Kiro can add a domain with no setup.
- `internal/core/{domain,usecase}`, gateways, and HTTP handlers are **created through using-neo**, not the
  skeleton — a fresh service legitimately has none.

The boot path is **best-effort**: `go run ./cmd/api` serves `/health` even with no Postgres / Redis /
Kafka running (it warns and continues — it never panics on missing infra).

## Tools

| Tool | Purpose |
|---|---|
| `AskUserQuestion` / chat | Gather the new service's identity (module path, name, id, postgres schema, target dir). |
| `Bash` | Run `assets/scaffold.py` (generate) + `assets/initcheck.py` (L1 verify). |
| `Agent` | Dispatch the L2 fresh-eyes verifier (`references/init-verifier.md`). |
| `Read` | Read the guide / verifier references. |

In the steps below, `<skill-dir>` is this skill's base directory (shown to you when the skill loads).

## Preconditions

- **Go ≥ 1.26** on PATH.
- **Private module access** for the org `common-lib` the template depends on — `GOPRIVATE` set for
  the module host (e.g. `gitlab.awesome-poc-th.com/*`) **and** working git credentials (SSH or
  `~/.netrc`). Without it `go mod tidy` / `go build` fail with an auth error and `scaffold.py` prints
  a hint; you can still create the project with `--no-build` and tell the user to build once they
  have access.

## Steps

1. **Gather identity.** Get five values from the user (ask for the module path first; derive
   sensible suggestions for the rest and confirm):
   - **module path** — the Go module path, e.g. `gitlab.awesome-poc-th.com/libero-engineering/core/<svc>`.
   - **service name** — kebab-case; default to the **last path segment** of the module.
   - **service id** — UPPER short id used in the error envelope / tracer (e.g. `NEOPAY`); suggest one
     from the name and confirm.
   - **postgres schema** — the schema this service owns inside the shared database (services share
     one database — `sit_core` — one schema per service, pinned via `search_path`); suggest the
     service name minus a trailing `-service` with dashes→underscores (e.g. `account-service` →
     `account`) and confirm.
   - **target dir** — where to create the project (suggest a sibling dir `../<service-name>`).

   Confirm all five before generating. Never invent the module path — it is org-specific; ask.

2. **Generate.** Run the bundled scaffold:
   ```bash
   python3 <skill-dir>/assets/scaffold.py \
     --target-dir <dir> --module-path <mod> --service-name <name> --service-id <id> --schema <schema>
   ```
   It copies the frozen template, substitutes the four sentinels, runs `go mod tidy`, `git init`, and
   `go build ./...`. If the build fails on private-module auth (the output prints a hint), re-run with
   `--no-build` and tell the user to run `go mod tidy && go build ./...` once they have access.

3. **L1 verify (deterministic).** Run the checker; **every check must PASS**:
   ```bash
   python3 <skill-dir>/assets/initcheck.py \
     --target-dir <dir> --module-path <mod> --service-name <name> --service-id <id> --schema <schema>
   ```
   It proves: build + vet, module identity, `go mod verify`, no leftover sentinels, steering
   placeholders preserved, manifest present, zero business survivors, no domain imports in outer
   layers, `/health` wired with an empty `Handlers`, and a best-effort (never-panicking) boot path. If
   any check FAILs, fix and re-run before reporting success.

4. **L2 verify (fresh eyes).** Dispatch a sub-agent — `Agent(subagent_type: "fresh-eyes")`,
   read-only by tool grant (harness without that type → `general-purpose`) — with the contract in
   `references/init-verifier.md`, passing the target dir. It independently
   confirms the project is a genuinely empty, runnable skeleton (serves `/health` without Docker, no
   business leak, steering intact). Relay any issue it surfaces.

5. **Report.** Summarize concisely: where the project is, that it builds + serves `/health`, and the
   next step — `cd <dir> && go run ./cmd/api` (curl `localhost:8080/health`), then use **`using-neo`** to
   add the first domain.

## Notes

- The bundled template is a **frozen snapshot** under `assets/template/` (sentinel module path
  `example.com/neo/service`, name `neo-service`, id `NEOSVC`, postgres schema `neoschema`). To
  refresh it when `account-service`'s conventions change, follow `references/init-project-guide.md`.
- Generic steering placeholders (`{{MODULE_PATH}}`, `<context>`, …) are intentionally left unresolved
  for `using-neo` to fill per-domain — only the four sentinels are substituted at generation time.
