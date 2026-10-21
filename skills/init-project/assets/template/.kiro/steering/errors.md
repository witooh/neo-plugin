---
inclusion: always
---

# Errors — common error code standard (common-lib `stderr` / `stdresp` v2.3.0+)

The **single** guide for errors in every layer. Other guides point here; when they disagree, this
file wins. Sources: the design is the Common Error Code HLD v0.3 on the team design board
("Neobank - Project › REQ - Technical"); the shipped API is common-lib `README.md` § "Error codes
(`responseCode` / `errorCode`)". This guide follows the payment-gateway standard; service-specific
prefixes and business codes live in the generated service, not in this template.

`<PREFIX>` is this service's 2–3 letter code prefix (this repo: see `repo-instance.md`). It must not
collide with another service's — taken: `ACC CUS PRD PAY GLM BOT CST FRD`. Examples use the neutral
`Order` domain.

## The contract (what a caller sees)

Every outbound HTTP error answers exactly this body — nothing else, no correlation id, no serviceId:

```json
{"responseCode": "002", "errorCode": "<PREFIX>-2001", "errorMessage": "Order is not active"}
```

- `errorMessage` is for **logs and support**, not customer wording — the BFF maps `errorCode` to the
  channel's text. The correlation id travels in header `x-correlation-id` and on every log line.
- **HTTP status follows `responseCode`** (common-lib owns the table); no code here sets a status:

  | responseCode | meaning | HTTP |
  |---|---|---|
  | `001` | request validation failed | 400 |
  | `002` | business rule violation | 400 |
  | `003` | resource not found | 404 |
  | `004` | duplicate / conflicting request | 409 |
  | `005` | downstream unavailable — **not processed**, safe to retry | 503 |
  | `006` | downstream timeout — **outcome unknown**, check status before retry | 504 |
  | `999` | unexpected error | 500 |

- **Code ranges** (`<PREFIX>-NNNN`): `1xxx` validation → `001` · `2xxx–7xxx` business, grouped by
  domain → `002/003/004` · `8xxx` downstream, **one code per dependency** (each service, DB, cache,
  event bus, vendor) → `005/006` · `9xxx` unexpected → `999`.
- **Reserved by common-lib** (never declared here, render with our prefix): `1001` mandatory field
  missing (`stderr.MandatoryFieldMissing`), `1002` invalid field format (`stderr.InvalidFieldFormat`),
  `9001` unexpected (`stderr.UnexpectedError`). Any error without a catalog code — a raw `error`, a
  panic — becomes `9001`; its text is logged, never returned.

## The catalog — `internal/core/domain/errorcatalog/errors.json`

Appendix-E as data. `embed.go` embeds it; `cmd/api` loads it at startup. One line per entry, exactly
these keys — common-lib rejects any other key and **the service will not start**:

```json
{"prefix": "<PREFIX>", "errors": [
  {"code": "<PREFIX>-2001", "responseCode": "002", "message": "Order is not active", "condition": "order is CLOSED or CANCELLED", "raisedBy": "Cancel Order, Ship Order"}
]}
```

- `message` — 1–255 **bytes** UTF-8. A Thai character is 3 bytes (~85 Thai characters max); over the
  limit `LoadCatalog` fails and the service will not start.
- `condition` — required; when the error happens (Thai or English, no length limit).
- `raisedBy` — required; who raises it, names joined by `", "` (comma + space):
  - a **usecase** is named by its `<operation>` package in Title Case —
    `usecase/order/cancel_order` → `Cancel Order`. Never a nickname: the name must match the package that calls the constructor.
  - a source that is **not a usecase** (Kafka consumer, background job, middleware) gets a Title Case
    name in the Account Service style, e.g. `Order Event Consumer`.
  - `All` only as the whole value and only on an `8xxx` code every usecase raises. No `All …`
    variants, routes (`PATCH /orders`), paths or lowercase names.
- Do not list `1001`, `1002`, `9001`.

