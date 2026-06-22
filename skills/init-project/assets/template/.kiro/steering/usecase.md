---
inclusion: fileMatch
fileMatchPattern: "**/internal/core/usecase/**"
---

# Usecase Layer

Application services that orchestrate **one operation**. They depend on `core/domain` and on
the **port interfaces** it needs — each imported from the **domain context that owns it**
(`<context>.<Aggregate>Repository`, `<context>.Cache`, `<upstream>.<Upstream>`, …; there is no
central `internal/port/` package). Never on a concrete adapter, never on another
usecase.

## One operation = one package

```
internal/core/usecase/<Domain>/<operation>/  # <operation> = snake_case of the method, e.g. cancel_order
    usecase.go                            # the CONTRACT (interface + Params + struct + New)
    exec.go                               # the IMPLEMENTATION (Exec + helpers + co-located models)
```

- Folder name = `snake_case(<Op>)`. The package clause is the folder name verbatim
  (underscores are fine — the lint set enables no naming rule).
- The interface is `<Op>Usecase`; the method is always `Exec`.
- Shared helpers used by several operations of one domain go in `<Domain>/shared/`.

## `usecase.go` — the contract (always this shape)

```go
// Package <operation> implements the <Op> use case of the <Aggregate>.
package <operation>

// <Op>Usecase is the inbound port for the <Op> handler; *usecase satisfies it.
type <Op>Usecase interface {
	Exec(ctx context.Context, /* inputs */) (/* result, */ error)
}

// Params holds the dependencies of the use case. Each port is imported from the domain
// context that owns it (e.g. "{{MODULE_PATH}}/internal/core/domain/<context>").
type Params struct {
	Repo <context>.<Aggregate>Repository
	// <Upstream>Adapter <sys>.<Upstream>   // add driven ports as needed (from integration/<sys>)
}

// usecase is the unexported application service. Construct it with New.
type usecase struct {
	Repo <context>.<Aggregate>Repository
}

// New builds the use case from its dependencies.
func New(p Params) <Op>Usecase {
	return (*usecase)(&p)
}
```

`usecase` and `Params` must have **identical fields** so `(*usecase)(&p)` compiles.
`New` returns the **interface**, so callers (handlers, the composition root) depend on
the contract, not the struct.

### Narrow dependency interfaces (ISP)

When the operation needs only a slice of a wide port, declare a **local** narrow
interface in `usecase.go` and accept that in `Params`. The full adapter satisfies it
structurally — no wiring change.

```go
// <X>Reader is the slice of <sys>.<Upstream> this operation needs.
type <X>Reader interface {
	Lookup(ctx context.Context, id string) (*<sys>.<Upstream>Data, error)
}
type Params struct { Adapter <X>Reader }
```

## `exec.go` — the implementation

```go
package <operation>

func (u *usecase) Exec(ctx context.Context, rawId string /* ... */) (/* ... */ error) {
	logger.Info("<op> start", logger.String("id", rawId))

	id, err := shared.ParseId(rawId)
	if err != nil {
		return err
	}
	acc, err := u.Repo.GetById(ctx, id)
	if err != nil {
		return err
	}
	if err := acc.SomeCommand(/* ... */); err != nil {
		return err
	}
	return u.Repo.Save(ctx, acc)
}
```

Rules:
- **`ctx` is the first parameter** and is threaded into every port/repo call.
- **Models co-locate.** Request/result structs that belong to this operation live in
  `exec.go` (or a sibling file in the package), not in a shared models package.
- **Return resolved-at-op values; don't smuggle them through the aggregate.** When an operation
  produces an aggregate **plus** a response-only value resolved during the flow (from an upstream or a
  computation) that is **not persisted**, return it alongside the aggregate —
  `Exec(...) (*<Aggregate>, <value>, error)` — rather than stashing it on the aggregate as a transient
  field. The aggregate carries persistent state only (`domain.md`); a transient field forces a setter and
  a re-attach after the repo round-trip.
- **Private helpers** for this operation live here too.
- **Logging happens at the usecase boundary**, not in `domain`. Log the decision /
  rejection reason; let typed domain errors carry the rest.
