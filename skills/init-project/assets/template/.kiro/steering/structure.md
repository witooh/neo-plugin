---
inclusion: always
---

# Project Structure — Hexagonal / DDD Go Service

This is the **primary, self-contained guide** for working in this codebase and any
service that adopts this layout. Read it first. Per-layer guides load automatically
when you open files in their layer (see the index at the bottom) — you should not
need to open source to learn a pattern; the steering carries verbatim-shaped skeletons.

## Working principles (MUST)

Cross-cutting rules for **how to work in this repo** — distinct from the architectural
invariants below (which govern the code). Treat them as iron rules: don't ignore, skip, or
reinterpret them on your own. Before any non-trivial action, stop and review which apply.

- **Honesty over agreement.** Answer with truth and reasoning, not what the user wants to
  hear. Don't soften or hide facts; don't compliment without basis. Hold your position while
  the evidence stands — yield to better evidence or reasoning, never to social pressure.
  Debate freely on facts, but **execute the user's instruction even when you disagree**
  (raise the concern first, then comply).
- **Never guess, never decide unilaterally.** Unsure about anything — scope, a name, an
  approach — **ask the user first** instead of inventing an answer. For an undocumented
  architectural pattern this is already the "stop, ask, fold it back" rule below.
- **Distrust your own output until verified.** Treat every artifact (code, analysis,
  recommendation, config, comparison) as untrustworthy until proven by concrete evidence —
  confidence comes from verification, not from re-reading your reasoning. By priority:
  1. **Run it** — tests, linter, `go build` / `go vet`, dry-run; if a command can prove it, run it.
  2. **Read it back** — re-read the file/source to confirm the change actually landed.
  3. **Compare to the source of truth** — code, specs, steering, prior results, the
     conversation; check the new output doesn't contradict established evidence.
  4. If nothing can verify it → **ask the user** before presenting.
  Found an issue? Fix and re-verify until clean. Never present unverified output.
- **Plan complex work before building.** For anything complex (multi-file changes,
  architectural decisions, > 3 steps), explore the approach with the **`brainstorm` skill**
  first, then use the **Plan agent** (`/plan`, or `Shift+Tab`) to break it into a plan before
  implementing — except under the **`neo`** workflow (`/neo`), which runs its own phases.
- **Keep output terminal-friendly** — concise and easy to scan.

## Placeholders

Code skeletons use placeholders — substitute your service's names. Examples use a neutral
`Order` domain throughout; **no per-layer guide names a real type, context, or operation** of
the service it documents.

| Placeholder | Meaning | Source | Example |
|---|---|---|---|
| `{{MODULE_PATH}}` | Go module path | the `module` line in `go.mod` | `example.com/org/<service>` |
| `{{SERVICE_NAME}}` | short service name | tracer / container / config | `<service>` |
| `<context>` | **lowercase** bounded-context name — the folder shared by `usecase/<context>/` and `delivery/http/handler/<context>` (domain is per-layer, not `domain/<context>`; never PascalCase like `Order`) | — | `order`, `billing` |
| `<Aggregate>` | an aggregate / entity | — | `Order`, `LineItem` |
| `<Upstream>` | an external system | — | `Payment`, `Inventory` |
| `<operation>` | snake_case usecase package | — | `cancel_order` |
| `<Op>` | PascalCase of `<operation>` | — | `CancelOrder` |

**The repo instance is one file.** The real bounded contexts, driven ports, the decomposed
operation's case-study, and these placeholders' concrete values for **this** service live in
`repo-instance.md` (a `manual` guide); every other guide is generic and points there for real
names. **To reuse this steering in another service: copy all guides unchanged and rewrite
`repo-instance.md`** — the one exception is the literal stub-directory glob in `e2e.md`'s
`fileMatchPattern` and the index below, which tracks your stub tool's directory.

Shared org infrastructure (`common-lib`: `logger`, `stderr`, `stdresp`, `ctxutils`,
`middleware`) is assumed present; its import paths are kept verbatim in examples.

## Layout