## Layer by layer

### Domain — `internal/core/domain/errors*.go` (`package domain`)

Declares the codes and the only constructors. One `Ref` per catalog row, one constructor per code,
plus a list of every `Ref` for the catalog test:

```go
var (
	ErrOrderNotActive       = stderr.Ref("<PREFIX>-2001")
	ErrInventoryUnavailable = stderr.Ref("<PREFIX>-8001")
)

func NewOrderNotActiveError() error { return stderr.New(ErrOrderNotActive, nil) }

func NewInventoryUnavailableError(cause error) error { return stderr.New(ErrInventoryUnavailable, cause) }

func NewMandatoryFieldMissingError(field, detail string) error {
	return stderr.NewField(stderr.MandatoryFieldMissing, field, errors.New(detail))
}

func NewInvalidFieldFormatError(field, detail string) error {
	return stderr.NewField(stderr.InvalidFieldFormat, field, errors.New(detail))
}

func ErrorRefs() []stderr.Code { return []stderr.Code{ErrOrderNotActive, ErrInventoryUnavailable} }
```

- A constructor takes a `cause` only when there is one (a dependency failure); the cause is logged,
  never rendered. `NewField` appends `": <field>"` to `errorMessage`.
- Split validation by meaning: "required / empty" → `NewMandatoryFieldMissingError` (1001); format,
  range, enum, length → `NewInvalidFieldFormatError` (1002).
- `entity` factories and `service` functions return these constructors directly (e.g. a
  `NewTransferRequest` that rejects a blank field).
- Persisted failure reasons (`domain.Code*` UPPER_SNAKE constants stored in a DB column) are **not**
  API codes; keep them separate from `Ref`s.
- **`integration/<sys>/gateway.go`** declares the upstream's error vocabulary as plain Go errors —
  sentinels (`var ErrUnavailable = errors.New("inventory: unavailable")`) or typed structs
  (`type RejectedError struct{ ResponseCode string }`). They carry **no catalog code**: the usecase
  decides what they mean.

### Usecase — `internal/core/usecase/<context>/<operation>/exec.go`

**The usecase picks the code**, at the point the decision is made:

```go
func mapReserveError(err error) error {
	switch {
	case errors.Is(err, inventory.ErrOutOfStock):
		return domain.NewOutOfStockError()
	case errors.Is(err, inventory.ErrTimeout):
		return domain.NewInventoryTimeoutError(err)
	default:
		return domain.NewInventoryUnavailableError(err)
	}
}
```

- Map every port error with `errors.Is` / `errors.As` to a domain constructor. A dependency that
  fails or answers unusably → its `8xxx` constructor with the cause; a timeout whose outcome is
  unknown → its `006` constructor.
- Return a domain constructor or an error that already carries a code — **never** a raw `error`,
  `fmt.Errorf` text, or a legacy `stderr.New…Error` (it would render `9001`).
- Log the reason at the boundary (`logger.Context(ctx).Info/Error(…, logger.Err(err))`) before
  returning; the error itself carries no log fields.
- A best-effort side effect (event publish after the outcome is decided) is logged and **not**
  returned — the caller's outcome stands.
- Add the usecase's name to `raisedBy` of every code it raises.

### Driven adapters — `internal/adapters/**`

- **Gateway** (`adapters/gateway/<sys>/http`): translate HTTP status / upstream codes into the
  `integration/<sys>` sentinels or typed errors. Never return a catalog code, never a raw transport
  error without wrapping it in the port's "unavailable" sentinel.
- **Repository** (`adapters/repository/postgres`): wrap every driver error with `NewDBError(err)`
  (→ the DB `8xxx` code). Classify a constraint the caller must branch on
  (`IsDuplicateEntryError` → SQLSTATE `23505`) and let the usecase turn it into a business code.
  `sql.ErrNoRows` on an optional read → `(nil, nil)`; on a required read → the not-found constructor.
