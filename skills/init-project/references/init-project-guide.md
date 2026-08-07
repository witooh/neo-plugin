# init-project — guide & maintainer reference

## What the template is

`assets/template/` is a **frozen, empty-but-runnable snapshot** of the `account-service`
hexagonal / DDD architecture. It is a real, compilable Go service under a **sentinel identity** so
it is CI-verifiable as-is:

| Sentinel | Replaced at generation with | Appears in |
|---|---|---|
| `example.com/neo/service` | `--module-path` | every `.go` import, `go.mod`, `sqlc.yaml`, `.golangci.yaml`, `.mockery.yaml` |
| `neo-service` | `--service-name` | `docker-compose.yaml`, `.gitlab-ci.yml`, `Makefile`, `Dockerfile`, READMEs |
| `NEOSVC` | `--service-id` | `config/config.yaml` (`service_id`) |
| `neoschema` | `--schema` (default: service name minus `-service`, dashes→underscores) | `config/config.yaml` (`schema`), `Makefile` (`PG_SCHEMA`), `docker-compose.yaml` (`postgres-init`) |

Generation (`scaffold.py`) is a **single-pass string substitution** of those four sentinels, then
`go mod tidy` + `git init` + `go build`. Generic steering placeholders (`{{MODULE_PATH}}`,
`{{SERVICE_NAME}}`, `<context>`, …) are **not** sentinels — they are left intact for `using-neo` to fill
per-domain.

## What's in the template (KEEP)

- **Layers** — `cmd/api` (gutted composition root), `config` (loader + `logger/service/postgres/redis/kafka`),
  `internal/delivery/http/{router,middleware}` (the `/health` probe + middleware chain),
  `internal/adapters/repository/{postgres,redis,cache}` (low-level clients + `sqlc/db.go` +
  `transactor`/`utilities`/`dberror`), `pkg/{clock,idgen,cache/valkey,lib/kafka}` (ambient + generic kafka).
- **Tooling** — `Makefile`, `Dockerfile`, `docker-compose.yaml` (postgres+valkey+kafka), `.gitlab-ci.yml`
  (prepare-mod / test / build), `.golangci.yaml`, `.mockery.yaml`, `sqlc.yaml`, `.pre-commit-config.yaml`,
  `.gitignore`, the five pinned `tools/*` modules.
- **Agentic context** — `.kiro/steering/*` (generic guides + an empty-service `repo-instance.md`),
  `CLAUDE.md` (thin index over steering). **No** `.kiro/skills` or `.kiro/agents` in the template —
  those install from the neo plugin / `kiro.sh`, not per service.
  `bruno/` + `mockoon/` shells (READMEs + env; collections/stubs regenerate per-domain).
  - **`CLAUDE.md` is gitignored by design** (`template/.gitignore`): this is a **Kiro-first**
    layout — `.kiro/` steering is the source of truth. The scaffold *creates* `CLAUDE.md` (so Claude
    Code users have it locally), but the generated project keeps it **untracked**, so teammates who
    use Kiro don't carry it. In the plugin repo the template's `CLAUDE.md` is committed with
    `git add -f` so it ships in the bundle. Do not "fix" the gitignore rule — it is intentional.

## What was removed (STRIP)

All business: `internal/core/{domain,usecase}`, `internal/adapters/{gateway,eventbus}`, business HTTP
handlers/DTOs/routes, business sqlc queries/migrations/seed (kept generic `sqlc/db.go`), `internal/mocks`,
`pkg/{messaging,accountnumber,mocks}`, the whole `tests/` e2e harness, `docs/`, and the business
`bruno`/`mockoon` content.

## Boot model (why it runs with no Docker)

`cmd/api/app.go` starts the HTTP server first and dials Postgres **best-effort** — on a missing or
unreachable DB it logs a warning (within a 2s timeout) and continues, so `go run ./cmd/api` serves
`/health` standalone. A failed HTTP **bind** still panics (a genuine fatal error). When `using-neo` adds a
real domain it tightens this as needed.

## Preconditions for generation

- **Go ≥ 1.26** on PATH.
- **Private module access** for the org `common-lib` the template imports
  (`gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2`): `GOPRIVATE` set for the
  host + git credentials. A warm module cache (having built `account-service` once) lets the build
  succeed offline. Without access, run `scaffold.py --no-build` and build later.

## Refreshing the snapshot (maintainer procedure)

When `account-service`'s conventions change, rebuild `assets/template/` in a scratch dir, then
`rsync` it back. Verify at every step — the frozen template MUST build and serve `/health` before it
is committed.

1. **Copy** a clean `account-service` into a scratch dir, excluding `.git/ vendor/ node_modules/
   __pycache__/ .DS_Store tests/e2e/{coverage,node_modules}/ *.out cover.profile` (keep `tools/`).
2. **Rename to sentinels** across the tree: the real Go module path → `example.com/neo/service`, the
   service/container name → `neo-service`, the service id (`NEOACCT`-style) → `NEOSVC`, the postgres
   schema (`account`-style, in `config.yaml` / `Makefile` / compose `postgres-init`) → `neoschema`.
   `go build` to prove the rename didn't break.
3. **Gut the composition root first** (`cmd/api/app.go` → best-effort boot, `http.go` →
   `buildHandlers()` returns `&router.Handlers{}`, delete `adapters.go`/`consumer.go`), then the
   **router** (`router.go` → `/health` + empty `Handlers struct{}`, delete business route files), then
   **config** (`config.go` → `logger/service/postgres/redis/kafka` only; `config.yaml` to match).
4. **Strip** the now-orphaned business packages (domains, usecases, gateways, eventbus adapters,
   business repos + migrations + queries + business sqlc, mocks, `pkg/messaging`, `pkg/accountnumber`,
   `tests/`, `docs/`, business `bruno`/`mockoon`).
5. **Genericize** the docs/config that name the business: `README.md`, `CLAUDE.md`,
   `repo-instance.md` (empty-service version), `docker-compose.yaml`, `Makefile`, `.gitlab-ci.yml`,
   `mockoon/README.md`, `bruno/{README.md,opencollection.yml,environments/*}`.
6. **Verify**: `gofmt -l` clean, `go build ./...` + `go vet ./...` = 0, `go test -short ./...` green,
   and `go run ./cmd/api` + `curl /health` = `{"status":"ok"}` with **no Docker** and **no panic**.
   Grep that no `internal/core/domain|usecase` import survives in `adapters`/`delivery`/`pkg`, and that
   no business term remains in service files. Do **not** reintroduce `.kiro/skills` or `.kiro/agents`
   into the freeze (plugin-owned, not project-owned).
7. **Freeze**: `rsync` the verified scratch tree into `assets/template/` (same excludes) and re-run the
   build + `/health` check **inside** the frozen location to prove the copy dropped nothing.
