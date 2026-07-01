---
inclusion: fileMatch
fileMatchPattern: "Makefile,tools/**,.mockery.yaml,.golangci.yaml,.golangci.yml,Dockerfile,docker-compose*.yaml"
---

# Tooling

The `Makefile` is the task entry point; generators and linters are pinned via a separate
tool module so they don't pollute the service's `go.mod`.

## Makefile — canonical targets

| Target | Does |
|---|---|
| `make test` | Go unit + property tests |
| `make compose-up` | `docker compose up -d --build` — **rebuilds the image** |
| `make test-e2e` | run the black-box e2e suite against the running stack |
| `make mock-gen` | regenerate mockery doubles into `internal/mocks` |
| `make db-gen` | regenerate sqlc code from `queries/*.sql` |
| `make gen` | `db-gen` + `mock-gen` |
| `make create-migration NAME=…` / `make migration-up` | create / apply a migration |

(There is no `make lint`/`make sqlc` target — lint runs as the gate `golangci-lint run` below; sqlc generation is `make db-gen`.)

Compose `make compose-up` **then** `make test-e2e` after any code change (the e2e target
may skip rebuild if the stack is already healthy → stale image). See `e2e.md`.

## Verification gates (run before "done")

```
gofmt -l ./internal && goimports -w ./internal   # formatting (goimports at $(go env GOPATH)/bin)
go build ./... && go vet ./internal/...
golangci-lint run ./internal/...                  # must equal the baseline issue count, not grow it
make test                                          # all green
```

Treat the current lint issue count as a **baseline**; a change may not increase it.
Pre-existing issues in untouched files are not your regression.

### depguard — the import boundaries, mechanically enforced

`depguard` (enabled in `.golangci.yaml`) is the **machine form of the `structure.md`
dependency rule + framework-independence**: a cross-layer import — or a transport/persistence/infra
import inside `domain`/`usecase` — fails `golangci-lint` (and CI), not just review. The rules deny, per layer:

| files | may NOT import |
|---|---|
| `internal/core/domain/**` | `core/usecase` · `delivery` · `adapters` · framework libs (`gin`/`net/http`/`database/sql`/`pgx`/`go-redis`/`kafka-go`) |
| `internal/core/usecase/**` | `delivery` · `adapters` · the same framework libs |
| `internal/adapters/**` | `core/usecase` · `delivery` |
| `internal/delivery/**` | `adapters` (whole — `gateway`/`repository`/`eventbus`; a shared wire contract lives in `pkg/messaging`, not `adapters/`) |

When you add a layer or a sanctioned exception, update **both** these rules in `.golangci.yaml`
**and** the dependency rule in `structure.md` — keep them in lockstep.

## `.mockery.yaml`

Generates testify-style mocks. Each entry maps a **source package root** (interfaces to mock)
to an **output dir** under `internal/mocks` (or `pkg/mocks`) — `recursive: true` walks the
subtree, and the output dir is computed from the source's relative path so the mock tree
mirrors the source tree. When you move/rename a mocked package, update its key/output
expression here and regenerate.

```yaml
template: testify
recursive: true
packages:
  {{MODULE_PATH}}/pkg:
    config: { all: true, dir: pkg/mocks/{{ trimPrefix "pkg" .InterfaceDirRelative }} }
  {{MODULE_PATH}}/internal/adapters/gateway:
    config: { all: true, dir: internal/mocks/gateway/{{.SrcPackageName}} }
  {{MODULE_PATH}}/internal/adapters/eventbus:
    config: { all: true, dir: internal/mocks{{ trimPrefix "internal/adapters" .InterfaceDirRelative }} }
  {{MODULE_PATH}}/internal/core/domain:
    config: { all: true, dir: internal/mocks/domain{{ trimPrefix "internal/core/domain" .InterfaceDirRelative }} }
```

This generates: `internal/mocks/domain/<context>/...` (the co-located domain ports —
repository, cache, event-publisher, the `integration/<sys>` gateways),
`internal/mocks/gateway/...`, `internal/mocks/eventbus/...`, and `pkg/mocks/...`. Mock the
**seams** — the domain-owned ports and the select adapter / `pkg` interfaces listed under
`packages:`. Not domain logic.

## tools module

Generators (mockery, sqlc) are pinned in a dedicated `tools/` module (its own `go.mod`)
and invoked with `-modfile`. This keeps tool dependencies out of the service module. If
`make mock-gen` fails on a vendored-dependency mismatch, temporarily move `vendor/` aside,
generate, then restore and re-run `go mod vendor`.

## `.golangci.yaml`

golangci-lint v2, **opt-in linter set** (`bodyclose`, `contextcheck`, `errname`,
`exhaustive`, `nilerr`, `nilnesserr`, `nilnil`, `unused`). `unused` **gates dead code** —
an unreferenced func/type/const/test-helper fails the lint, so dead code can't accumulate
silently. No `revive`/`stylecheck`/`staticcheck` naming rules — which is why snake_case
usecase package names lint clean. Keep the set small and meaningful; don't add a linter
that floods the baseline.

## Dockerfile — two-stage

```dockerfile
FROM golang:<ver> AS build
# ... go mod download (use vendor if committed... but vendor/ is gitignored here) ; CGO off; build static binary
FROM alpine:latest
COPY --from=build /app/bin/service /service
ENTRYPOINT ["/service"]
```

Small final image (alpine), static binary. `docker-compose*.yaml`
wires the service + its infra (DB, cache, kafka, upstream stubs) for local + e2e.

## Don'ts

- ✗ Committing `vendor/` (gitignored) or secrets (`.env*`, keys, `credentials*`).
- ✗ Hand-editing generated code (`internal/mocks/**`, `repository/postgres/sqlc/**`).
- ✗ Adding a noisy linter that inflates the baseline.
