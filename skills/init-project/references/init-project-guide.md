# init-project: guide & maintainer reference

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
| `NZQ` | `--error-prefix` (2-3 upper-case letters) | `internal/core/domain/errors.go`, `errorcatalog/{errors.json,embed_test.go}`, `README.md` (Appendix-E), `repo-instance.md`, code comments |

Generation (`scaffold.py`) is a **single-pass string substitution** of those five sentinels (never in
`go.sum`: a short sentinel can occur inside a base64 hash), then
`go mod tidy` + `git init` + `go build`. Generic steering placeholders (`{{MODULE_PATH}}`,
`{{SERVICE_NAME}}`, `<context>`, …) are **not** sentinels: they are left intact as placeholders for later
domain work.

## What's in the template (KEEP)

- **Layers**: `cmd/api` (gutted composition root, loads the error catalog first), `config` (loader +
  `logger/service/postgres/redis/kafka`), `internal/delivery/http/{router,middleware}` (the `/health`
  probe + middleware chain with `stdresp.ErrorHandler(catalog)`),
  `internal/adapters/repository/{postgres,redis,cache}` (low-level clients + `sqlc/db.go` +
  `transactor`/`utilities`/`dberror` + `migrations/000001_create_uuid_generate_v7`),
  `pkg/{clock,idgen,cache/valkey,lib/kafka}` (ambient (`idgen` = UUIDv7) + generic kafka).
- **Error codes**: `internal/core/domain/errors.go` (`<PREFIX>-8001` + `ErrorRefs()` +
  `NewDatabaseUnavailableError`, used by `dberror`) and `errorcatalog/` (embedded `errors.json` +
  tests). The only `internal/core/domain` content a fresh skeleton keeps.
  Error handling follows the payment-gateway standard in `.kiro/steering/errors.md`: domain
  constructors, usecase-owned mapping, port errors from gateways, and the three-field HTTP body.
- **Tooling**: `Makefile`, `Dockerfile`, `docker-compose.yaml` (postgres+valkey+kafka+mockoon
  placeholder), `.gitlab-ci.yml`
  (workflow auto-cancel + Go module cache; stages `prepare-mod` / `test` / `e2e-test` / `build` on
  `ec2-shell` for image push: no DinD *build*), `.golangci.yaml`,
  `.mockery.yaml`, `sqlc.yaml`, `.pre-commit-config.yaml`, `.gitignore`, the five pinned `tools/*` modules.
  `tests/e2e/` Jest + Playwright-request harness (`specs/health.e2e.ts` only) and
  `mockoon/placeholder.json` (empty env on `:8500`).
- **Agentic context**: `.kiro/steering/*` (generic guides + an empty-service `repo-instance.md`),
  `CLAUDE.md` (thin index over steering). **No** `.kiro/skills` or `.kiro/agents` in the template ,
  those install from the neo plugin / `kiro.sh`, not per service.
  `bruno/` + `mockoon/` shells (READMEs + env; collections/stubs regenerate per-domain).
  - **`CLAUDE.md` is gitignored by design** (`template/.gitignore`): this is a **Kiro-first**
    layout: `.kiro/` steering is the source of truth. The scaffold *creates* `CLAUDE.md` (so Claude
    Code users have it locally), but the generated project keeps it **untracked**, so teammates who
    use Kiro don't carry it. In the plugin repo the template's `CLAUDE.md` is committed with
    `git add -f` so it ships in the bundle. Do not "fix" the gitignore rule, it is intentional.

## What was removed (STRIP)

All business: `internal/core/usecase`, everything in `internal/core/domain` except `errors.go` (cut
to the dependency codes the skeleton raises) + `errorcatalog/` (cut to those rows),
`internal/adapters/{gateway,eventbus}`, business HTTP handlers/DTOs/routes, business sqlc
queries/migrations/seed (kept generic `sqlc/db.go` + the `uuid_generate_v7` migration), `internal/mocks`,
`pkg/{messaging,accountnumber,mocks}`, **business** e2e specs and mockoon upstream files (keep the
empty harness + `placeholder.json`), `docs/`, and the business `bruno` content.

