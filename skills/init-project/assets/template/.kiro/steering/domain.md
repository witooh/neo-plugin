---
inclusion: fileMatch
fileMatchPattern: "**/internal/core/domain/**"
---

# Domain Layer

`internal/core/domain` is the model. It imports **nothing** from `usecase` or `adapters`.
No HTTP, no SQL, no logging, no framework types — pure business rules. **depguard enforces this**:
transport/persistence/infra packages (`gin`, `net/http`, `database/sql`, `pgx`, `go-redis`, `kafka-go`)
are denied in `domain` (and `usecase`) — the build fails on a regression.

## Split per bounded context — each context owns its ports

The model is **not** one flat package. It is split into one package per bounded context,
and **each context owns the driven ports it consumes** (the ports-and-adapters seam lives
here — there is no central `internal/port/` package).

```
core/domain/
  <context>/                package = folder
    <aggregate>.go          encapsulated aggregate(s) & value objects (private fields, factories, commands)
    <service>.go            stateless domain services (package functions), one file per service
    events.go               domain event definitions (the published contract)
    enums.go                typed string/enum constants — owned by the context that uses them
    errors.go               typed sentinel errors + HTTP-status category
    repository.go           persistence PORT interface(s), domain-owned
    cache.go                driven Cache port (when this context drives a cache)
    eventpublisher.go       driven EventPublisher port (when this context emits events)
    numbergenerator.go      any other co-located driven port
  integration/<sys>/        EXTERNAL read-only domains — one package per upstream
    gateway.go              driven PORT interface + its param/result types (see integration.md)
    readmodels.go           read-models the core consumes (plain data, no behavior)
```

> The package clause is the **context folder name** (`package <context>`). A handler package
> may share that name (`delivery/http/handler/<context>`) — where a file imports both, the
> domain import takes an alias. See `handler.md` / `app.md`.

The concrete contexts (aggregates, value objects, services, co-located ports) for this service
are in `repo-instance.md`.

## Aggregates — fully encapsulated

Fields are **private**. Read through getters; never expose or mutate a field directly.
Construct only through factories; change state only through command methods.

```go
package <context> — the aggregate lives in its context package

// <Aggregate> ... All fields are private: create with New<Aggregate>, reconstitute
// from storage with Restore<Aggregate>, read through getters, mutate through commands.
type <Aggregate> struct {
	id        uuid.UUID
	status    Status
	createdAt time.Time
	// ...
}

// Getters — pointer receiver for entities (mutable identity).
func (a *<Aggregate>) Id() uuid.UUID     { return a.id }
func (a *<Aggregate>) Status() Status     { return a.status }

// New<Aggregate> — creation factory. Sets only the fields the caller supplies; DB-generated
// fields (id, timestamps) stay zero so the DB fills them. Invariants that can fail are
// validated by domain services (RequireX, see below) before construction, so New returns
// just the aggregate. (If a creation invariant must be enforced here, New may return
// (*<Aggregate>, error) instead.)
func New<Aggregate>(p New<Aggregate>Param) *<Aggregate> {
	return &<Aggregate>{status: StatusActive /* ... */}
}

// Restore<Aggregate> — reconstitution factory, REPOSITORY ONLY. Bypasses invariant
// checks (the row was already valid when written). Mirrors every persisted column.
func Restore<Aggregate>(p Restore<Aggregate>Param) *<Aggregate> {
	return &<Aggregate>{id: p.Id, status: p.Status, createdAt: p.CreatedAt /* ... */}
}

// Command methods — the only way to change state. No Set<Field>; name by intent.
func (a *<Aggregate>) Activate(/* ... */) error { /* guard, then mutate */ }
```

Rules:
- **No setters.** Mutation = an intent-named command method that protects invariants
  (`Activate`, `ApplyFinalRate`, `ReplaceSpecialListFlags` — never `SetX`), even for a one-field replace.