```
cmd/api/                          COMPOSITION ROOT (package main) — wires concretes to interfaces
  main.go                         thin entry point → MustLoad + Run(ctx, cfg)
  app.go http.go consumer.go      build + wire adapters, repositories, usecases, handlers
  adapters.go
config/                           CONFIGURATION (package config) — typed config + loader, beside config.yaml
  config.go                       typed Config struct + Load/MustLoad + env/file loader
  config.yaml                     runtime config values (mounted into the container)
internal/
  core/                           THE CORE — domain + application logic (depends on nothing outward)
    domain/                       THE MODEL — split per technical layer (one package per stereotype)
      enums.go errors.go          package domain — typed enums + typed errors (flat root files)
      entity/                     package entity — aggregates + value objects + computed results + read-models
      service/                    package service — domain services (stateless package functions)
      repository/                 package repository — ALL driven persistence ports (centralized, one per file)
      event/                      package event — EventPublisher + domain event definitions
      integration/<sys>/          EXTERNAL read-only domains — one package per upstream (e.g. product)
                                    gateway.go         driven PORT interface + its param/result types
                                    readmodels.go      read-models the core consumes (plain data)
    usecase/<context>/<operation>/ ONE operation per package → usecase.go + exec.go
  delivery/                       DRIVING ADAPTERS — receive input, call a usecase
    http/                         inbound HTTP (gin)
      handler/<resource>/         handler.go (struct+New) + one file per operation
      dto/                        response DTOs + mappers (resource-prefixed names)
      middleware/                 standard gin middleware chain (wraps common-lib)
      router/                     New(Handlers, serviceID) + one route file per resource
    consumer/                     inbound messaging (Kafka processor)
  adapters/                       DRIVEN ADAPTERS — implement / call a driven port
    eventbus/kafka/               messaging infra: producer, consumer (low-level client glue)
    gateway/<sys>/                outbound HTTP adapters → implement integration/<sys> ports
    repository/postgres/          outbound persistence (sqlc): migrations, queries, seed, sqlc
    repository/redis/             low-level Redis client
    repository/cache/             cache adapter → implements repository.Cache (Redis-backed)
  mocks/                          generated test doubles (mockery): domain/{repository,event}, gateway, eventbus
pkg/                              shared low-level libraries (no domain logic) — tested in isolation
  messaging/                      Kafka WIRE CONTRACT shared by inbound (delivery) + outbound (adapters):
    eventid/ models/ schema/        routing ids · Avro models · .avsc — in pkg/ so neither layer crosses the other
  clock/ idgen/                   AMBIENT-CAPABILITY ports (current time · fresh id) — context-free primitives
                                    every layer injects: interface + System() impl + a *test fake. NOT domain
                                    driven ports (see "Ambient capabilities" under the dependency rule).
```

The concrete bounded contexts, `integration/<sys>` upstreams, and `pkg/` helpers for this
service are in `repo-instance.md`.

## The dependency rule (the one rule that governs everything)

Imports point **inward only**: `delivery / adapters → usecase → domain`. An inner layer must
never import an outer one.

- **`core/domain`** imports nothing from `usecase` / `adapters`. It is split by **technical
  layer**: `entity` (data types), `service` (domain services), `repository` (ALL driven
  persistence ports, **centralized**), `event` (event-bus ports + event defs), root `enums.go` /
  `errors.go` (`package domain`), plus `integration/<sys>` (external gateways + read-models). Inside
  the domain, refs are acyclic: `domain` ← `entity` ← {`repository`, `event`, `service`}. The **one
  exception to centralized ports is `integration/<sys>/gateway.go`** — external-system ports stay
  per-upstream.
- **Ambient capabilities are the exception.** A *context-free technical primitive* every layer
  consumes identically, with no business semantics in its signature — the wall-clock
  (`clock.Clock`), a fresh id (`idgen.Generator`) — is **not** a driven port and is **not**
  co-located: it lives in `pkg/` (beside any pure-function domain helper there), with its own
  small interface + a `System()` constructor wired from `cmd/api`, faked in a `*test` sub-package.
  The test: does the contract speak a context's language, driven by one context (→ a domain
  port), or is it a primitive every layer needs the same way (→ `pkg/`)? Repository / Cache /
  EventPublisher / Gateway / NumberGenerator are ports; clock & id-generation are `pkg/`. **Domain
  stays pure** — a domain service takes the resolved value (`now time.Time`, the way it takes
  `decimal.Decimal`, never a clock service); only the **usecase** holds the injected port and
  reads `.Now()` / `.NewString()` at the boundary.
- **`core/usecase`** depends on `core/domain` + the port **interfaces** it needs — imported
  from the centralized `repository` / `event` packages (`repository.<Aggregate>Repository`,
  `repository.Cache`, `event.EventPublisher`) plus each `<upstream>.<Upstream>` from
  `integration/<sys>`. Never on a concrete adapter, never on another usecase.
- **Cross-capability collaboration goes through a consumer-defined port.** When one usecase needs another
  capability's operation, it does **not** import that usecase and there is **no** central
  driving-port package. The **consuming** side declares a narrow, consumer-defined port in
  `core/domain/repository` (or `event`, expressed in the language it needs); an **adapter**
  satisfies that port over the providing capability, wired at the composition root (`cmd/api`, the
  only importer of usecases). The seam is a port like every other outbound dependency — never a
  usecase→usecase import.
