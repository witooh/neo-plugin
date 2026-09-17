---
name: http-audit-log
description: >
  Add per-request HTTP audit logging to a Go hexagonal gin+sqlc service: one
  audit_log row per inbound request, written by the outermost gin middleware
  after the handler returns and before the client sees the response.
  Persistence is fail-soft. Ports the account-service pattern (domain audit
  aggregate, postgres adapter, middleware, tests). Use when adding an audit
  log, an audit_log table, gin audit middleware, per-request audit, or Thai
  "เพิ่ม audit log" / "สร้าง audit log". Not created_by/updated_by actor
  columns. Not OpenAPI.
---

# HTTP audit log (one-row)

Port the **one-row** HTTP audit: one `audit_log` row per inbound HTTP request,
SUCCESS and FAILED, captured by the **outermost** gin middleware, persisted
**fail-soft** (a write error never fails the request).

Reference: account-service MR 196. Copy that pattern. Do not invent a second
schema.

`ASSET_DIR` = `<skill base dir>/assets`. Read
[`references/invariants.md`](references/invariants.md) before editing. Copy
templates from `assets/templates/` (drop a `.tmpl` suffix when present);
replace `__MODULE__` with the target's `go.mod` module path.

## Preconditions

A Go hexagonal service with gin, sqlc, and postgres migrations, the
account-service / `init-project` layout. Confirm by opening `go.mod`,
`internal/delivery/http/middleware/`, `internal/adapters/repository/postgres/`.
Missing that layout → STOP and say why. Already has `audit_log` → STOP unless
the user asked for a delta.

## Step 1 · Domain

Write `internal/core/domain/audit/` from the templates (`auditlog.go`,
`repository.go`, `auditlog_test.go`). Package comment, private fields,
`NewAuditLog`, getters, `AuditStatus_SUCCESS` / `AuditStatus_FAILED`.

Done when `go test ./internal/core/domain/audit/` is green.

## Step 2 · Migration + sqlc

Next migration number (or timestamp, if that is what this repo uses), named
`create_audit_log`. Copy `000N_create_audit_log.up.sql` / `.down.sql` and
`queries/audit_log.sql`. Confirm `sqlc.yaml` overrides `uuid` → `google/uuid`
and `jsonb` → `json.RawMessage`; add them if absent. Run `make db-gen`. Never
hand-edit `sqlc/`.

Done when generated `InsertAuditLog` exists and `go build ./...` is green.

## Step 3 · Adapter

Copy `postgres/audit_log.go.tmpl`. `NewAuditLogRepository` returns the domain
port. Map getters onto the generated `InsertAuditLogParams` field names (sqlc
may emit `HttpMethod` or `HTTPMethod`). Stamp `CreatedAt` with `time.Now()`.
Wrap errors with this service's `NewDBError`.

Done when the postgres package compiles.

## Step 4 · Middleware + wire

Copy `middleware/audit.go.tmpl` and `audit_test.go.tmpl`. Align `logger.Error` /
`logger.Err` with the signature already used in `middleware.go` (include the
category argument when this service uses one).

Wire, do not reorder the rest of the chain:

1. `Setup(r, serviceID, auditRepo)` registers `r.Use(Audit(auditRepo))` **first**.
2. `router.New(..., auditRepo)` threads it into `Setup`.
3. `cmd/api`: `auditRepo := postgres.NewAuditLogRepository(queries)` into
   `runHTTPServer` → `router.New`.
4. Grep `middleware.Setup(` and `router.New(`: every callsite takes the extra
   arg. Tests may pass `nil` (no-op persist).

Done when `go test ./internal/delivery/http/...` is green and Audit is the first
`r.Use` in `Setup`.

## Step 5 · E2e (only if `tests/e2e` exists)

Reuse the target's HTTP client + `DbHelper`. SUCCESS probe defaults to `GET
/health` (every skeleton has it). FAILED probe: one known 4xx. Query
`<schema>.audit_log`. Append `TRUNCATE <schema>.audit_log RESTART IDENTITY;` to
the e2e cleanup SQL. No 4xx path → skip the FAILED probe and say the middleware
unit test covers it. No harness → skip this step and say so.

HTTP-observable ACs on the originating ticket: call the Skill tool with
"e2e-playwright" after the middleware is wired. No ACs: keep the probes.

Done when the SUCCESS probe sees one matching row, or the skip is reported.

## Step 6 · Verify

```
python3 <ASSET_DIR>/auditcheck.py
go test ./internal/core/domain/audit/ ./internal/delivery/http/...
go build ./...
```

`go build` does not typecheck `_test.go`; the `go test` line is what catches a
forgotten `Setup`/`New` callsite. `auditcheck.py` is a tripwire, not ground
truth. Exit 1 → fix the real defect, re-run. Loop until exit 0, or ~3 rounds
with no progress → STOP.

Done when the script exits 0 and the tests above are green.

## Step 7 · Report

```
## HTTP audit log
**Service:** <module>   **Schema:** <postgres schema>
**Files:** domain / migration NNNN / adapter / middleware / callsites
**E2e:** SUCCESS+FAILED probes / skipped (no tests/e2e)
**Verify:** auditcheck.py exit 0 · go test <packages> · go build
```

## What this skill is NOT

- **Not** `created_by` / `updated_by` / `mobile:<id>` actor columns. Same MR
  shipped that for account-open only; this skill does not.
- **Not** an API spec, Bruno collection, or Confluence page (`api-spec` /
  `open-collection` / `confluence-api-doc`).
- **Not** a new e2e harness (`e2e-playwright` authors AC tests on an existing
  one).
