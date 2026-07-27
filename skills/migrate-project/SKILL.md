---
name: migrate-project
description: >
  Refactor an EXISTING Go service so its structure conforms to the account-service hexagonal / DDD
  blueprint — the brownfield sibling of `init-project` (which supplies the target-structure
  contract: its frozen template + `.kiro/steering/` + `.golangci.yaml`). Plans the work as ordered,
  independently-verifiable SLICES (one bounded context each), moves each on a branch with `git mv`
  (behavior-preserving), and verifies per slice (go build/test/vet + golangci) plus a final
  three-layer check (L1 `structurecheck.py` + L2 fresh-eyes + L3 completeness). Plan-first and
  resumable via `<target>/docs/migration/plan.md`. Trigger on: "migrate project", "/migrate-project",
  "restructure an existing service", "refactor ให้เหมือน account-service", "ย้ายโครงสร้างโปรเจกต์",
  "จัดโครงสร้างใหม่ตาม account-service", "migrate service เดิมให้เข้าโครง", "ปรับโครงสร้าง service
  ให้เหมือน account-service". NOTE: refactors EXISTING code — a brand-new empty service is
  `init-project`; adding a domain / AC / endpoint / tests is `using-neo`.
compatibility:
  environment: claude-code
  tools: [Agent, Read, AskUserQuestion]
metadata:
  version: "1.0"
---

# migrate-project — Brownfield Migration Orchestrator

Refactor an **existing** Go service so its structure matches the `account-service` hexagonal / DDD
**blueprint**. You are the **orchestrator**: you analyze, plan, checkpoint, and dispatch specialists —
you **do not move code yourself**. The blueprint is reused from the `init-project` skill (its frozen
template + `.kiro/steering/` guides); this skill is the brownfield counterpart that brings an existing
codebase up to that blueprint, slice by slice, behavior-preserving and resumable.

> **Boundary.** This refactors an **existing** codebase. An **empty / new** service → the
> **`init-project`** skill (greenfield scaffold). Adding a domain / AC / endpoint → **`using-neo`**.

## Core Rules
- **Orchestrate, never implement.** Every move / analysis / verify goes to a specialist via `Agent`.
  Never use `Edit` / `Write` / `Bash` yourself — you only `Read` (plan/map/context), plan, and
  checkpoint.
- **Never guess.** Unclear target / scope / a pattern the steering doesn't cover → `AskUserQuestion`
  first; relay a specialist's Open Questions to the user, never invent an answer.
- **Point-to-read, never paste.** A dispatch sends *paths* (`MIGRATE_DIR` + `INIT_TEMPLATE` +
  artifact paths); the specialist reads its own role spec. Never paste role specs / file contents.
- **Behavior-preserving.** This is a structural migration — observable behavior must not change. It is
  proven per slice by the existing tests + build + lint staying green, never by reasoning.

## Tools
| Tool | Purpose |
|---|---|
| `Agent` | Dispatch a specialist (`subagent_type: "general-purpose"`): Analyzer · Mapper · Migrator. **Verifier + Reviewer** → `"fresh-eyes"` — both are report-only by their own role spec, so a read-only tool grant stops them editing what they judge (harness without that type → `general-purpose`). |
| `Read` | Read `<target>/docs/migration/{plan,target-map}.md` (resume + route) and project context (`CLAUDE.md`, `go.mod`). |
| `AskUserQuestion` | Get the target dir; **CP1** plan approval; relay Open Questions. |

## Handoff (point-to-read)
- **`MIGRATE_DIR`** = this skill's base dir (from the skill-load message *"Base directory for this
  skill: …"*). The specialist is a generic agent and does not know it — send it on **every**
  dispatch.
- **`INIT_TEMPLATE`** = `<MIGRATE_DIR>/../init-project/assets/template` — the frozen blueprint
  (steering guides + `.golangci.yaml` + `CLAUDE.md`). Send it too; the roles read the steering from
  there.

## Phases
- **P0 — Init / Resume.** Get the target dir (`AskUserQuestion` if not given). If
  `<target>/docs/migration/plan.md` exists → **resume**: `Read` it, report the slice tally, continue
  from the first `pending` / `in-progress` slice (skip to P3). Else → fresh (P1).
- **P1 — Analyze.** Dispatch **Analyzer** → `<target>/docs/migration/target-map.md`. **Boundary:** if
  it reports no Go code (empty dir) → STOP and point the user at `init-project`.
- **P2 — Plan.** Dispatch **Mapper** → `<target>/docs/migration/plan.md` (ordered slices). **[CP1]**
  show the slice plan + `AskUserQuestion` Confirm / Edit / Cancel — the gate **before any code moves**.
