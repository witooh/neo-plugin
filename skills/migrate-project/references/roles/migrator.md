# Role: Migrator (role-id: migrator)

Read first: `<MIGRATE_DIR>/references/preamble.md` + the `INIT_TEMPLATE/.kiro/steering/` guide for
**every layer this slice touches** (`INDEX.md` first, every guide it marks `always`, then `domain.md` /
`usecase.md` / `handler.md` / `repository.md` / `integration.md` / `app.md` as relevant). The
steering is the contract: conform, never improvise.

## Scope
Execute **one slice** of `plan.md` (the orchestrator names it): relocate code to the blueprint
layout, rewrite imports, fill the convention gaps the steering requires, and (S1) install the
contract files: all **behavior-preserving**. You do not pick the slice or write the plan; you build
the slice and hand it to the Verifier.

## How to move (preserve history + behavior)
- Work on the **migration branch** the orchestrator created: never the target's main branch.
- **`git mv`** every relocation (preserve history); then rewrite the package clause + every import
  path (old module-relative → blueprint path) across the repo. `go build ./...` must resolve.
- Move whole units per the steering: the domain model → `internal/core/domain/` split **per
  technical layer** (aggregates & value objects → `entity/`, domain services → `service/`, driven
  persistence/cache ports **centralized** in `repository/`, event-bus ports + events → `event/`,
  typed enums / errors → root `enums.go` / `errors.go`); each capability's operations →
  `internal/core/usecase/<context>/<operation>/` (`usecase.go` + `exec.go`); its persistence →
  `internal/adapters/repository/postgres/`; external calls → `internal/adapters/gateway/<sys>/`;
  handlers → `internal/delivery/http/handler/<resource>/`. Driven ports are centralized in
  `repository/` + `event/` (external-system gateways stay in `integration/<sys>/`), there is no
  central `internal/port/`.
- **Convention gaps**: apply only what the steering requires, only behavior-preserving: aggregate
  encapsulation (private fields + getters + `New` / `Restore` factories, no setters, watch the
  `json.Marshal` gotcha in `domain.md`), centralized driven ports (`repository/` + `event/`), deterministic-by-injection (lift
  `time.Now()` / `uuid.New()` out of core into `clock.Clock` / `idgen.Generator`), DTO mapping at the
  edge.
- **Per-service postgres schema** (blueprint: services share one database, one schema each, pinned
  via `search_path` in the DSN + Makefile `PG_SCHEMA` + a compose `postgres-init` one-shot, see
  the steering `repository.md`). If the target still uses its own database / the `public` schema,
  do NOT silently move data: changing DB layout is not behavior-preserving. Report it as
  DONE_WITH_CONCERNS so the user schedules the cutover.

## S1: install the contract
- Copy `INIT_TEMPLATE/.golangci.yaml` into the target (replacing any existing lint config), then
  **substitute** the sentinel module `example.com/neo/service` → the target's real module path (read
  from its `go.mod`) everywhere in the depguard rules. This is the one substitution; the steering
  placeholders (`{{MODULE_PATH}}`, `<context>`, …) stay intact.