- **Error wrapping:** pass domain/port errors through unchanged so the edge mapper can
  categorize them; wrap with `fmt.Errorf("...: %w", err)` only to add context, never to
  flatten a typed error into a string.

## Multi-port operations

A complex operation (e.g. placing an order) lists every dependency as a `Params`
field and orchestrates them in `Exec`, delegating business decisions to `domain` /
`domain/service` and side effects to ports. The package shape is unchanged — still
`usecase.go` (contract) + `exec.go` (+ extra impl files split by step).

## Splitting impl files — earn the split

A complex operation may split `exec.go` into step files — but each split must **earn
its place** as a distinct step of the flow, and folds back when it stops:

- A file holding a **single helper with a single caller** folds into that caller's file.
- Co-locate a concern's pieces — the function that orchestrates a concern lives with
  the helpers it drives (e.g. background-document assembly sits with its task builders).
- Pull a self-contained mechanism (idempotency, cache plumbing, retry) out of
  `exec.go` into its own concern file (e.g. `idempotency.go`) when inlining it would
  bury the `Exec` orchestration — `exec.go` should read as the flow, not the plumbing.
- Keep a split only when it isolates a genuine step a reader would look for by name
  (the validation gate, a dispatch branch, …).

## Decompose a large operation into sub-packages

When file-splitting is no longer enough — a `usecase` struct with **many ports** that every
method can reach (no boundary), a flow that **dispatches to branches** (one per variant),
tests that must mock a dozen deps to exercise one concern — promote the step files
to **sub-packages by concern**. The operation package becomes a thin orchestrator over
cohesive components.

```
internal/core/usecase/<Domain>/<operation>/
    usecase.go        # contract: interface + Params (raw ports) + slim struct (components only) + New (wires)
    exec.go           # orchestrator: gate → validator checklist → dispatch (reads as the flow)
    shared/           # tiny stateless helpers reused across sub-packages (no sibling deps)
    validation/       # Validator{ports}        — RequireX gate checks
    idempotency/      # Guard{cache, repo}      — FindExisting / CacheOpened / HandleDuplicate
    documents/        # Service{port}           — fire-and-forget side effect
    <branchA>/        # Opener{Deps}            — one branch (open.go / campaign.go / gateway.go)
    <branchB>/        # Opener{Deps}            — the other branch
```

The decomposed operation for this service (its sub-packages + branch openers) is in
`repo-instance.md`.

Rules:
- **One sub-package = one component struct** (`Validator`/`Guard`/`Service`/`Opener`) holding
  **only the deps it uses**, built by a constructor. Few deps → `NewX(a, b)`; many → a `Deps`
  struct (`NewOpener(Deps{...})`) so the call site reads by name.
- **The orchestrator struct holds only components** (`{idempotency, validator, <branchA>, <branchB>}`),
  never raw ports. `New` builds the **shared** components as locals (documents, idempotency,
  validator) and injects the **same instance** into each branch opener's `Deps`; `Exec` reads
  as a checklist (`u.idempotency.FindExisting` → `u.validator.RequireX…` → `u.<branch>.Open`).
- **External surface is unchanged.** The inbound interface and `New(Params)` keep their
  signatures — `Params` still lists the raw ports the caller injects; `cmd/api` wiring and
  mocks don't change. (`New` is no longer `(*usecase)(&p)` — it constructs components.)
- **Imports point inward only; a child never imports the parent.** parent → every sub-package;
  branch/opener → `shared`/`validation`/`idempotency`/`documents`. A side effect used by the
  branch openers (documents, idempotency) **must be its own sub-package**, not a flat file in
  the parent — a flat file forces `branch → parent` and cycles.
- **Constructors guarantee non-nil components** → no nil-receiver guards (`if g == nil`), they
  are dead code; guard the *configured-absent* case via the field the constructor stored (`if g.cache == nil`).
- **Cut dead deps** while here — a port in `Params` used by no flow is removed from `Params` +
  the struct + the `cmd/api` field (verify no other consumer first).

## Don'ts

- ✗ A second exported method besides `Exec`. New behavior = new package.
- ✗ Exposing the `usecase` struct, or returning it from `New`.
- ✗ Importing another usecase package, a handler, or a concrete adapter.
- ✗ HTTP status codes, gin types, or SQL here — those belong to the adapters.
