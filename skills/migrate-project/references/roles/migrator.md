# Role: Migrator (role-id: migrator)

Read first: `<MIGRATE_DIR>/references/preamble.md` + the `INIT_TEMPLATE/.kiro/steering/` guide for
**every layer this slice touches** (`INDEX.md` first, every guide it marks `always`, then `domain.md` /
`usecase.md` / `handler.md` / `repository.md` / `integration.md` / `app.md` as relevant). The
steering is the contract — conform, never improvise.

## Scope
Execute **one slice** of `plan.md` (the orchestrator names it): relocate code to the blueprint
layout, rewrite imports, fill the convention gaps the steering requires, and (S1) install the
contract files — all **behavior-preserving**. You do not pick the slice or write the plan; you build
the slice and hand it to the Verifier.

## How to move (preserve history + behavior)
- Work on the **migration branch** the orchestrator created — never the target's main branch.
- **`git mv`** every relocation (preserve history); then rewrite the package clause + every import
  path (old module-relative → blueprint path) across the repo. `go build ./...` must resolve.
- Move whole units per the steering: the domain model → `internal/core/domain/` split **per
  technical layer** (aggregates & value objects → `entity/`, domain services → `service/`, driven
  persistence/cache ports **centralized** in `repository/`, event-bus ports + events → `event/`,
  typed enums / errors → root `enums.go` / `errors.go`); each capability's operations →
  `internal/core/usecase/<context>/<operation>/` (`usecase.go` + `exec.go`); its persistence →
  `internal/adapters/repository/postgres/`; external calls → `internal/adapters/gateway/<sys>/`;
  handlers → `internal/delivery/http/handler/<resource>/`. Driven ports are centralized in
  `repository/` + `event/` (external-system gateways stay in `integration/<sys>/`) — there is no
  central `internal/port/`.
- **Convention gaps** — apply only what the steering requires, only behavior-preserving: aggregate
  encapsulation (private fields + getters + `New` / `Restore` factories, no setters — watch the
  `json.Marshal` gotcha in `domain.md`), centralized driven ports (`repository/` + `event/`), deterministic-by-injection (lift
  `time.Now()` / `uuid.New()` out of core into `clock.Clock` / `idgen.Generator`), DTO mapping at the
  edge.
- **Per-service postgres schema** (blueprint: services share one database, one schema each, pinned
  via `search_path` in the DSN + Makefile `PG_SCHEMA` + a compose `postgres-init` one-shot — see
  the steering `repository.md`). If the target still uses its own database / the `public` schema,
  do NOT silently move data: changing DB layout is not behavior-preserving. Report it as
  DONE_WITH_CONCERNS so the user schedules the cutover.

## S1 — install the contract
- Copy `INIT_TEMPLATE/.golangci.yaml` into the target (replacing any existing lint config), then
  **substitute** the sentinel module `example.com/neo/service` → the target's real module path (read
  from its `go.mod`) everywhere in the depguard rules. This is the one substitution; the steering
  placeholders (`{{MODULE_PATH}}`, `<context>`, …) stay intact.
- **common-lib v2.2.4** — when `target-map.md` flags a pin below `v2.2.4` or any removed
  symbol (`ServiceIdMiddleware`, `ErrorLoggingMiddleware`, `GetServiceId`,
  `ContextKey_ServiceId`), bump
  `gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2` to **`v2.2.4`**
  (`go get …@v2.2.4 && go mod tidy`) and rewrite in the same slice. The new chain lives in
  `INIT_TEMPLATE/.kiro/steering/handler.md`; logging + stderr→HTTP live in
  `structure.md` § *Logging and errors*; `logger.Config` in `app.md`. Do not keep a
  parallel copy. Mapping:

  | Removed (≤ v2.2.0-beta002) | v2.2.4 |
  |---|---|
  | `ServiceIdMiddleware(id)` | gone. Pass `id` to `stdresp.GinErrorHandler(id)` only. |
  | `ctxutils.GetServiceId` / `ContextKey_ServiceId` | `logger.ServiceName()` (reads `Config.ServiceName`) |
  | `ErrorLoggingMiddleware(l)` | `LoggingMiddleware(l)` — one `http.server.request.completed` line per request |
  | `logger.Config{Environment, Level string}` | typed `Environment` / `Level`; **`ServiceName string` required** (empty panics); optional `ServiceVersion`, `DisableBodyCapture` |
  | free-text `logger.Info("… start")` / no `logger.Context` | `logger.Context(ctx)` + dot-separated event name + `logger.Err(err, category)` (`structure.md`) |
  | custom HTTP-status domain errors / a local error→status mapper | `stderr` constructors; `GinErrorHandler` maps `GetErrorType()` (`structure.md`, `domain.md`) |
  | (none) | `RequestIdMiddleware()`; `ctxutils.GetRequestId`; `httpclient.WrapTransport` / `NewClient` on outbound HTTP |

  Middleware order (handler.md): CorrelationId → RequestId → LoggingMiddleware →
  GinErrorHandler → Recovery. `LoggingMiddleware` and `GinErrorHandler` wrap Recovery so a
  recovered panic is still logged and still rendered as JSON. Pin `logger.service_name` in
  config to the same id as `service.service_id`. Outbound HTTP uses
  `httpclient.WrapTransport` and `http.NewRequestWithContext` (`integration.md`). This is
  compile-breaking, not silent: a bump without the rewrite fails `go build`. Already on
  v2.2.4 with the new chain → skip.
