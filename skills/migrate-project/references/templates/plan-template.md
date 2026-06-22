# Migration Plan — content spec for `<target>/docs/migration/plan.md`

The **Mapper** writes this (sole writer — migration-tracking.md). Markdown **by design**: the
orchestrator reads it to resume. Keep it a tracking index, not prose.

## Shape

```
# Migrate <service-name> → hexagonal blueprint

Target: <abs path to the target repo>
Blueprint: INIT_TEMPLATE steering (account-service hexagonal/DDD)
Branch: migrate/hexagonal-blueprint
Slices: <done>/<N> done
Updated: <YYYY-MM-DD or session marker>

## Slices

| Slice | Scope | Status | Verify | Depends-on |
|---|---|---|---|---|
| S1 | cross-cutting + install contract | pending | build + test + golangci | - |
| S2 | <context> context → blueprint | pending | build + test + golangci | S1 |
| … | … | … | … | … |
| S<last> | composition root (cmd/api) | pending | build + test + golangci | S2..Sn |

Status ∈ pending | in-progress | done (migration-tracking.md §3). `done` = build + vet + the
existing test suite + golangci all green.

## S1 — cross-cutting + install contract       (next unbuilt slice — elaborated to path level)
Moves:
- install `INIT_TEMPLATE/.golangci.yaml` → `<target>/.golangci.yaml`  (substitute example.com/neo/service → <target module>)
- install `INIT_TEMPLATE/.kiro/steering/` → `<target>/.kiro/steering/`  (+ fill repo-instance.md with real contexts)
- install `INIT_TEMPLATE/CLAUDE.md` → `<target>/CLAUDE.md`
- <current edge path> → <blueprint path>     (error mapping / response envelope / middleware / config)
- create `internal/core/{domain,usecase}/` skeleton
Steering: structure.md · app.md · handler.md (middleware + router)
Verify: `go build ./... && go test ./... && golangci-lint run ./internal/... ./cmd/... ./config/...`

## S2 — <context> → blueprint                  (coarse until it becomes the next unbuilt slice)
Scope: relocate the <context> bounded context (domain + usecase + repository + gateway + handler) to
the blueprint layout; fill convention gaps per steering. (Elaborated to path level when reached.)

… one section per slice …

## Notes (optional)
- <lean tracking bullets only: cross-slice ordering caveat, a convention gap the user accepted as
  deferred. Nothing owned elsewhere — a verify failure lives in the Verifier's report, not here.>
```

## Rules
- The **Slices table** is the resume index; the per-slice sections carry the detail. Only the **next
  unbuilt** slice (and S1 at creation) is elaborated to path level — far slices stay scope-only
  (migration-tracking.md §6 drift containment); `done` slices are not re-stated.
- Every slice's `Verify` must be a command that proves the slice ends green; a slice whose verify
  cannot pass on its own is too large — split it.
- One file per target, in `<target>/docs/migration/`. Never HTML.