- **`delivery`** (HTTP handler / Kafka consumer) *calls* a usecase — it translates transport ↔ usecase
  and lives at top level, a sibling of `adapters` (deliberately **not** nested under it).
- **`adapters`** *implements* a driven port (repository / gateway / cache / producer).
  **Delivery packages and adapters never import each other** — the one exception is
  `delivery/http/router`, the HTTP-composition sub-layer (like `cmd/api` but scoped to
  routing), which imports the handler packages to wire routes. Handlers still never import each other.
- **`cmd/api`** is the **only** package that imports concrete adapters + usecases and wires
  them together. Everywhere else programs to interfaces.
- **Interfaces live where they are consumed** (the inner layer); implementations live
  in the outer layer. This is the ports-and-adapters seam.

If a change needs an inner layer to import an outer one, the design is wrong — revisit
before coding.

## When a pattern isn't in the steering (stop — don't improvise)

These guides describe every pattern this codebase sanctions. If the work in front of you
**fits none of them** — a layout the guides don't show, a case the skeletons don't cover,
or a rule you'd have to bend to proceed — treat it as a gap in the design, **not** a
decision you're free to make on your own.

1. **Stop before writing code.** Do not invent an approach and implement it. A pattern
   absent from steering is unverified against this architecture; improvising one risks
   silently diverging from the agreed design.
2. **Surface it to the user and ask.** State plainly that you hit a pattern the steering
   doesn't cover, show the specific case, and ask how they want it handled. Do not pick an
   approach for them.
