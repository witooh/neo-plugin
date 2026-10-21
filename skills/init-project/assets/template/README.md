# neo-service

A freshly scaffolded Go microservice on a **hexagonal / DDD** architecture: a pure `domain`
core (encapsulated aggregates, domain services, typed errors, and the centralized driven ports, `repository` + `event`),
an application `usecase` layer (one package per operation), and `delivery` / `adapters` layers
for every inbound (HTTP, Kafka consumer) and outbound (Postgres, Redis, Kafka) integration.
Dependencies point **inward only**: `delivery / adapters → usecase → domain`.

It builds and serves `GET /health` out of the box with **no business domains yet**. Grow it
using `.kiro/steering/` (start with `structure.md` / `new-feature-checklist.md`) and
follow the documented layer patterns.

## Tech Stack

- Go 1.26 / Gin HTTP framework
- PostgreSQL (`jackc/pgx/v5`, sqlc) + Valkey/Redis (`redis/go-redis/v9`)
- Kafka (`segmentio/kafka-go`): generic producer/consumer primitives in `pkg/lib/kafka`
- mockery (mocks) + golang-migrate (migrations): pinned tool modules under `tools/`
- Docker / Docker Compose / GitLab CI

## Project Structure

```
neo-service/
├── cmd/api/                         # COMPOSITION ROOT (package main): entry + wiring
│   ├── main.go                      #   thin entry point → MustLoad + Run(ctx, cfg)
│   └── app.go http.go               #   start server + best-effort infra + handler wiring
├── config/                          # typed config + loader, beside config.yaml
├── internal/
│   ├── core/
│   │   ├── domain/                  # THE MODEL (per layer: entity/ service/ repository/ event/) , 
│   │   │   │                        #   aggregates, domain services, typed errors + centralized ports (neo adds these)
│   │   │   ├── errors.go            #   NZQ error codes (common-lib stderr): only NZQ-8001 so far
│   │   │   └── errorcatalog/        #   errors.json (Appendix-E) embedded + loaded at startup
│   │   └── usecase/                 # ONE operation per package → usecase.go + exec.go (neo adds)
│   ├── delivery/
│   │   └── http/{router,middleware} # inbound HTTP (gin): /health + the middleware chain
│   └── adapters/
│       └── repository/{postgres,redis,cache}   # outbound persistence + cache (low-level clients)
│                                    #   postgres/migrations/000001: uuid_generate_v7() for DB-generated ids
├── pkg/                             # shared low-level libs (no domain logic)
│   ├── cache/valkey/                #   Valkey client
│   ├── clock/  idgen/               #   ambient capabilities (clock, id) + *test fakes
│   └── lib/kafka/                   #   generic Kafka producer/consumer primitives
├── .kiro/steering/                  # the authoritative engineering guide (read structure.md first)
├── bruno/  mockoon/                 # API-collection shell + empty Mockoon placeholder
├── tests/e2e/                       # Jest + Playwright-request harness (`GET /health`)
├── tools/                           # pinned tool modules (sqlc, mockery, golang-migrate, …)
├── Makefile  Dockerfile  docker-compose.yaml
├── config/config.yaml               # single committed config (env vars override per env)
└── go.mod
```

`internal/core/usecase`, `internal/adapters/gateway`, the HTTP handlers and everything in
`internal/core/domain` beyond `errors.go` + `errorcatalog/` are added later as domains: a fresh
skeleton has none. The contract for
each layer lives in `.kiro/steering/` (start with `structure.md`).

## Getting Started

### Prerequisites
- Go 1.26+
- Private Go module access for `gitlab.awesome-poc-th.com` (`GOPRIVATE` + git credentials), the
  service depends on the org `common-lib`.
- Docker & Docker Compose (only for the full stack)
- `jq` (for pretty-printing log output)

### Run locally (no Docker)
```bash
go run ./cmd/api                       # or: make run-api
curl -sf http://localhost:8080/health  # {"status":"ok"}
```
Postgres/Redis are dialed **best-effort**: the skeleton serves `/health` even with nothing else running.

### Full stack in Docker
```bash
make compose-up        # build image + start postgres/valkey/kafka + the service (:8080)
make compose-down      # tear down (removes volumes)
```

## Make commands

| Command | Description |
|---|---|
| `make run-api` | Run the API server (logs piped through `jq`) |
| `make compose-up` / `make compose-down` | Start / stop the full local stack |
| `make gen` | Regenerate code (sqlc + mocks) |
| `make test-short` | Unit + property tests (no Docker) |
| `make test` | Full Go suite incl. integration (needs Docker) |
| `make create-migration NAME=xxx` | Create a new migration |
| `make migration-up` | Apply pending migrations (⚠️ never `migration-down` on UAT/Prod) |

## Adding a feature

This service is meant to be grown using `.kiro/steering/` (start with `structure.md` /
`new-feature-checklist.md`). Don't hand-improvise structure: if a pattern isn't in the
steering, surface it and fold the decision back into the guide (see `structure.md`).

## Error codes (Appendix-E)

Every HTTP error answers the common-lib body `{ "responseCode", "errorCode", "errorMessage" }`
(common-lib v2.3.0 error code standard). Callers branch on `responseCode` and log `errorCode`.
`errorMessage` is for logs and support, not for customers. Prefix: **`NZQ`**. The catalog is
`internal/core/domain/errorcatalog/errors.json`, loaded at startup (an invalid catalog stops the
service). Startup checks every `domain.ErrorRefs()` entry. The HTTP status follows the response
code; the single error contract is `.kiro/steering/errors.md` (payment-gateway standard).

| Error Code | Response Code | HTTP Status | Message | Condition | Raised By |
|---|---|---|---|---|---|
| NZQ-1001 | 001 | 400 | Mandatory field missing | A required field is absent, null or empty (reserved) | All |
| NZQ-1002 | 001 | 400 | Invalid field format | Malformed JSON, unknown field, wrong JSON kind or value (reserved) | All |
| NZQ-8001 | 005 | 503 | Database unavailable | Postgres is unreachable or a query / transaction failed | All |
| NZQ-9001 | 999 | 500 | Unexpected system error | Any error with no specific code, including a panic (reserved) | All |

## Configuration

A single committed `config/config.yaml` holds local/compose defaults. Every value can be
overridden by an environment variable named after its dotted path in upper snake case
(`.` → `_`): e.g. `postgres.host` → `POSTGRES_HOST`. SIT/production inject the full config as
environment variables from the secret manager, so no per-environment YAML file is needed.