## Boot model (why it runs with no Docker)

`cmd/api/app.go` starts the HTTP server first and dials Postgres **best-effort**: on a missing or
unreachable DB it logs a warning (within a 2s timeout) and continues, so `go run ./cmd/api` serves
`/health` standalone. A failed HTTP **bind** still panics (a genuine fatal error). When a real domain
is added later it tightens this as needed.

## Preconditions for generation

- **Go ≥ 1.26** on PATH.
- **Private module access** for the org `common-lib` the template imports
  (`gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2` **v2.3.0**): `GOPRIVATE` set for the
  host + git credentials. A warm module cache (having built `account-service` once) lets the build
  succeed offline. Without access, run `scaffold.py --no-build` and build later.

## Refreshing the snapshot (maintainer procedure)

When `account-service`'s conventions change, rebuild `assets/template/` in a scratch dir, then
`rsync` it back. Verify at every step: the frozen template MUST build and serve `/health` before it
is committed.

The architecture snapshot remains account-service-based, but **standard errors follow
payment-gateway's steering and code**. Preserve `errors.md`, `ErrorRefs()`, usecase-owned code
mapping and gateway port errors when refreshing; do not restore an older error convention from
the architecture source. Keep only the dependency codes the empty skeleton actually raises.

1. **Copy** a clean `account-service` into a scratch dir, excluding `.git/ vendor/ node_modules/
   __pycache__/ .DS_Store tests/e2e/{coverage,node_modules}/ *.out cover.profile` (keep `tools/`).
2. **Rename to sentinels** across the tree: the real Go module path → `example.com/neo/service`, the
   service/container name → `neo-service`, the service id (`NEOACCT`-style) → `NEOSVC`, the postgres
   schema (`account`-style, in `config.yaml` / `Makefile` / compose `postgres-init`) → `neoschema`,
   the error prefix (`FRD`-style, in `errors.json` / `errors.go` / README Appendix-E) → `NZQ`.
   `go build` to prove the rename didn't break.
3. **Gut the composition root first** (`cmd/api/app.go` → best-effort boot, `http.go` →
   `buildHandlers()` returns `&router.Handlers{}`, delete `adapters.go`/`consumer.go`), then the
   **router** (`router.go` → `/health` + empty `Handlers struct{}`, delete business route files), then
   **config** (`config.go` → `logger/service/postgres/redis/kafka` only; `config.yaml` to match).
4. **Strip** the now-orphaned business packages (domains, usecases, gateways, eventbus adapters,
   business repos + migrations + queries + business sqlc, mocks, `pkg/messaging`, `pkg/accountnumber`,
   business e2e specs and mockoon upstream files (keep `tests/e2e` harness + `health.e2e.ts` +
   `mockoon/placeholder.json`), `docs/`, business `bruno`). Keep `internal/core/domain/errors.go` +
   `errorcatalog/` cut to the codes the skeleton raises (`<PREFIX>-8001`), and keep migration
   `000001_create_uuid_generate_v7` (renumber it to `000001` if the source numbers it later).
5. **Genericize** the docs/config that name the business: `README.md`, `CLAUDE.md`,
   `repo-instance.md` (empty-service version), `docker-compose.yaml`, `Makefile`, `.gitlab-ci.yml`,
   `mockoon/README.md`, `bruno/{README.md,opencollection.yml,environments/*}`.
6. **Verify**: `gofmt -l` clean, `go build ./...` + `go vet ./...` = 0, `go test -short ./...` green,
   and `go run ./cmd/api` + `curl /health` = `{"status":"ok"}` with **no Docker** and **no panic**.
   Grep that no `internal/core/usecase` or `internal/core/domain/<sub>` import survives in
   `adapters`/`delivery`/`pkg` (the domain root, for error constructors, is allowed), and that
   no business term remains in service files. Do **not** reintroduce `.kiro/skills` or `.kiro/agents`
   into the freeze (plugin-owned, not project-owned).
7. **Freeze**: `rsync` the verified scratch tree into `assets/template/` (same excludes) and re-run the
   build + `/health` check **inside** the frozen location to prove the copy dropped nothing.
