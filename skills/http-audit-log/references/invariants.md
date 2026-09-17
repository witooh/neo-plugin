# one-row invariants

The portable contract. Match these; do not invent a second schema.

Reference implementation: account-service MR 196 (`feat/GI-3453-3531-audit-log`), itself adapted from `payment-gateway`.

## Row

One `audit_log` row per inbound HTTP request, SUCCESS and FAILED.

| Column | Rule |
| --- | --- |
| `id` | `BIGSERIAL` PK |
| `request_id` | `UUID NOT NULL UNIQUE`, a fresh `uuid.New()` (not the correlation / request-id header) |
| `http_method` | verb |
| `route` | `c.FullPath()` (the registered route, not the raw URL) |
| `status` | `SUCCESS` if HTTP `< 400`, else `FAILED`. CHECK `IN ('SUCCESS','FAILED')` |
| `http_status` | CHECK `BETWEEN 100 AND 599` |
| `response_code` | fail-soft from JSON key `responseCode`, else `''` |
| `failure_reason` | fail-soft from JSON key `message`, else `''` |
| `metadata` | JSONB, default `{}`. Extension point for searchable fields; leave `{}` unless the user names keys |
| `raw_request` / `raw_response` | captured bodies, cap 1MB |
| `duration_ms` | CHECK `>= 0` |
| `created_at` | `TIMESTAMPTZ`, adapter stamps `time.Now()` on insert |

Indexes: `(http_method, route, created_at DESC)` and `(status, created_at DESC)`.

Table lives on the service `search_path` (no schema prefix in the migration). E2e queries `<schema>.audit_log`.

## Middleware

- **outermost**: first `r.Use` in `Setup`, so it wraps ServiceId / CorrelationId / error handler / recovery / the route.
- Capture request body, restore `c.Request.Body` for handlers, wrap the writer, `c.Next()`, then INSERT, then the client sees the response.
- Body `ContentLength` or actual bytes over 1MB: abort 413, still write a FAILED row (`raw_request` = `[truncated: request body too large]`).
- `persistAuditLog`: `writer == nil` is a no-op (tests pass `nil`). Insert error is logged and swallowed. Auditing never changes the HTTP outcome.
- Every inbound route is audited, including `/health`.

## Layers

Hexagonal cut, same as the rest of the service:

- domain owns `AuditLog` (private fields, `NewAuditLog(NewAuditLogParam)`, getters) and `AuditLogRepository.Insert`
- postgres adapter implements the port via sqlc `InsertAuditLog :exec`
- `sqlc.yaml` must override `uuid` → `google/uuid` and `jsonb` → `json.RawMessage` so the generated params match the aggregate
- delivery owns gin `Audit(writer)`
- `cmd/api` constructs the repo and threads it `runHTTPServer` → `router.New` → `middleware.Setup`

## Out of this skill

The same account-service MR also changed `created_by` / `updated_by` to `mobile:<customerId>`. That is an account-open actor format, not HTTP audit. Leave those columns alone unless the user asked for that separately.
