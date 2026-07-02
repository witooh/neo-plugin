---
inclusion: fileMatch
fileMatchPattern: "**/internal/core/domain/**"
---

# Domain Layer

`internal/core/domain` is the model. It imports **nothing** from `usecase` or `adapters`.
No HTTP, no SQL, no logging, no framework types — pure business rules. **depguard enforces this**:
transport/persistence/infra packages (`gin`, `net/http`, `database/sql`, `pgx`, `go-redis`, `kafka-go`)
are denied in `domain` (and `usecase`) — the build fails on a regression.

## Split per technical layer

The model is split into one package per **technical layer** (stereotype), shared across every
bounded context — **not** one package per context. Driven ports are **centralized** in
`repository/` (plus `event/` for event-bus ports); external-system gateways are the one
exception and stay under `integration/<sys>/`.

```
core/domain/
  enums.go                  package domain — ALL typed string/enum constants (one flat root file)
  errors.go                 package domain — typed sentinel errors + HTTP-status category (root, when needed)
  entity/                   package entity — ALL domain data types: aggregates + their component
                            value objects + computed results + read-models (private fields, factories, commands)
  service/                  package service — stateless domain services (package functions), one file per service
  repository/               package repository — ALL driven persistence ports (one interface per file);
                            prefix names to keep them distinct (<contextA>_dailyamount.go, <contextB>_dailyamount.go)
  event/                    package event — EventPublisher & other event-bus ports + domain event definitions
  integration/<sys>/        EXTERNAL read-only domains — one package per upstream (UNCHANGED)
    gateway.go              driven PORT interface + its param/result types (see integration.md)
    readmodels.go           read-models the core consumes (plain data, no behavior)
```

> The package clause is the **layer folder name** (`package entity` / `service` / `repository` /
> `event`; the root `enums.go` / `errors.go` are `package domain`). Cross-layer refs inside the
> domain are qualified — `entity` imports `domain` for enums; `repository` / `event` / `service`
> import `entity` for the aggregates & value objects they speak in. `integration/<sys>` keeps one
> package per upstream. Dependency order is acyclic: `domain` ← `entity` ← {`repository`, `event`, `service`}.

The concrete aggregates, services, and ports for this service are in `repo-instance.md`.

## Aggregates — fully encapsulated

Fields are **private**. Read through getters; never expose or mutate a field directly.
Construct only through factories; change state only through command methods.

```go
package entity — aggregates, value objects & read-models all live in the entity package

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
  (`Activate`, `ApplyFinalRate`, `ReplaceStatusFlags` — never `SetX`), even for a one-field replace.
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
// Domain services are package functions in the `service` package (one <service>.go per service) —
// pure business logic spanning aggregates. Depends only on entity types + driven ports. Never HTTP/log/IO.
package service

func RequireUnderAggregateLimit(ctx context.Context, repo repository.<Aggregate>Repository, agg *entity.<Aggregate> /* ... */) error {
	// read via the port, decide, return a typed domain error (constructor from package domain)
	return domain.NewLimitExceededError(/* ... */)
}
```

## Driven ports (centralized in `repository/` + `event/`)

All driven ports the core consumes live in the central `repository/` package — persistence
repositories, caches, number generators — one interface per file, referencing `entity` types.
Event-bus ports live in `event/`. External-system gateways are the exception: they stay in
`integration/<sys>/gateway.go` (see `integration.md`). Usecases & domain services consume these
ports; implementations live in `internal/adapters/...` (see `repository.md` / `integration.md`).
Methods speak in aggregates, not rows.

```go
// repository/<aggregate>.go — a driven persistence port, in the central repository package.
// Implemented in internal/adapters/repository/postgres.
package repository

import "{{MODULE_PATH}}/internal/core/domain/entity"

type <Aggregate>Repository interface {
	GetById(ctx context.Context, id uuid.UUID) (*entity.<Aggregate>, error)
	Create(ctx context.Context, /* ... */) (*entity.<Aggregate>, error)
}
```

Other driven ports follow the same shape: `repository/cache.go` (`Cache`, satisfied by
`internal/adapters/repository/cache`), `repository/<x>.go` (`NumberGenerator`), and
`event/eventpublisher.go` (`EventPublisher`, satisfied by `internal/adapters/eventbus`). When two
contexts drive a similarly-named port, prefix the file (`repository/<contextA>_dailyamount.go`,
`repository/<contextB>_dailyamount.go`). External-system gateway ports remain in
`integration/<sys>/gateway.go`.

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

Domain event definitions live in the `event` package (`event/events.go`), alongside the
event-bus ports — exported fields, the published contract.

```go
package event
type <Aggregate>Opened struct { /* exported fields — the published contract */ }
```

## Integration read-models (`integration/<sys>`)

An external system is its own read-only context under `integration/<sys>` (package `<sys>`).
It holds the driven port (`gateway.go`, see `integration.md`) and the **read-models** the core
consumes (`readmodels.go` — read-models the core needs from the upstream). These are plain
data the adapter maps the upstream wire DTO into; no behavior.

## Typed errors + HTTP-status category

Typed errors live in a root `errors.go` (`package domain`, beside `enums.go`): constructors that
wrap a cause and carry a category which a single edge mapper turns into an HTTP status (see
`handler.md`). Domain/usecase code returns these; it never sets status codes itself.

```go
func NewInvalidRequestError(cause error, msg string) error // → 400
func NewNotFoundError(cause error) error                    // → 404
func New<Rule>Error(cause error, msg string) error          // → 409 / 422 …
```

Keep wire/validation concerns out of `domain` — only business meaning lives here.