- **Persistent state only — no transient field.** An aggregate holds the state that is persisted
  (its identity + invariants), nothing else. A value *resolved during an operation* — from an upstream
  or a computation — that is **not persisted** (response-only, excluded from the cache projection) does
  **not** belong as a field: holding it there forces a setter, and a re-attach hack after the repository
  returns a fresh instance. Return it from the usecase instead (see `usecase.md`; this
  service's worked example is in `repo-instance.md`).
- `New<Aggregate>Param` / `Restore<Aggregate>Param` are exported plain structs (the only exported writable surface).
- A getter that forgets `()` is a method value — it **compiles** but assertions fail at runtime. Always call getters.

### ⚠️ JSON gotcha

Private fields are invisible to `encoding/json` → `json.Marshal` silently yields `{}`.
**Before encapsulating any aggregate, grep for `json.Marshal` / `json.Unmarshal` of it**
(idempotency cache, event payloads). If found, add marshalers that project through the
restore param:

```go
func (a *<Aggregate>) MarshalJSON() ([]byte, error)      { return json.Marshal(a.toRestoreParam()) }
func (a *<Aggregate>) UnmarshalJSON(b []byte) error { /* unmarshal into param → *a = *Restore<Aggregate>(p) */ }
```

Unit tests miss this (stubs don't round-trip); e2e catches it. Rebuild before e2e.

## Value objects

Immutable → **value receiver** getters, factory only (no Restore unless reconstituted
independently, no command methods).

```go
func (v <ValueObject>) Amount() decimal.Decimal { return v.amount }
```

## Domain services — package functions

Logic spanning entities / not owned by one aggregate. **Stateless package functions** —
no `struct{}` receiver, no globals (precompute package-level `var` for constants only).

```go
// Domain services are package functions on the SAME context package as the aggregate
// (one <service>.go per domain service, in the same context package) — pure business logic spanning
// aggregates. Depends only on its context's own types + driven repository port. Never HTTP/log/IO.
package <context>

func RequireUnderAggregateLimit(ctx context.Context, repo <Aggregate>Repository, /* ... */) error {
	// read via the port, decide, return a typed domain error (defined in this context's errors.go)
	return NewLimitExceededError(/* ... */)
}
```

## Driven ports (domain-owned, co-located)

Every outbound contract the context requires lives **in that context package** — the
persistence `repository.go`, plus any `cache.go` / `eventpublisher.go` / `numbergenerator.go`
the context drives, and (for an external system) the `integration/<sys>/gateway.go`. Usecases &
domain services consume them; implementations live in `internal/adapters/...` (see
`repository.md` / `integration.md`). Methods speak in aggregates, not rows.

```go
// repository.go — driven persistence port of the <Aggregate>, in its context package.
// Implemented in internal/adapters/repository/postgres.
package <context>

type <Aggregate>Repository interface {
	GetById(ctx context.Context, id uuid.UUID) (*<Aggregate>, error)
	Create(ctx context.Context, /* ... */) (*<Aggregate>, error)
}
```

The other driven ports follow the same shape, each its own file in the context package —
e.g. `<context>/cache.go` (`Cache`, satisfied by `internal/adapters/repository/cache`),
`<context>/eventpublisher.go` (`EventPublisher`, satisfied by `internal/adapters/eventbus`),
`<context>/numbergenerator.go` (`NumberGenerator`). The gateway ports for external systems
are documented in `integration.md` (`integration/<sys>/gateway.go`).

**Not every injected interface is a domain port.** A *context-free ambient capability* with no
business meaning that every layer consumes identically — the wall-clock, a fresh id — is **not**
co-located here; it is a generic `pkg/` utility (`pkg/clock.Clock`, `pkg/idgen.Generator`, beside
any pure-function domain helper there), injected from `cmd/api` and faked in a `*test` sub-package.
Keep the domain **pure**: a service takes the resolved value (`calculateAge(birthDate string, now
time.Time)` — like `decimal.Decimal`, never a clock service); the **usecase** holds the injected
`clock.Clock` and passes `o.clock.Now()` down. Discriminator: a signature that carries a context's
language → port here; a technical primitive every layer needs the same way → `pkg/` (see
`structure.md`).

## Domain events

Events live in the owning context's `events.go` (e.g. `<context>/events.go` defines
`<Aggregate>Opened`) — exported fields, the published contract.

```go
package <context>
type <Aggregate>Opened struct { /* exported fields — the published contract */ }
```

## Integration read-models (`integration/<sys>`)

An external system is its own read-only context under `integration/<sys>` (package `<sys>`).
It holds the driven port (`gateway.go`, see `integration.md`) and the **read-models** the core
consumes (`readmodels.go` — read-models the core needs from the upstream). These are plain
data the adapter maps the upstream wire DTO into; no behavior.

## Typed errors + HTTP-status category

`errors.go` defines constructors that wrap a cause and carry a category which a single
edge mapper turns into an HTTP status (see `handler.md`). Domain/usecase code returns
these; it never sets status codes itself.

```go
func NewInvalidRequestError(cause error, msg string) error // → 400
func NewNotFoundError(cause error) error                    // → 404
func New<Rule>Error(cause error, msg string) error          // → 409 / 422 …
```

Keep wire/validation concerns out of `domain` — only business meaning lives here.
