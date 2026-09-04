# Shared: Migration Tracking — the resumable slice plan

**Single source of truth for the migration plan-file (`<target>/docs/migration/plan.md`) and the
`Slice` progress axis.** Referenced by the Mapper (the sole writer of the plan-file) and the
Orchestrator (reads it to route + resume). This file owns the **definitions**; the role/SKILL prose
that cites it keeps its own enforcement.

## 1. The plan-file — `<target>/docs/migration/plan.md`

- **One markdown file per target service.** Markdown **by design** — the orchestrator reads it to
  decide resume-vs-fresh and to scope continued work, in the spirit of how `using-neo` resumes from `docs/tasks/<id>/plan.md` + `todo.md`.
  It lives in the **target repo** (the thing being migrated), not in this skill.
- **Sole writer = the Mapper.** The Migrator moves code; the Verifier runs gates; neither writes the
  plan. The orchestrator is write-forbidden. Every plan-file write/refresh is a Mapper dispatch.
- **Reader = the orchestrator**, to decide resume vs. fresh and to scope the next slice. Humans read
  it as the migration's resume index.
- It sits beside `target-map.md` (the Analyzer's structure map of the target before migration).

## 2. The unit of work is a SLICE, not a file

A **slice** is the smallest independently-verifiable migration step — a coherent set of moves that
leaves the target **building, testing, and lint-clean** on its own. The unit is a *structural change*
(a feature relocated to the blueprint layout, a cross-cutting package installed), **not** a single
file and **not** an AC. Slice order **is** execution order. A slice that cannot end green is too
large — the Mapper splits it.

The canonical slice shape for a service that is already clean-but-different-dialect (the common case):
1. **S1 — cross-cutting + install** — install `.golangci.yaml` (with the **target's** module path
   substituted into its depguard rules) + `.kiro/steering/` (including `INDEX.md`) + `CLAUDE.md`;
   relocate shared/edge code (error mapping, response envelope, middleware, config) into the
   blueprint layout; when `target-map.md` flags it, bump common-lib to v2.2.4 and rewrite
   removed APIs (migrator.md); create the `internal/core/` skeleton. After S1 the contract is
   in place even though most features still fail it.
2. **S2..Sn — one feature per slice** — relocate each bounded context into the per-layer domain
   (`internal/core/domain/{entity,service,repository,event}`) + `internal/core/usecase/<context>/<operation>/`
   + the adapter (`internal/adapters/{repository,gateway}`) + delivery
   (`internal/delivery/http/handler/<resource>`), rewriting imports and filling convention gaps
   (aggregate encapsulation, centralized ports in `repository/` + `event/`, deterministic-by-injection)
   per the steering.
3. **S-last — composition root** — converge wiring on `cmd/api/{app,http,adapters,consumer}.go`.

## 3. Slice state machine

- `pending` — not started (the default at plan-file creation).
- `in-progress` — the Migrate Loop has begun this slice but it has not yet exited green.
- `done` — the slice's Verify exited green: `go build ./...` + `go vet ./...` + the existing
  `go test ./...` + `golangci-lint run` all pass (the same exit condition the orchestrator's Migrate
  Loop uses). `done` means **moved + verified**, not merely "files relocated".

A slice never reaches `done` while its verify is red; it stays `in-progress` and the Migrator loops.

The Migrate Loop that drives a slice to `done` has **four independent exits** (SKILL.md P3 step 3):
green → `done`; **no-progress** (Verifier `failure-set` repeats), **hard cap** (3 rounds), or
**scope-drift** (blast radius exceeds the slice's planned scope) → the slice stays `in-progress` and
the orchestrator **escalates** — a stuck slice is never silently retried forever and never marked `done`.

## 4. The plan-file shape

Content spec: `templates/plan-template.md`. The structure:

- **Header** — target path · blueprint ref (`INIT_TEMPLATE` steering) · migration branch · slice
  tally (`<done>/<N> done`) · updated marker.
- **`## Slices`** table — the per-slice status/resume index:

  | Slice | Scope | Status | Verify | Depends-on |
  |---|---|---|---|---|
  | S1 | cross-cutting + install contract | done | `go build && go test ./...` | - |
  | S2 | `product` context → blueprint | in-progress | `go build && go test ./...` | S1 |

- **Per-slice detail** — below the table, one `### S<n> — <scope>` section per slice listing: the
  concrete moves (old path → blueprint path), the steering guide(s) that govern them, and the verify
  command. The **`### Ready` (pending/in-progress) slices are elaborated to path level**; `done`
  slices are not re-stated (the table row is the record); far slices stay coarse until reached
  (file-level detail on far work only drifts).

## 5. Lifecycle — who writes when (every write is a Mapper dispatch)

1. **At Plan (P2):** the Mapper diffs `target-map.md` against the steering and writes the full slice
   list — every slice `pending`, S1 elaborated to path level, later slices coarse.
2. **After each slice's Verify exits green (P3):** the orchestrator dispatches the Mapper in
   **tracker-sync** mode to set that slice `Status = done` and update the tally + the updated marker.
   Updating per slice (not only at the end) keeps progress crash-resilient across sessions.
3. **On resume (P0):** the orchestrator reads the plan-file, finds the first `pending` /
   `in-progress` slice, and continues from there — re-elaborating that slice to path level if the
   target drifted since it was planned.

## 6. Drift containment
Only the **next** unbuilt slice is elaborated to path level — it is the small, short-lived set of
work actually in front of the Migrator. The Mapper **regenerates** the elaborated detail from the
current target + steering on each refresh rather than hand-maintaining a parallel copy of every
slice's file list. A relocated path recorded in a `done` slice is the git history's job, not the
plan-file's.

## 7. No re-narration
Beyond the header, tally, slice table, and per-slice detail, the plan-file may end with **one
optional `Notes` section** — a few lean tracking bullets (e.g. a cross-slice ordering caveat, a
deferred convention gap the user accepted). Anything **owned elsewhere** is referenced, never
re-narrated: a verify failure → the Verifier's report; an architecture decision the user made → state
it once as a one-line caveat, not the rationale. Bullets, not prose.
