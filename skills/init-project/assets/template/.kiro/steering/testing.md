---
inclusion: fileMatch
fileMatchPattern: "**/*_test.go"
---

# Testing

This guide covers the **Go unit/property tests** next to the code. Black-box e2e and the
upstream stubs are their own guide — see `e2e.md`. Unit tests prove logic against
mockery-generated mocks of the driven ports; e2e proves the wired service against stubbed
upstreams.

## Unit tests — Go

- **Table-driven**, `t.Run(name, ...)` per case. Cover the rejection paths (`stderr` typed
  errors — `errors.As` onto `stderr.StandardError` / `errors.Is` through `Unwrap`), not just
  the happy path.
- **Mock every driven port with its mockery-generated mock** (`mockPKG.NewMockXxx(t)`; see
  `tooling.md` for regen). `NewMockXxx(t)` registers `AssertExpectations` via `t.Cleanup`, so the
  expectations *are* the assertions:
  - **Arm only the calls a path makes** — `m.EXPECT().Method(args).Return(...)`. A port that must
    **not** be called gets **no expectation** (the mock fails if it is touched) — this replaces a
    `t.Fatal` guard or a `called` bool.
  - **Assert arguments through the matcher**, not a captured field — pass the exact expected value
    (`mock.Anything` for ctx / computed / uninteresting args). For same-args-different-returns
    across calls, chain ordered `.Once()` expectations (testify matches FIFO).
  - **Capture a complex emitted request** with `.Run(func(_ context.Context, req T){ captured = req })`
    then assert fields of `captured`.
  - **Ambient capabilities are the exception** — `clock` / `idgen` use their hand-written test
    stubs (`clocktest.NewStub`, `idgentest.NewStub`), never a generated mock (see `app.md`).
  - A no-op path that takes `nil` for a port passes `nil`, not a mock.
- **Construct the unit under test through its real constructor** where it returns an interface (`<operation>.New(<operation>.Params{Repo: mockRepo})`); use a struct literal (`&usecase{...}`) only inside the package's own tests.
- **Domain aggregates in tests**: build via `New<Aggregate>` / `Restore<Aggregate>`, assert via getters — **always call the getter** (`a.Status()`, not `a.Status`; the latter compiles as a method value and the assertion fails at runtime).

```go
func TestExec(t *testing.T) {
	cases := []struct{ name string; in Input; wantErr error }{ /* ... */ }
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			repo := mockPKG.NewMockRepo(t)
			repo.EXPECT().Method(mock.Anything, mock.Anything).Return(/* ... */, nil)
			uc := <operation>.New(<operation>.Params{Repo: repo})
			_, err := uc.Exec(context.Background(), tc.in)
			require.ErrorIs(t, err, tc.wantErr)
		})
	}
}
```

### One test file per source file (mirror naming)

Split a package's tests to **mirror the source files they cover** — never one giant
`*_test.go`:

- **Every test file mirrors a source file** — named for the source whose behavior it
  covers (`exec.go` → `exec_test.go`, a `validate.go` step file → `validate_test.go`).
  **Never** name a test file after a concept with no matching source (e.g.
  a feature- or ticket-named `<concept>_test.go`); there is no standalone
  shared-helpers file.
- Route each test to the file that **owns the behavior under test**, even when the
  test drives it through `Exec`: a rejection test exercises the step file that owns the
  rule (a `validate.go` compliance gate → `validate_test.go`). When a flow dispatches to
  branch files, branch-specific tests live with their branch. (Once an operation grows
  into sub-packages, this same routing crosses package boundaries — see the next section.)
- **Shared fixtures/builders live with the tests that use them**, not in a standalone helpers
  file. A data fixture or mock-builder helper (`passingGateway(t)`, `baseFixture()`) used by
  **one** test file lives in that file; one used by **two or more** lives in `exec_test.go` (the
  entry-point test), which every file reaches through package scope. (The mocks themselves are the
  shared generated ones under `internal/mocks`; only the per-test arming/fixtures are local.) This
  keeps every test file a real source mirror.
