---
name: audit-log
description: >
  Add per-request HTTP audit logging to an existing Go hexagonal microservice.
  Adds an audit_log table, a domain aggregate plus driven port, a sqlc postgres
  adapter, and an outermost gin middleware that records one row per inbound
  request (SUCCESS and FAILED) after the handler returns and before the
  response reaches the client. Persistence is fail-soft. Trigger on: "add audit
  log", "/audit-log", "เพิ่ม audit log", "audit middleware", "per-request audit",
  "ทำ audit log ให้เหมือน account-service". Not for entity created_by/updated_by
  actor strings, Kafka/async audit, or application logger lines.
metadata:
  version: "1.0"
---

# audit-log

Add **one `audit_log` row per inbound HTTP request** to an existing Go hexagonal
service. Pattern source: account-service MR
[196](https://gitlab.awesome-poc-th.com/libero-engineering/core/account-service/-/merge_requests/196)
(adapted from payment-gateway). Copy the templates in `assets/templates/`; do
not re-invent the middleware.

`SKILL_DIR` = this skill's base directory (from the skill-load message).

## Contract

```
inbound request
  → Audit: capture body (restore for handlers), wrap writer, start timer
    → existing middleware chain → route handler → response
    ← writer captures status + body
  ← Audit: derive SUCCESS/FAILED, INSERT fail-soft, THEN response to client
```

| Invariant | Rule |
|---|---|
| Cardinality | Exactly one row per inbound attempt, including `/health` and 4xx/5xx |
| Position | `r.Use(Audit(repo))` is the **first** `Use` in `middleware.Setup` |
| When | Persist **after** `c.Next()` returns, **before** the response is the client's problem — a persist error is logged, the request still succeeds |
| Nil repo | `writer == nil` → no-op (unit tests pass `nil`) |
| Status | HTTP `< 400` → `SUCCESS`; `>= 400` → `FAILED` |
| Route | `c.FullPath()` (pattern, e.g. `/v1/accounts/:id`), not `URL.Path` |
| `request_id` | `uuid.New()` at write time — not the correlation-id header |
| Body cap | 1 MiB; oversize → `413` + a `FAILED` row, handler never runs |
| JSON fields | `responseCode` ← JSON `responseCode`; `failureReason` ← JSON `message`; missing/non-JSON → `""` |
| `metadata` | JSONB `'{}'` unless the user named route-specific keys |
| `created_at` | Adapter stamps `time.Now()` on insert (ignore the aggregate's `CreatedAt`) |
| sqlc | `make db-gen` owns `sqlc/`; never hand-edit generated files |

Out of scope (do not add as part of this skill): entity `created_by` /
`updated_by` actor format (`mobile:<id>` was a separate account-service change);
Kafka / async audit; skipping routes; redacting PII in `raw_request` /
`raw_response` (bodies are stored as captured).

## Preconditions

Target is a **Go hexagonal gin + sqlc + postgres** service:

- `go.mod`
- `internal/delivery/http/middleware` with `Setup(*gin.Engine, …)`
- `internal/adapters/repository/postgres/{migrations,queries,sqlc}`
- `cmd/api` composition root

Anything else → stop and say so. Do not invent a chi/echo/kafka variant.

Already complete (`middleware/audit.go` **and** a `*create_audit_log.up.sql`
exist, wired through `Setup`) → report present, do not duplicate. Partial →
finish the missing layers only.

## Step 0 · Probe

Read, do not guess. Record:

| Fact | Where |
|---|---|
| Module path | `go.mod` |
| Next migration number | highest `NNNNNN_*.up.sql` under postgres migrations + 1, same zero-padding |
| Migration wrapper | `BEGIN;`/`END;` (or none) of the latest existing `.up.sql` — copy that style |
| Postgres schema name | existing `TRUNCATE <schema>.…` in e2e fixtures, or `search_path` / `DB_SCHEMA` |
| `Setup` / `router.New` signatures | current args — **append** `auditRepo` last; keep every existing param |
| `/health` | registered **after** `middleware.Setup` on the same engine (init-project / account-service). If it is not, do not use it as the SUCCESS e2e |
| `logger.Err` call shape | one existing `logger.Error(…, logger.Err(…))` site |
| common-lib import | `go.mod` require of `common-lib.git` — middleware template hardcodes v2; match the module path in use |
| DB error wrap | `NewDBError` in the postgres adapter package (use it; if absent, return `err`) |
| Sibling adapter field | `Queries *sqlc.Queries` vs unexported `q` — match the existing constructor |
| sqlc.yaml | `initialisms: []`, uuid → `uuid.UUID`, jsonb → `json.RawMessage`. After generate, map adapter fields to **generated** `InsertAuditLogParams` names |
| sqlc generate | `Makefile` `db-gen` (or `sqlc generate`) |
| e2e harness | `tests/e2e/**/*.e2e.ts` + a `DbHelper` — missing → skip Step 8 |
| ApiClient GET | `get(path)` on the helper (account-service has it). Missing → `globalThis.apiContext.get("/health")` |
| Cleanup SQL file | `seed-cleanup.sql` / `cleanup.sql` — whichever already truncates |

Completion: every cell filled from a file opened this session.

## Step 1 · Migration

Write the next `NNNNNN_create_audit_log.{up,down}.sql` from
`assets/templates/migrations/`. Keep the probed transaction wrapper. Do not edit a shipped migration.

Up file must contain: table `audit_log` with columns `id BIGSERIAL PK`,
`request_id UUID NOT NULL UNIQUE`, `http_method`, `route`, `status`,
`http_status`, `response_code`, `failure_reason`, `metadata JSONB`,
`raw_request`, `raw_response`, `duration_ms`, `created_at TIMESTAMPTZ`;
`CHECK (status IN ('SUCCESS','FAILED'))`; `CHECK (http_status BETWEEN 100 AND 599)`;
`CHECK (duration_ms >= 0)`; indexes `(http_method, route, created_at DESC)` and
`(status, created_at DESC)`. No schema prefix (search_path).

Completion: up + down files exist; down is `DROP TABLE IF EXISTS audit_log`.

## Step 2 · sqlc query + generate

Copy `assets/templates/queries/audit_log.sql` into the service's
`queries/` dir. Run the probed generate command (`make db-gen`).

Completion: generated `InsertAuditLog` / `InsertAuditLogParams` exist under
`sqlc/`; `models.go` gained `AuditLog`. `sqlc/` was not hand-edited.

## Step 3 · Domain

Copy `assets/templates/domain/` → `internal/core/domain/audit/`, substituting
`{{MODULE_PATH}}` in **every** copied file that contains it.

Completion: package `audit` has encapsulated `AuditLog`, `NewAuditLog`,
`AuditStatus_SUCCESS` / `AuditStatus_FAILED` (`"SUCCESS"` / `"FAILED"`), and
`AuditLogRepository.Insert(ctx, *AuditLog) error`.

## Step 4 · Adapter

Copy `assets/templates/adapter/audit_log.go` →
`internal/adapters/repository/postgres/audit_log.go`. Substitute
`{{MODULE_PATH}}`. Wrap insert errors with the probed DB helper. Match the
sibling adapter's `Queries` field name. After `make db-gen`, align
`InsertAuditLogParams` field names with the generated struct (do not assume
`RequestId` vs `RequestID` — org sqlc.yaml uses `initialisms: []` so `RequestId`
is the account-service form).

Completion: `NewAuditLogRepository(q *sqlc.Queries) audit.AuditLogRepository`
maps every getter except `CreatedAt` (stamp `time.Now()`).

## Step 5 · Middleware

Copy `assets/templates/middleware/audit.go` →
`internal/delivery/http/middleware/audit.go`. Substitute `{{MODULE_PATH}}` and
the probed common-lib import if it is not `common-lib.git/v2`. Match the probed
`logger.Err` signature if the copy does not compile.

In `middleware.Setup`, **keep the existing chain and existing parameters**.
Insert `r.Use(Audit(auditRepo))` as the first `Use` and **append** `auditRepo`
as the last parameter:

```go
func Setup(r *gin.Engine, serviceID string, /* existing args… */, auditRepo audit.AuditLogRepository) {
	r.Use(Audit(auditRepo))
	// existing Use lines unchanged
}
```

Register Audit on the **engine**, not a route group — `/health` must be covered.

Completion: `Audit` is the first `r.Use` in `Setup`; `Setup` takes
`audit.AuditLogRepository` last.

## Step 6 · Wire + every callsite

1. Composition root: `auditRepo := postgres.NewAuditLogRepository(queries)` next
   to the other repos; thread it into `router.New` (via `runHTTPServer` if that
   is the seam).
2. `router.New(…)` appends `auditRepo` and passes it to `middleware.Setup`.
3. Grep `middleware.Setup(` and `router.New(` under `cmd/` and
   `internal/delivery/http/` only — **every** callsite. Tests pass `nil`.

Completion: compile-clean; no leftover old signature.

## Step 7 · Domain + middleware tests

Copy `assets/templates/domain/auditlog_test.go` (already in Step 3) and
`assets/templates/middleware/audit_test.go` into the middleware package,
substituting `{{MODULE_PATH}}`.

account-service MR 196 had only the domain getter test; payment-gateway covered
the middleware with httptest. This skill ships both so `go test` of the
middleware package is not empty.

```bash
go test -short ./internal/core/domain/audit/ ./internal/delivery/http/middleware/
```

Completion: pass.

## Step 8 · E2E (only if a harness exists)

No `tests/e2e` Jest+Playwright-request harness → skip, say so, still done.

Otherwise:

1. Append to the existing cleanup/seed-cleanup SQL:

   ```sql
   TRUNCATE <schema>.audit_log RESTART IDENTITY;
   ```

   (`<schema>` from Step 0. The middleware writes a row per request including
   the health probe; without this the table grows across runs.)

2. Author `tests/e2e/specs/audit-log.e2e.ts` from
   `assets/templates/e2e/audit-log.e2e.ts`. Reuse `ApiClient` + `DbHelper`.
   - **SUCCESS:** `GET /health` — portable stand-in for MR 196's `POST /v1/accounts`.
     Requires `/health` on the same engine **after** `Setup` (probed). Set
     `SCHEMA` from Step 0; leaving `__SCHEMA__` is a fail.
     No `ApiClient.get` → `globalThis.apiContext.get("/health")`.
   - **FAILED:** a **registered** route that returns 4xx (validation reject).
     Do not use an unmatched path — `c.FullPath()` is empty on 404.
     Replace `REPLACE_ME` before running.
   - Title: `[<CARD> - AC-NNN] …` when a work record has ACs; else `[audit] …`.

3. Run the project's e2e script against a stack that has applied the new
   migration.

Completion: both cases query `<schema>.audit_log` and pass, or e2e skipped
with reason.

## Step 9 · Verify

```bash
go build ./...
go test -short ./internal/core/domain/audit/ ./internal/delivery/http/middleware/ ./internal/delivery/http/router/
```

Do **not** `go test` the whole postgres adapter package — account-service
keeps dockertest integration tests there. `go build` of that package is enough
for the new adapter file.

Confirm `Audit(` is the first `Use` in `Setup` by reading the file.

HTTP wire did not change (no new public endpoint) → `apispeccheck` /
`openapi-doc` are not triggered. Production code changed → package tests +
coverage ≥ 80% on **touched packages that have tests** (`domain/audit`,
`middleware`). Adapter coverage is not required (MR 196 had none).

## Report

```
## audit-log
**Target:** <module path>
**Migration:** <NNNNNN_create_audit_log>
**Wired:** Setup first Use = Audit · composition root passes repo
**Tests:** domain <pass/fail> · e2e <pass/fail/skipped: reason>
**Callsites updated:** <N> Setup / New (tests nil)
```

## Rationalizations

| Thought | Reality |
|---|---|
| "Put Audit after Recovery so panics aren't audited" | Outermost. A 500 still gets a FAILED row. |
| "Reuse correlation-id as request_id" | New UUID. Correlation-id stays a log field. |
| "Skip /health, it's noise" | One row per inbound request includes /health. Cleanup TRUNCATEs. |
| "FAILED e2e via GET /no-such-route" | Unmatched 404 has empty `FullPath()`. Use a registered 4xx. |
| "Hand-write sqlc/ to save a generate" | `make db-gen` only. |
| "Also set created_by to mobile:id" | Different change. Out of scope here. |
| "Redact bodies, PII" | Store as captured unless the user asked to redact. |