3. **Fold the decision back into the central steering.** Once the user decides, the new
   pattern must be written into the steering guide that owns that layer (and `structure.md`
   if it's cross-cutting) so it becomes the documented norm — tell the user this steering
   update is needed and treat it as part of finishing the work. Never leave a new pattern
   living only in code.

Steering is the source of truth: an undocumented pattern is a gap to close *with the user*,
not a license to guess.

## Layers at a glance

| Layer | Path | Responsibility | May import |
|---|---|---|---|
| Domain | `internal/core/domain/**` | Business rules, invariants, aggregates, domain services, typed errors, **and the centralized driven ports** (`repository/`, `event/`; external gateways in `integration/<sys>/`) | (nothing outward) |
| Usecase | `internal/core/usecase/**` | Orchestrate one operation; transaction/flow | `core/domain` (+ the ports it owns) |
| Delivery (driving) | `internal/delivery/**` | Translate transport ↔ usecase calls | `core/usecase`, `core/domain` |
| Outbound adapter | `internal/adapters/{gateway,repository,eventbus}/**` | Implement a port against a real system | the owning `core/domain` context, `core/domain` |
| Composition root | `cmd/api/**` | Build + wire everything | everything (the only place) |
| Configuration | `config/**` | Typed `Config` + env/file loader via `Load`/`MustLoad`; read once at startup, injected as values | (its own leaf config types only) |

## The invariants — keep the structure clean and the code readable (MUST)

Non-negotiable. A violation is a defect, not a style preference — every change is checked
against these. `★` = mechanically enforced by **golangci-lint** (fails the build): **depguard** on a
cross-layer import or a transport/persistence/infra import inside `domain`/`usecase`, and **forbidigo**
on a direct ambient call (`time.Now` / `uuid.New`) inside `domain`/`usecase`. The rest are enforced at
review and by the gates. Per-layer detail lives in the linked guides.

**Keep the structure clean — don't let the layout rot**
- ★ **Imports point inward only** (`delivery / adapters → usecase → domain`): domain imports
  nothing outward · usecase never imports an adapter or delivery · adapters never import
  usecase/delivery · delivery never imports any outbound adapter (`gateway`/`repository`/`eventbus`) —
  a wire contract shared with an adapter goes in `pkg/` (e.g. `pkg/messaging`), not in `adapters/`.
- ★ **`core` stays framework-free** (depguard): `domain` and `usecase` import no transport /
  persistence / infra library (`gin`, `net/http`, `database/sql`, `pgx`, `go-redis`, `kafka-go`) —
  the build fails on it. Business logic depends only on the stdlib + its own ports.
- ★ **Business logic is deterministic-by-injection** (forbidigo): `domain` / `usecase` never call
  `time.Now()`, `uuid.New()` / `uuid.NewString()`, `rand`, or `os.Getenv` **directly** — a domain
  service takes the resolved value (`now time.Time`), a usecase injects the port (`clock.Clock` /
  `idgen.Generator`) and reads it at the boundary; `cmd/api` wires `System()`. The build fails on a
  direct call — **this is what stops the testability seam from rotting** (see "Ambient capabilities").
- **Driven ports are centralized** in `core/domain/repository` (persistence) and
  `core/domain/event` (event bus), one interface per file referencing `entity` types — **except**
  external-system gateways, which stay in `core/domain/integration/<sys>/gateway.go`
  (`integration.md`, `domain.md`). *Also:* a context-free **ambient capability** (clock,
  id-generation) is a generic `pkg/` utility, not a driven port — see "Ambient capabilities".
- **One layer per directory.** Don't add a new top-level package under `internal/`, or move a
  layer, without updating this file first.
- **Cross-capability goes through a port:** a usecase never imports another usecase · an adapter
  never imports another adapter · handlers never import each other (only `delivery/http/router`
  imports handlers, to wire routes).
- **Map at the edges:** wire DTOs (HTTP/SQL/Kafka) and aggregates never cross a layer raw —
  translate via getters/mappers at the boundary (`handler.md`, `integration.md`, `repository.md`).
- **Never hand-edit generated code** (`…/sqlc/**`, `…/mocks/**`) — change the source + regenerate.
- A pattern **not** covered by steering → **stop, ask, fold it back** (see the section above).
  Never improvise structure.

**Keep the code readable — don't let it get hard to read again**
- **One operation = one usecase package** (`usecase.go` + `exec.go`) **and one handler file.**
  New behavior is a new package/file, not another method bolted onto a shared service.
- **Decompose a large operation into sub-packages** when it stops fitting in one head — but
  **earn the split** (don't break out a one-caller helper) (`usecase.md`).
- **Every test mirrors its source file**, in the package that owns the behavior. No floating
  tests, no concept-named tests (`<feature>_*_test.go`), no parallel/stale test families; shared
  fixtures → `exec_test.go`, single-use → the mirrored file (`testing.md`).
- **Test the exported API, not private functions.**
- **Remove dead code the moment you find it** — don't punt it as "out of scope".
- **Aggregates stay encapsulated:** private fields + getters, no setters, intent-named command
  methods (`domain.md`).
- **Aggregates hold only persistent state:** a value resolved during an operation but not persisted
  (response-only) is a **usecase return value, not an aggregate field** — no transient field carried
  through the repo round-trip via a setter + re-attach (`domain.md` / `usecase.md`).
- **Interfaces are narrow and consumer-defined**; behavior-preserving refactors **prove it with
  the existing tests**, don't reason about it.
- **Comment on the function header only:** every comment is a godoc-style comment on the
  function (or type) header. **No comments inside a function body** — make the body
  self-explanatory through naming and decomposition. A line that "needs a comment" is a
  signal to rename or extract, not to annotate.

**Verify before "done":** `gofmt` · `go build ./...` · `go vet ./internal/... ./cmd/... ./config/...` ·
`golangci-lint run ./internal/... ./cmd/... ./config/...` (≤ baseline, **incl. depguard**) · `make test` ·
then rebuild image (`make compose-up`) + `make test-e2e`.

## Steering index

Open a file in a layer and its guide loads automatically. `manual` files load only when you reference them.

| Guide | Loads when you touch | Covers |
|---|---|---|
| `domain.md` | `internal/core/domain/**` | per-layer split (entity/service/repository/event + root enums), aggregate encapsulation, value objects, domain services, events, typed errors, centralized driven-port interfaces, integration read-models |
| `usecase.md` | `internal/core/usecase/**` | the `usecase.go` + `exec.go` one-operation-per-package pattern |
| `handler.md` | `internal/delivery/http/**` | inbound HTTP: handler (op-split) + DTO + router + middleware + error mapping |
| `messaging.md` | `internal/delivery/consumer/**`, `internal/adapters/eventbus/**` | Kafka inbound processor + outbound producer + event infra |
| `integration.md` | `internal/core/domain/integration/**`, `internal/adapters/gateway/**`, `internal/adapters/repository/cache/**` | define a driven port (in its domain context) + implement it as an outbound adapter |
| `repository.md` | `internal/adapters/repository/**`, `*.sql`, `sqlc.yaml` | sqlc-backed persistence adapter + query/migration conventions |
| `app.md` | `cmd/api/**`, `config/**` | composition root: build, wire, route, run; the `config` package (typed config + loader) |
| `testing.md` | `*_test.go` | unit (stubs/fakes/mocks), property tests |
| `e2e.md` | `tests/**`, `mockoon/**` | black-box e2e: upstream stubs (one file per upstream), spec layout, sentinels, rebuild-before-e2e |
| `tooling.md` | `Makefile`, `tools/**`, mockery/lint/Docker configs | make targets, mock generation, lint, container build |
| `bruno.md` | `bruno/**` | API request collection (OpenCollection) layout |
| `new-feature-checklist.md` | *manual* — reference it when adding a feature | linear domain → … → wiring → tests procedure |
