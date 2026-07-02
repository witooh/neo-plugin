# Target Map — content spec for `<target>/docs/migration/target-map.md`

The **Analyzer** writes this (read-only role). A precise picture of the target's **current**
structure + the **delta** to the blueprint. Accurate, not exhaustive — the Mapper turns it into
slices. Markdown.

## Shape

```
# Target Map — <service-name>

Module: <go.mod module path>
Go: <version>   Stack: <gin? pgx? sqlc? common-lib?>
Analyzed: <YYYY-MM-DD or session marker>

## Current layout
<top-level tree to ~3 levels; annotate which layer each dir holds>

## Dialect deltas (current → blueprint)
| Concern | Current | Blueprint |
|---|---|---|
| composition root | <e.g. app/ + cmd/main.go> | cmd/api/ |
| http handlers | <e.g. internal/adapter/handler/<r>/> | internal/delivery/http/handler/<r>/ |
| domain | <e.g. internal/domain/*.go (flat)> | internal/core/domain/ (per layer: entity/ service/ repository/ event/) |
| usecase | <e.g. internal/<feat>/usecase/> | internal/core/usecase/<context>/<op>/ |
| repository | <e.g. internal/<feat>/repository/ + database/postgres/> | internal/adapters/repository/postgres/ |
| gateways | <e.g. external/<sys>/> | internal/adapters/gateway/<sys>/ |
| ports | <e.g. internal/<feat>/ports/> | centralized in internal/core/domain/{repository,event}/ (gateways in integration/<sys>/) |

## Features / bounded contexts
| Feature | Current home(s) | Notes (layers present, coupling) |
|---|---|---|
| <name> | <usecase / repo / handler / domain paths> | <e.g. repo used by another feature> |

## Convention gaps (vs steering)
- [ ] aggregates: <plain structs / public fields> → encapsulate (private + getters + factories) — domain.md
- [ ] ports: <feature-local internal/<feat>/ports/ or scattered> → centralize in internal/core/domain/repository/ + event/ (gateways stay integration/<sys>/) — domain.md
- [ ] deterministic-by-injection: time.Now()/uuid.New() in core at <file:line> → clock/idgen — structure.md
- [ ] DTO mapping: <returns aggregate raw?> → map at the edge — handler.md
- [ ] <other gaps>

## Cross-cutting
- error handling: <where> · response envelope: <where> · middleware: <where> · config loader: <where>
- already has .golangci.yaml? <y/n>   .kiro/steering/? <y/n>

## Candidate slice order (advisory)
- S1 cross-cutting + install · S2..Sn one feature each (state coupling order) · S-last cmd/api

## Boundary
<if the target has no Go code → "greenfield: use the init-project skill, not migrate-project">
```

## Rules
- The **dialect deltas** table and the **convention gaps** checklist are the heart — the Mapper
  derives slices and target placements from them. Fill them concretely (real paths, real `file:line`
  for ambient-call gaps), not generically.
- Every feature row must name where the feature lives **now**, so the Migrator knows what to relocate.
- Read-only: this artifact records what you found; it never proposes code edits beyond the advisory
  slice order.