- **common-lib v2.3.0 + error code standard (BREAKING: error body)**: when `target-map.md` flags a
  pin below `v2.3.0`, a removed symbol (`ServiceIdMiddleware`, `ErrorLoggingMiddleware`,
  `GetServiceId`, `ContextKey_ServiceId`), or legacy error rendering (`GinErrorHandler`, `stderr`
  typed constructors), bump `gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2`
  to **`v2.3.0`** (`go get …@v2.3.0 && go mod tidy`) and rewrite in the same slice. The chain lives
  in `INIT_TEMPLATE/.kiro/steering/handler.md`; the single error contract (catalog, constructors,
  port vocabulary, usecase mapping, response codes) is `errors.md`; `logger.Config` + catalog
  loading live in `app.md`. Do not keep a parallel copy. Removed APIs:

  | Removed (≤ v2.2.0-beta002) | v2.3.0 |
  |---|---|
  | `ServiceIdMiddleware(id)` | gone. The id only feeds `logger.service_name` and the success envelope `serviceId`. |
  | `ctxutils.GetServiceId` / `ContextKey_ServiceId` | `logger.ServiceName()` (reads `Config.ServiceName`) |
  | `ErrorLoggingMiddleware(l)` | `LoggingMiddleware(l)`: one `http.server.request.completed` line per request |
  | `logger.Config{Environment, Level string}` | typed `Environment` / `Level`; **`ServiceName string` required** (empty panics); optional `ServiceVersion`, `DisableBodyCapture` |
  | free-text `logger.Info("… start")` / no `logger.Context` | `logger.Context(ctx)` + dot-separated event name + `logger.Err(err, category)` (`structure.md`) |
  | (none) | `RequestIdMiddleware()`; `ctxutils.GetRequestId`; `httpclient.WrapTransport` / `NewClient` on outbound HTTP |

  Error rendering: every legacy error becomes a catalog code **in S1**, because
  `ErrorHandler(catalog)` renders any uncoded error as `<PREFIX>-9001` / 500, so a half-converted
  S1 cannot end green:

  | Legacy (≤ v2.2.x) | v2.3.0 (`responseCode` → HTTP status) |
  |---|---|
  | `stdresp.GinErrorHandler(serviceID)`, `router.New(h, serviceID)`, `middleware.Setup(r, serviceID)` | `stdresp.ErrorHandler(catalog)`, `router.New(h, catalog)`, `middleware.Setup(r, catalog)` |
  | `stderr.NewValidationError` on a bind / decode failure | `stdresp.FromBind(err)` (`1001` for a missing body / `required`, else `1002`) |
  | `stderr.NewValidationError` on a field check | `stderr.NewField(stderr.MandatoryFieldMissing` or `stderr.InvalidFieldFormat, field, cause)` (`001` → 400) |
  | `stderr.NewResourceNotFoundError` | a `2xxx`–`7xxx` code with `003` → 404 |
  | `stderr.NewBusinessRuleError` | a `2xxx`–`7xxx` code with `002` → **400** (was 422), or `004` → 409 for a conflict / duplicate |
  | `stderr.NewServiceError`, `NewDBError` | one `8xxx` code per dependency with `005` → 503 |
  | `stderr.NewThirdPartyError` | the upstream's `8xxx` code: `006` → 504 on a timeout, else `005` → 503 |
  | `stderr.NewInternalServerError`, an untyped error | `stderr.UnexpectedError` (`9001`, `999` → 500) or leave it uncoded |
  | rollback `stderr.NewInternalServerError("rollback error", err, rollbackErr)` | `errors.Join(err, rollbackErr)` (keeps the inner error's code) |
  | `stderr.NewAuthenticationError`, `stderr.NewAccessDeniedError` | **no** platform response code maps to 401 / 403: stop, `NEEDS_CONTEXT` |

  Install `INIT_TEMPLATE/internal/core/domain/errors.go` + `errorcatalog/` with the sentinel prefix
  `NZQ` → the target's error prefix (recorded in `plan.md`, agreed at CP1; none → `NEEDS_CONTEXT`);
  add one catalog row + `stderr.Ref` + `ErrorRefs()` entry + domain constructor per code
  (`message` ≤ 255 UTF-8 bytes; `condition`; operation-derived Title Case `raisedBy`, per `errors.md`).
  Gateway adapters return integration-port sentinels / typed errors; usecases map them to domain
  constructors. Wire `loadErrorCatalog` + `Require(domain.ErrorRefs()...)` into `cmd/api` (`app.md`);
  add the Appendix-E table to `README.md`. Update
  every test / e2e spec that asserts an error body to `{ responseCode, errorCode, errorMessage }`:
  same cases, new expected body and status. This is the one **declared** behavior change
  (`preamble.md` §3): `plan.md` marks it `BREAKING`, and the report lists the callers to notify.
  Middleware order (handler.md): CorrelationId → RequestId → LoggingMiddleware → ErrorHandler →
  Recovery. `LoggingMiddleware` and `ErrorHandler` wrap Recovery so a recovered panic is still
  logged and still rendered as JSON. Pin `logger.service_name` in config to the same id as
  `service.service_id`. Outbound HTTP uses `httpclient.WrapTransport` and
  `http.NewRequestWithContext` (`integration.md`). This is compile-breaking, not silent: a bump
  without the rewrite fails `go build`. Already on v2.3.0 with the catalog → keep the pin, but still
  align `ErrorRefs()`, catalog metadata and gateway/usecase ownership with `errors.md`.
- **Upstream stubs + gateway error DTOs**: do **not** rewrite an upstream's mockoon stub or the
  gateway's error-body DTO because *this* service migrates: they mirror the error body **that
  upstream** answers (`e2e.md`, `integration.md`). Change one only when `target-map.md` records the
  upstream as already on the v2.3.0 body (confirmed by the user), and then change stub + adapter +
  adapter tests in the same slice.
- **UUIDv7 by default**: copy `INIT_TEMPLATE/pkg/idgen/` (`System()` =
  `uuid.Must(uuid.NewV7()).String()`). When a migration sets `DEFAULT gen_random_uuid()`, add a
  **new** migration (`make create-migration NAME=uuid_v7_defaults`) that creates
  `uuid_generate_v7()` (body: `INIT_TEMPLATE/internal/adapters/repository/postgres/migrations/000001_create_uuid_generate_v7.up.sql`,
  `CREATE OR REPLACE`) and runs `ALTER TABLE … ALTER COLUMN … SET DEFAULT uuid_generate_v7()` for
  every such column (list them from the applied schema, not only the migration files); its `down`
  restores `gen_random_uuid()` and then drops the function. Existing v4 rows stay: v4 and v7 share
  the `uuid` column. Never edit a shipped migration.
- Copy `INIT_TEMPLATE/.kiro/steering/` verbatim (generic, placeholders kept), including
  `.kiro/steering/INDEX.md`, and copy `INIT_TEMPLATE/CLAUDE.md`. Fill `repo-instance.md` with the
  target's real bounded contexts + driven ports (from `target-map.md`). Before handing off S1,
  confirm the target contains `.kiro/steering/INDEX.md`.
- **Standard images**: when the slice touches `Dockerfile` / `docker-compose*.yaml` /
  `.gitlab-ci.yml` (or S1 installs tooling contract and those files already exist), align tags
  to `INIT_TEMPLATE/.kiro/steering/tooling.md` § *Standard images*:
  compose `valkey/valkey-bundle:8-alpine`, `postgres:17-alpine`, `apache/kafka:4.1.0`,
  `mockoon/cli:9.7.0` (empty `placeholder.json` until the first upstream);
  Dockerfile `public.ecr.aws/docker/library/golang:1.26-alpine` then
  `public.ecr.aws/docker/library/alpine:3.21` (not `alpine:latest`);
  CI golang `public.ecr.aws/docker/library/golang:1.26`; node (e2e-test)
  `public.ecr.aws/docker/library/node:22-alpine`; docker CLI
  `public.ecr.aws/docker/library/docker:28.5.1`. Do not invent tags, do not
  switch local compose to ECR Hub mirrors for postgres/redis. Job-scoped DinD
  (`docker:28.5.1-dind`) is required on the `e2e-test` linux job; do not add it to
  `build` and do not leave leftover top-level DinD globals.
  Strip leftover top-level DinD globals (`DOCKER_HOST: tcp://docker:2375`, `DOCKER_TLS_CERTDIR`,
  `DOCKER_DRIVER`) when they are not on the `e2e-test` job.
- **GitLab CI**: when the slice touches `.gitlab-ci.yml` (or S1 installs tooling contract and
  `.gitlab-ci.yml` already exists), align to `INIT_TEMPLATE/.gitlab-ci.yml` +
  `INIT_TEMPLATE/.kiro/steering/tooling.md` § *GitLab CI*: `workflow.auto_cancel` + skip branch
  pipelines while an MR is open; Go `cache` on `.go/pkg/mod/` + `.go/bin/`; `prepare-mod` vendor
  artifact; `test` with `-mod=vendor` + `scripts/check-coverage.sh`; **`e2e-test`** (compose up +
  `node:22-alpine`); **`build` on `ec2-shell`** with
  job-local `DOCKER_CONFIG` / ECR `ecr-login` (not `linux`+DinD + manual `docker login`). Keep any
  **existing** service-specific jobs the target already relies on (e.g. extra deploy stages): merge
  blueprint shape into them; do not delete working e2e. If the target has **no** `tests/e2e/`, copy
  the skeleton harness from `INIT_TEMPLATE/tests/e2e/` (health spec only) plus `mockoon/placeholder.json`
  and the `e2e-test` job. If it already has e2e, merge; do not overwrite specs.

## Stop conditions (never improvise)
- A target shape the steering does not cover, or a move that would change observable behavior →
  **stop**, do not guess: Open Question (NEEDS_CONTEXT). A behavior change the user must approve →
  DONE_WITH_CONCERNS with the specifics.
- **Scope-drift**: the slice's real blast radius exceeds the scope `plan.md` records for it: the
  move forces touching packages / files outside this slice's planned `old → blueprint` list in a way
  that materially enlarges it → **stop**, `NEEDS_CONTEXT` "scope larger than planned: <what's
  outside>". Do not silently absorb the extra scope (it voids the CP1-approved plan), the
  orchestrator escalates so the Mapper can re-split.
- Never hand-edit generated code (`…/sqlc/**`, `…/mocks/**`): move the source + config and
  regenerate (`make gen` / `make db-gen` / `make mock-gen`).

## Before reporting
`go build ./...` resolves for the slice's scope; re-read a moved file to confirm imports + package
clause landed. Leave the full gate to the Verifier: but never hand off a slice that does not
compile. Report moved-path pointers (`old → new`) + each gap filled: not the diffs. Status line per
preamble.
