---
inclusion: manual
---

# New Feature Checklist

A linear, inside-out procedure for adding a feature. Work **domain → outward**, so each
layer compiles against the one beneath it. Each step links to the layer guide that loads
when you open those files.

## 1. Domain (`domain.md`)
- [ ] Add/extend the **aggregate** (private fields, `New`/`Restore` factories, command methods) or **value object**. No setters.
- [ ] A value resolved during the op but **not persisted** (response-only) → return it from the **usecase**, not as an aggregate field (no transient field + re-attach).
- [ ] If logic spans aggregates → a **domain service** package function (no IO/log).
- [ ] Add **typed errors** (root `errors.go`, package `domain`) for new rejection reasons, each with its HTTP-status category.
- [ ] New persistence need → add a method to the **repository interface** in the centralized `repository` package (`internal/core/domain/repository`, speaks in aggregates).
- [ ] New event → define it in the `event` package (`internal/core/domain/event/events.go`).
- [ ] ⚠️ If the aggregate is `json.Marshal`-ed anywhere (cache/event), add/update `Marshal/UnmarshalJSON`.

## 2. Driven port (`integration.md`)
- [ ] New external dependency → add a narrow interface + its data contracts in its integration context, `internal/core/domain/integration/<sys>/gateway.go`. (A non-gateway driven port — cache / publisher / generator — lives in the centralized `repository` (or `event`) package, e.g. `repository/cache.go`.)

## 3. Repository (`repository.md`)
- [ ] Add the query in `queries/*.sql`; `make db-gen` to regenerate.
- [ ] Implement the new interface method in `postgres/<aggregate>.go`; map rows via `Restore<Aggregate>`; wrap errors with `NewDBError`.
- [ ] Schema change → a **new** migration (never edit a shipped one).

## 4. Usecase (`usecase.md`)
- [ ] Create the package `internal/core/usecase/<context>/<operation>/`.
- [ ] `usecase.go`: `<Op>Usecase` interface (`Exec`) + `Params` + unexported `usecase` + `New(Params) <Op>Usecase`.
- [ ] `exec.go`: implement `Exec`; co-locate request/result models + private helpers; log at the boundary; propagate typed errors. If the op yields a response-only value resolved in-flow, return it alongside the aggregate (`(*Aggregate, <value>, error)`) — don't stash it on the aggregate.

## 5. Gateway adapter (`integration.md`) — only if step 2 added a gateway port
- [ ] Implement the port in `internal/adapters/gateway/<sys>/http` (`NewHTTPAdapter → <sys>.<Upstream>`); map wire DTO → integration type; translate errors.
- [ ] Add a **fake** of the port for tests.

## 6. Inbound adapter (`handler.md` / `messaging.md`)
- [ ] HTTP: add the `<resource>` handler method, `dto.go` (request/response + mapper), `routes.go` (`Register`). Use a `UC`-suffixed field if it would collide with the method name.
- [ ] Event-driven: add the case in the consumer `processor` + the `eventid` enum; map the transport DTO to usecase inputs.

## 7. Wiring (`cmd/api`, `app.md`)
- [ ] In `cmd/api/http.go` `buildHandlers` (or `consumer.go`): construct the usecase via `New(Params{...})` and inject it into the handler/processor. Import the centralized `repository` / `event` ports it needs (alias only integration packages whose name collides with a handler — e.g. `dm<sys>`).
- [ ] `cmd/api/adapters.go`: construct any new outbound adapter (returns a port interface).
- [ ] Register the route: add a `register<Resource>` (or extend one) in `internal/delivery/http/router` and wire the handler into `router.Handlers` (see `handler.md`).

## 8. Config (`app.md`)
- [ ] Add config fields for any new dependency; pass them via the adapter's `Config` (don't read globals inside the adapter).

## 9. Tests (`testing.md` unit · `e2e.md` e2e + stubs)
- [ ] Unit: table tests for the usecase + domain logic against stubs/fakes/mocks (cover rejection paths).
- [ ] E2e: a spec arranging the upstream stub, calling the endpoint, asserting the envelope + side effects.

## 10. Tooling + verify (`tooling.md`)
- [ ] `make mock-gen` if a mocked interface changed.
- [ ] Gates green: `gofmt`/`goimports` clean · `go build ./...` · `go vet` · `golangci-lint` (≤ baseline) · `make test`.
- [ ] `make compose-up` **then** `make test-e2e` (rebuild first).

## 11. API collection (`bruno.md`) — optional
- [ ] Add a request file under `bruno/<resource>/`; update `openapi.yaml`.