- **P3 — Migrate loop** (per `pending` slice, in order):
  1. Dispatch **Migrator** for that one slice (it works on branch `migrate/hexagonal-blueprint`,
     creating it on the first slice; `git mv` + import rewrite + convention-gap fill; S1 installs the
     contract).
  2. Dispatch **Verifier** (`go build` + `go vet` + the existing `go test` + `golangci-lint`).
  3. **The Migrate Loop** — re-dispatch the Migrator with the Verifier's findings → re-verify (one
     Migrator→Verifier cycle = one round; the initial dispatch is round 1). **Four independent
     exits**, only the first is success:
     - **Green** → exit success (slice may be marked `done`).
     - **No-progress** → the Verifier's `failure-set` is identical to the previous round's → the
       slice is stuck; escalate with the repeating set (catches circling early, ~round 2).
     - **Hard cap** → 3 rounds on one slice still red → escalate with the remaining failures
       ("moving but not reaching green").
     - **Scope-drift** → the Migrator returns `NEEDS_CONTEXT` because the slice's real blast radius
       exceeds the scope `plan.md` records for it → escalate with what falls outside the plan (the
       CP1-approved plan no longer covers this slice).
     Every non-green exit escalates via `AskUserQuestion` — reason + attached evidence + options
     (retry / split / accept-gap / re-approve scope); **never mark a red slice `done`**. A Migrator
     `NEEDS_CONTEXT` for a steering gap / behavior change → relay to the user, re-dispatch with the answer.
  4. Green → dispatch **Mapper (tracker-sync)** to set the slice `done` + refresh the tally.

  Resumable: the user may stop after any green slice and re-invoke later (P0 resumes).
- **P4 — Final three-layer verify** (after the last slice):
  - **L1** — dispatch **Verifier** in final mode: `python3 <MIGRATE_DIR>/assets/structurecheck.py
    --target-dir <target>` (deterministic conformance tripwire) **plus** full `golangci-lint run` +
    `go build` + `go test` + **a Docker image build** (`docker compose build <svc>`, or
    `make compose-up`) — the gate that catches stale build/run tooling refs (a relocated entrypoint,
    a deleted-fixture `COPY`) that package-mode `go build ./...` never exercises. DRIFT / build
    failure → loop back to the Migrator.
  - **L2** — dispatch **Reviewer** (`<MIGRATE_DIR>/references/migrate-verifier.md`), independent
    fresh-eyes: conforms to steering? behavior preserved? no residue? Relay findings.
  - **L3** — completeness sweep: from `target-map.md`, confirm every feature is present in the new
    layout, every slice in `plan.md` is `done`, and no old-dialect residue remains (dispatch a sweep
    if the reports don't already cover it).
- **P5 — Report.** Summary: target · slices done · the migration branch · verify results · residual
  concerns · next steps (review the branch diff, run the service, merge). Never auto-merge or push.

## Checkpoints (2 only)
**CP1** the slice plan (before any code moves) · **CP-final** the P5 summary (fold the L2 fresh-eyes
ask into it). The per-slice migrate loop runs continuously — the plan was already approved at CP1 and
each slice is gated by its own verify; per-slice checkpoints would only re-litigate the approved plan.

## Dispatch (point-to-read)
```
Agent(subagent_type: "general-purpose" | "fresh-eyes" for Verifier + Reviewer, description: "<3-5 words>", prompt: """
# Role: <Name>  (role-id: <id>)
Read first: <MIGRATE_DIR>/references/preamble.md + <MIGRATE_DIR>/references/roles/<role>.md
(Mapper also: <MIGRATE_DIR>/references/migration-tracking.md + templates/plan-template.md)
(Analyzer also: <MIGRATE_DIR>/references/templates/target-map-template.md)
(Reviewer reads: <MIGRATE_DIR>/references/migrate-verifier.md)
(Verifier + Reviewer are read-only: list Open Questions inline whatever the count, and report a
 regression instead of fixing it — preamble §2's open-questions file and §3's "fix and re-verify"
 belong to the writing roles. Scratch builds go to /tmp, never into the target tree.)
MIGRATE_DIR   = <abs path of this skill>
INIT_TEMPLATE = <MIGRATE_DIR>/../init-project/assets/template   # blueprint steering + .golangci.yaml + CLAUDE.md

## Task
<this phase / this one slice only>

## Context / Artifacts (read from path — never pasted)
- target dir: <abs path>
- target map: <target>/docs/migration/target-map.md      # P2+ 
- plan:       <target>/docs/migration/plan.md             # P3+
- slice:      <slice id + scope>                          # Migrator/Verifier in P3

End with Status: DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED
""")
```
**Parallel writers:** the Migrate Loop is sequential (one slice at a time — slices are ordered and
share files). The final L1/L2 verify are read-only.

## Subagent Status
A specialist ends with `DONE | DONE_WITH_CONCERNS | NEEDS_CONTEXT | BLOCKED`.
- `NEEDS_CONTEXT` / `BLOCKED` → something must change before re-dispatch (never treat as DONE).
- **Open Questions** → pause, relay verbatim to the user, re-dispatch with the answers, confirm the
  ephemeral `docs/migration/open-questions-*.md` was deleted.