- **Event bus** (`adapters/eventbus/kafka`): return the producer error; the usecase decides (usually
  log, not fail).

### Delivery — `internal/delivery/http`

Handlers **never choose a status or write an error body**:

```go
if err := c.ShouldBindJSON(&req); err != nil {
	c.Error(shared.HandleValidationError(err))
	return
}
out, err := h.usecase.Exec(c, in)
if err != nil {
	c.Error(err)
	return
}
```

- Bind / JSON errors go through `shared.HandleValidationError` → `stdresp.FromBind`: empty body →
  `1001`, wrong type → `1002` with the field, anything else → `1002`.
- `middleware.Setup` registers, in this order: correlation id → request id → logging →
  `stdresp.ErrorHandler(catalog)` → recovery. When request audit is enabled, place it after request id
  and before logging. Logging sits **outside** the error handler so every error line carries
  `errorCode` / `responseCode`; recovery turns a panic into `9001`.
- Exception: an inbound partner contract with its own body (e.g. a clearing house's `responseCode`)
  writes that contract directly and does not use this body — document it in `handler.md`.

### Inbound messaging — `internal/delivery/consumer`

A consumer has no HTTP body, but its errors still use catalog codes (log line carries `errorCode`).
Name the consumer in `raisedBy` (`Order Event Consumer`). Retry / commit behavior is decided by the
consumer, not by the code.

### Composition root — `cmd/api`

First thing in `Run`, before any connection is opened:

```go
errorCatalog, err := stderr.LoadCatalog(errorcatalog.JSON())
if err != nil {
	logger.Error("error catalog is invalid", logger.Err(err))
	return fmt.Errorf("load error catalog: %w", err)
}
```

Pass `errorCatalog` down to `router` / `middleware.Setup`. An invalid catalog stops the service.

## Tests

| What | Where | Assert |
|---|---|---|
| constructor → code | `domain/errors_test.go` | `stderr.HasCode(err, domain.ErrX)`; cause kept with `ErrorIs` |
| every `Ref` is in the catalog | `domain/errors_test.go` | `catalog.Require(domain.ErrorRefs()...)` |
| catalog loads | `errorcatalog/embed_test.go` | `LoadCatalog` succeeds |
| usecase rejection | `<operation>/exec_test.go` | `assert.True(t, stderr.HasCode(err, domain.ErrX))` |
| middleware / handler body | `middleware_test.go`, handler tests | full body with `assert.JSONEq` (incl. panic → `9001`) |
| e2e | `tests/e2e/specs/*.e2e.ts` | assert `responseCode`, `errorCode`, `errorMessage` and exactly those 3 keys |

## Adding or changing an error

1. Pick the range and `responseCode` (table above); `8xxx` = one code per dependency.
2. Add the row to `errors.json` with `message` (≤ 255 bytes), `condition`, `raisedBy`.
3. Add the `Ref`, its constructor, and the `Ref` in `ErrorRefs()`.
4. Raise it from the usecase (map the port error); add the usecase to `raisedBy`. A new usecase that
   raises an existing code is added to that code's `raisedBy`.
5. Tests per the table; update the endpoint's `errors` in `docs/api/**` and the Appendix-E table in the
   spec.

## Don'ts

- ✗ `stdresp.GinErrorHandler(serviceID)` or the legacy `stderr.NewBusinessRuleError`,
  `NewResourceNotFoundError`, `NewValidationError`, `NewServiceError`, `NewInternalServerError` — they
  render `9001`.
- ✗ `c.JSON(status, …)` for an error, or `c.AbortWithStatus` — use `c.Error(err)`.
- ✗ A catalog code raised from a gateway adapter — adapters speak the port's vocabulary.
- ✗ Upstream / driver / panic text in the body — it goes to the log via the cause.
- ✗ A constructor nobody calls, or a catalog row without a `Ref` (`TestEveryRaisedCodeIsInTheCatalog` and review catch them).
- ✗ Hand-picking `raisedBy` names for usecases — derive them from the package name.
