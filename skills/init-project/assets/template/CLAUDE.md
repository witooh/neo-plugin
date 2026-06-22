# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

This is a **freshly scaffolded service** — a hexagonal / DDD Go skeleton that builds and
serves `GET /health` with no business domains yet. Add the first domain with the **`neo`**
skill (`/neo`); it reads the steering below and follows the documented layer patterns.

## Steering is the source of truth — read it, don't re-derive

The authoritative engineering guide lives in **`.kiro/steering/`**. It carries the
architecture, per-layer skeletons, conventions, and gotchas verbatim — you should not need
to read source to learn a pattern. CLAUDE.md is a thin index over it: when steering and any
other doc disagree, **steering wins**.

Those files declare a Kiro `inclusion:` mode in their frontmatter. **Claude Code has no
native Kiro loader**, so apply the inclusion rules yourself, as follows.

### 1. Always read first — every session, before any work

| Guide | Why |
|---|---|
| `.kiro/steering/structure.md` | The primary, self-contained map: layout, the inward-only dependency rule, layers-at-a-glance, and the steering index. Start here. |

### 2. Read on file match — before you open / create / edit a file under the pattern

When the files you are about to touch match a glob below, read that guide **first** — it is
the contract for that layer (it carries the gotchas that unit tests miss). The empty skeleton
has not created every layer dir yet; the guide is still the contract for the dir you add.

| Read this guide | …before touching files matching |
|---|---|
| `domain.md`     | `internal/core/domain/**` |
| `usecase.md`    | `internal/core/usecase/**` |
| `handler.md`    | `internal/delivery/http/**` |
| `messaging.md`  | `internal/delivery/consumer/**`, `internal/adapters/eventbus/**`, `pkg/messaging/**` |
| `integration.md`  | `internal/core/domain/integration/**`, `internal/adapters/gateway/**`, `internal/adapters/repository/cache/**` |
| `repository.md` | `internal/adapters/repository/**`, `*.sql`, `sqlc.yaml` |
| `app.md`        | `cmd/api/**`, `config/**` |
| `testing.md`    | `**/*_test.go` |
| `e2e.md`        | `tests/**`, `mockoon/**` |
| `tooling.md`    | `Makefile`, `tools/**`, `.mockery.yaml`, `.golangci.yaml`, `Dockerfile`, `docker-compose*.yaml` |
| `bruno.md`      | `bruno/**` |

A change that spans layers loads several guides — read each before editing that layer.

### 3. Read on demand — manual reference

| Guide | Read when |
|---|---|
| `new-feature-checklist.md` | Adding a feature — it's the linear domain → … → wiring → tests procedure that chains the layer guides above. |
| `repo-instance.md` | You need this service's **real names** — its bounded contexts and driven ports. The per-layer guides are generic (placeholders only) and point here for concrete values. A freshly scaffolded service has none yet; the first `neo` domain run fills it in. |

## The one architectural rule

Imports point **inward only**: `delivery / adapters → usecase → domain`. An inner layer never
imports an outer one. Interfaces live where they are consumed (the inner layer) — each driven
port is **co-located inside the `internal/core/domain/<context>` package that owns it** (there
is no central `internal/port/`); implementations live in the outer `internal/adapters/`.
`cmd/api` is the **only** package that imports concrete adapters + usecases and wires them.
**Delivery packages and adapters never import each other; a usecase never imports another
usecase** — cross-capability needs go through a port (the one exception: `delivery/http/router`
imports handlers to wire routes — see `structure.md`). If a change needs an inner layer to
import an outer one, the design is wrong — revisit before coding.
Full rationale and the per-layer import table: `structure.md`.

## Commands

Generators and linters are pinned in per-tool modules under `tools/` (own `go.mod`),
invoked with `go tool -modfile=…` so they stay out of the service module.

### Run locally (no Docker)
```bash
go run ./cmd/api        # serves GET /health on :8080; Postgres/Redis are best-effort
make run-api            # same, with logs piped through jq
curl localhost:8080/health   # {"status":"ok"}
```

### Verification gates — all green before "done"
```bash
gofmt -l ./internal ./cmd ./config && goimports -w ./internal ./cmd ./config  # formatting
go build ./... && go vet ./internal/... ./cmd/... ./config/...
go tool -modfile=tools/golangci-lint/go.mod golangci-lint run ./internal/... ./cmd/... ./config/...   # pinned; must NOT grow the baseline issue count
make test-short                                              # unit + property tests (no Docker)
```
Lint is a **baseline**, not zero — a change may not *increase* the count; pre-existing
issues in untouched files are not your regression. (`golangci-lint` may also be on PATH;
the pinned `go tool` form is canonical and matches CI / the `pre-push` hook.)

### Tests
```bash
make test-short                 # unit + property (no Docker; -short)
make test                       # full Go suite incl. integration (needs Docker)
go test -run '^TestExec$' ./internal/core/usecase/<domain>/<operation>/...   # one Go test function
cd tests/e2e && npm test -- specs/<feature>.e2e.ts             # one e2e spec (jest)
```

### Codegen, stack, migrations
```bash
make gen                        # db-gen (sqlc) + mock-gen (mockery)
make compose-up / compose-down  # full local stack: service:8080, postgres, valkey, kafka
make create-migration NAME=x    # new migration under internal/adapters/repository/postgres/migrations
make migration-up               # apply  (⚠️ never run migration-down on UAT/Prod)
```

## Repo invariants

- **Never hand-edit generated code:** `internal/adapters/repository/postgres/sqlc/**`,
  `internal/mocks/**`, `pkg/mocks/**`. Change the source/query/config and regenerate.
- **Never create or alter tables manually** — schema changes go through golang-migrate.
- `vendor/` is gitignored; never commit it or secrets (`.env*`, keys, `credentials*`).
- Runtime config is a single committed YAML at `config/config.yaml`, loaded by the `config`
  package (`yaml.v3` + `mapstructure` decode — **not Viper** — then env-var overrides keyed by the
  upper-snake dotted path, e.g. `postgres.host` → `POSTGRES_HOST`). The committed values use the
  docker-network hostnames (`postgres`, `valkey`, `kafka`); the Dockerfile bakes the file into the
  image (docker-compose **builds** it, does not mount it). For a local `go run` the empty skeleton
  dials Postgres best-effort and serves `/health` regardless; override hosts to `localhost` via
  those env vars once you need the database.
- `bruno/` (runnable Bruno OpenCollection) is generated from the `docs/api/*.yaml` api-spec by
  the `open-collection` skill — regenerate rather than hand-edit (see `bruno.md`).
