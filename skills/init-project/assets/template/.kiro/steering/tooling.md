---
inclusion: fileMatch
fileMatchPattern: "Makefile,tools/**,scripts/**,.mockery.yaml,.golangci.yaml,.golangci.yml,Dockerfile,docker-compose*.yaml,.gitlab-ci.yml"
---

# Tooling

The `Makefile` is the task entry point; generators and linters are pinned via a separate
tool module so they don't pollute the service's `go.mod`.

## Makefile — canonical targets

| Target | Does |
|---|---|
| `make test` | Go unit + property tests |
| `make test-cover` | the same tests with coverage, then **fails** below `COVERAGE_THRESHOLD` (default 80) |
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
make test-cover                                    # coverage gate — exits non-zero below the threshold
```

`make test-cover` is the coverage gate, not a report: `scripts/check-coverage.sh` drops
generated code (`mocks`, `sqlc`, the `*test` stub packages) from the denominator so the
percentage reflects hand-written production Go, then exits non-zero below
`COVERAGE_THRESHOLD`. CI runs the same script, so the local and pipeline numbers agree.
When coverage is short, add tests — widening the exclusion list manufactures the threshold
and is a review finding.

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

This generates: `internal/mocks/domain/{repository,event}/...` (the centralized domain ports —
repository, cache, event-publisher, plus the `integration/<sys>` gateways),
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

## GitLab CI — `.gitlab-ci.yml`

Empty-skeleton pipeline (no `tests/e2e` yet). Align with the org core services that already
tuned CI for speed — **not** the older DinD build path.

| Piece | Required shape |
|---|---|
| `workflow` | `auto_cancel.on_new_commit: interruptible`; skip branch pipelines when an MR is open (`$CI_COMMIT_BRANCH && $CI_OPEN_MERGE_REQUESTS` → `when: never`) |
| Go cache | top-level `cache.paths`: `.go/pkg/mod/`, `.go/bin/` with `GOPATH: ${CI_PROJECT_DIR}/.go` |
| `prepare-mod` | `go mod download` + `go mod vendor`; `vendor/` artifact (1 day); `CI_JOB_TOKEN` rewrite for the private module host |
| `test` | `needs: [prepare-mod]`; `go test -short -mod=vendor` + `scripts/check-coverage.sh` (threshold 80) |
| `build` | tag **`ec2-shell`** (host docker socket — **not** `linux` + DinD); job-local `DOCKER_CONFIG` + ECR `credHelpers` / `ecr-login`; assume-role to n005; `docker build` + `docker push` of `${ECR_URI}/${ECR_REPO_NAME}:${IMAGE_TAG}`; `interruptible: false` |
| stages (skeleton) | `prepare-mod` → `test` → `build` |

**When `using-neo` adds HTTP e2e**, insert stage `e2e-test` (between `test` and `build`) modeled on
payment-gateway: DinD image + `docker compose up`, migrate on the compose network, Node test
container with service-specific `API_BASE_URL` / `DB_SCHEMA`. Do not copy e2e into a service that
has no `tests/e2e` yet.

### Don'ts

- ✗ `build` on `tags: ["linux"]` with `docker:*-dind` + manual `docker login` / `aws ecr get-login-password` — prefer `ec2-shell` + credential helper (faster, shared runner socket).
- ✗ Creating the ECR repository from CI (`aws ecr create-repository`) — repo is provisioned out-of-band.
- ✗ Omitting `workflow.auto_cancel` / dual branch+MR pipelines — wastes runners on superseded commits.

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

## Docker Compose — standard images

Local + e2e compose uses these pinned images. Do not invent tags or Hub/ECR
mirrors; align every service's `docker-compose*.yaml` (and dockertest tags) to
this list.

### Required (every service scaffold)

| Service | Image |
|---|---|
| cache | `valkey/valkey-bundle:8-alpine` |
| postgres / postgres-init | `postgres:17-alpine` |
| kafka | `apache/kafka:4.1.0` |

### When the feature needs it

| Service | Image | When |
|---|---|---|
| mockoon | `mockoon/cli:9.7.0` | first external HTTP upstream stub |
| kafka-ui | `ghcr.io/kafbat/kafka-ui:latest` | local topic browsing (optional) |
| migrate | `migrate/migrate:v4.18.1` | one-shot migration runner in compose (optional; Makefile uses `tools/golang-migrate`) |
| localstack | `localstack/localstack:3.4` | AWS API mock |

### Don'ts

- ✗ `apache/kafka:3.7.0` (or any non-4.1.0 tag) — standard is `4.1.0`.
- ✗ `valkey/valkey:8-alpine` — use **`valkey-bundle`**, not plain valkey.
- ✗ `public.ecr.aws/docker/library/{postgres,redis}:…` mirrors in local compose — use the Hub paths above.
- ✗ `redis:*` for the cache service — Valkey is the cache image.

## Don'ts

- ✗ Committing `vendor/` (gitignored) or secrets (`.env*`, keys, `credentials*`).
- ✗ Hand-editing generated code (`internal/mocks/**`, `repository/postgres/sqlc/**`).
- ✗ Adding a noisy linter that inflates the baseline.