- One test per scenario — don't keep parallel or stale test families for the same
  behavior (e.g. an old `TestCreate*` set beside a renamed `TestOpen*`); dedup to the
  current operation's naming.
- `usecase.go` (interface + `New`) has no test of its own; its behavior is covered by
  `exec_test.go`.

### Mirror across sub-packages — test each component's exported API

When an operation is decomposed into sub-packages (see `usecase.md`), the mirror rule applies
**per package**, and "drive through `Exec`" no longer reaches a sub-package — a sub-package
test **cannot import the parent** (it would cycle). So:

- **Each sub-package owns its tests**, mirroring its source files (`<branchA>/open.go` →
  `<branchA>/open_test.go`, `<branchA>/<step>.go` → `<step>_test.go`). When a package splits
  across several source files (`<pkg>/<a>.go` + `<pkg>/<b>.go`), mirror **each** (`<a>_test.go`
  + `<b>_test.go`) — a package-named `<pkg>_test.go` mirrors no source file and is the same
  anti-pattern as a concept-named test. Test the package's
  **exported API directly** — `Opener.Open`, `Validator.RequireX`, `Guard.FindExisting` —
  built via the package's real constructor with mocks; never reach back to the parent's `Exec`.
- **Route by behaviour owner across packages**: a rejection test for a validator rule exercises
  `Validator.RequireX` → `validation/<rule>_test.go`, NOT the `<branchA>` opener that calls it;
  a branch-specific test → `<branchA>/<step>_test.go`. A gate the orchestrator runs **once**
  (e.g. shared compliance checks) is tested **once** against the `Validator` — collapse
  historical per-branch duplicates (the same case re-asserted through both branch paths) onto
  that single owner.
- **Mock-builder helpers duplicate per package** (the "no shared-helpers package" rule, now per
  package): a sub-package's `passingX(t)` mock-builders live in its own entry-point test file (the
  opener's `open_test.go`, the validator's `<rule>_test.go`). Build the real sibling components a
  flow needs from mocks (`validation.NewValidator(mockGateway, ...)`).
- **The orchestrator's `exec_test.go` tests orchestration only** — the idempotency gate, that
  the compliance gate precedes dispatch, and variant-field dispatch — driving
  `New(Params{mocks}).Exec` (`New` returns the inbound interface, so no cast is needed). Assert
  dispatch by **which port the branch hits** (`<branchA>` → `Gateway.MethodA`, `<branchB>` →
  `Gateway.MethodB`), not by re-checking branch internals. A
  `newTestUsecase(p) *usecase { return New(p).(*usecase) }` cast is only for a rare white-box
  field tweak — a fully decomposed orchestrator needs none.
- **Test the exported surface, not private functions.** A white-box test that called an
  unexported helper is rewritten onto the exported method that now owns it, in the package
  that owns it.

The decomposed operation for this service (branches, validator method, compliance cases,
dispatch ports) is in `repo-instance.md`.

### In-package vs external tests

- `package <pkg>` (white-box): can touch unexported types — use for `&usecase{}` literals and mock wiring.
- `package <pkg>_test` (black-box): exercises only the exported surface.

### Property tests

For algorithmic code (number generation, allocation), use a property-based runner
(`pgregory.net/rapid`) to assert invariants across generated inputs (uniqueness,
ordering, no collisions) rather than enumerating cases.

## What to test where

| Concern | Tier |
|---|---|
| Domain rules, usecase orchestration, mappers | Go unit |
| Algorithmic invariants | Go property |
| Wiring, routing, error→status mapping, serialization round-trips | E2e |

## Don'ts

- ✗ Asserting on a getter without `()` (compiles, fails at runtime).
- ✗ Hitting a real upstream from a test — stub it.
- ✗ Over-mocking domain logic — test it directly; mock only ports.
- ✗ Mocking an ambient capability (`clock` / `idgen`) — use its test stub instead.
- ✗ Arming an expectation for a call a path never makes — arm only what's hit (an unwanted call should fail by having no expectation).
