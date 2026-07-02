---
inclusion: manual
---

# Repo instance — neo-service

The generic steering guides describe the **pattern**; this file holds the **neo-service
instance** they point to — its real bounded contexts, driven ports, and any decomposed
operation's case-study. Reuse: a new service rewrites *this* file; every other steering file
copies across unchanged (they carry no repo names).

> **Status: freshly scaffolded.** This service has **no bounded contexts yet** — it builds and
> serves `GET /health` only. The first `neo` domain run fills in the sections below as it adds
> the first aggregate, ports, and usecase. Until then they are intentionally empty.

## Bounded contexts (`structure.md`, `domain.md`)

_None yet._ neo builds the model **per technical layer** under `internal/core/domain/` — aggregates
& value objects in `entity/`, domain services in `service/`, driven persistence/cache ports
**centralized** in `repository/`, event-bus ports + event definitions in `event/`, and typed enums /
errors in the root `enums.go` / `errors.go` (package `domain`). Each bounded context contributes its
types across those layer packages; its usecases live under `internal/core/usecase/<context>/<operation>/`.
External read-only upstreams stay one-package-per-upstream under `internal/core/domain/integration/<sys>/`.

## Driven ports (`app.md`)

_None yet._ As the model grows, list the centralized ports here — persistence/cache in `repository`
(e.g. `repository.<Aggregate>Repository`, `repository.Cache`), event-bus in `event`
(`event.EventPublisher`), and each external gateway under `integration/<sys>` (`<sys>.<Upstream>`).

## Decomposed operations (`usecase.md`, `testing.md`)

_None yet._ When an operation grows past one head, record its sub-package split here
(`shared/`, `validation/`, branch openers, …) so the case-study stays discoverable.

## Infrastructure (wired, dormant)

The skeleton ships the infrastructure every service needs, ready for the first domain:

- **Postgres** — `internal/adapters/repository/postgres` (sqlc `db.go` + `transactor` /
  `utilities` / `dberror`); `cmd/api` dials it best-effort so `/health` serves without it.
- **Redis / Valkey** — `internal/adapters/repository/{redis,cache}` + `pkg/cache/valkey`.
- **Kafka** — `pkg/lib/kafka` generic producer/consumer primitives; no topics until a domain
  publishes or consumes (see `messaging.md`).
- **Ambient capabilities** — `pkg/clock`, `pkg/idgen` (+ their `*test` fakes).

## Placeholder values (`structure.md` table)

| Placeholder | This repo |
|---|---|
| `{{MODULE_PATH}}` | `example.com/neo/service` |
| `{{SERVICE_NAME}}` | `neo-service` (service id `NEOSVC`) |
| `<context>` / `<operation>` | _(none yet — neo fills these on the first domain)_ |
| `<Aggregate>` | _(none yet)_ |
| `<Upstream>` | _(none yet)_ |