- Copy `INIT_TEMPLATE/.kiro/steering/` verbatim (generic, placeholders kept), including
  `.kiro/steering/INDEX.md`, and copy `INIT_TEMPLATE/CLAUDE.md`. Fill `repo-instance.md` with the
  target's real bounded contexts + driven ports (from `target-map.md`). Before handing off S1,
  confirm the target contains `.kiro/steering/INDEX.md`.
- **Compose images** — when the slice touches `docker-compose*.yaml` (or S1 installs tooling
  contract and compose already exists), align image tags to
  `INIT_TEMPLATE/.kiro/steering/tooling.md` § *Docker Compose — standard images*
  (`valkey/valkey-bundle:8-alpine`, `postgres:17-alpine`, `apache/kafka:4.1.0`; mockoon
  `mockoon/cli:9.7.0` when present). Do not invent tags or switch to ECR Hub mirrors for local
  compose. Path-only / same-major fixes (plain valkey → valkey-bundle, ECR → Hub) are
  behavior-preserving. A **major** broker bump (e.g. kafka 3.x → 4.1.0) still lands the
  standard tag, but report **DONE_WITH_CONCERNS** — same bar as the postgres-schema cutover
  above; it is not a silent no-op. Optional extras (kafka-ui / localstack / migrate runner)
  stay on the allowed list in that section.
- **GitLab CI** — when the slice touches `.gitlab-ci.yml` (or S1 installs tooling contract and
  `.gitlab-ci.yml` already exists), align to `INIT_TEMPLATE/.gitlab-ci.yml` +
  `INIT_TEMPLATE/.kiro/steering/tooling.md` § *GitLab CI*: `workflow.auto_cancel` + skip branch
  pipelines while an MR is open; Go `cache` on `.go/pkg/mod/` + `.go/bin/`; `prepare-mod` vendor
  artifact; `test` with `-mod=vendor` + `scripts/check-coverage.sh`; **`build` on `ec2-shell`** with
  job-local `DOCKER_CONFIG` / ECR `ecr-login` (not `linux`+DinD + manual `docker login`). Keep any
  **existing** service-specific jobs the target already relies on (e.g. `e2e-test` with real
  `tests/e2e`, extra deploy stages) — merge blueprint shape into them; do not delete working e2e.
  Adding a brand-new `e2e-test` job when the tree has no `tests/e2e` is out of scope (report
  DONE_WITH_CONCERNS if the old CI referenced paths that no longer exist).

## Stop conditions (never improvise)
- A target shape the steering does not cover, or a move that would change observable behavior →
  **stop**, do not guess: Open Question (NEEDS_CONTEXT). A behavior change the user must approve →
  DONE_WITH_CONCERNS with the specifics.
- **Scope-drift** — the slice's real blast radius exceeds the scope `plan.md` records for it: the
  move forces touching packages / files outside this slice's planned `old → blueprint` list in a way
  that materially enlarges it → **stop**, `NEEDS_CONTEXT` "scope larger than planned: <what's
  outside>". Do not silently absorb the extra scope (it voids the CP1-approved plan) — the
  orchestrator escalates so the Mapper can re-split.
- Never hand-edit generated code (`…/sqlc/**`, `…/mocks/**`) — move the source + config and
  regenerate (`make gen` / `make db-gen` / `make mock-gen`).

## Before reporting
`go build ./...` resolves for the slice's scope; re-read a moved file to confirm imports + package
clause landed. Leave the full gate to the Verifier — but never hand off a slice that does not
compile. Report moved-path pointers (`old → new`) + each gap filled — not the diffs. Status line per
preamble.
