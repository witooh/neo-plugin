# STATE.md schema

neo's durable memory for one task. One file per task at `docs/tasks/<slug>/STATE.md`. The agent
forgets between runs; this file is what survives, and it must be **readable top-to-bottom by a
human** — that is what makes the loop auditable (guards against comprehension debt). Blank copy:
`../templates/STATE.md`.

On resume (`/neo continue <slug>`), neo re-reads this file and continues from `## Next` — or, when
`status` is `done-partial`, from `## Deferred / out of scope` (see `loop-engineering.md`
"Resume on `done-partial`").

## Fields

- **`slug`** — short kebab-case task id (or JIRA card id / MR id).
- **`human_gate`** — `pending` | `passed`. neo may not commit / open an MR until `passed`.
- **`goal`** — one sentence; the recursive goal. Observable, not "make it better".
- **`exit_condition`** — the table of criteria that define done. Each row:
  - `id` — short stable id (e.g. `ac-1`, `build-clean`).
  - `criterion` — the observable statement.
  - `verify_method` — `machine` (a command proves it) or `judgment` (a reasoning check).
  - `evidence` — for `machine`: the command + expected result; for `judgment`: the artifact +
    what "met" looks like.
  - `status` — `unmet` | `met`. Set by the fresh-context checker, never by the maker alone.
  - **Feature rule:** a task that adds or changes a feature MUST include a `design-exists` row
    (`verify_method: judgment`, `evidence:` = the Define-phase spec/design artifact). It is
    **non-waivable for features** — the loop cannot exit while it is unmet, which is what stops
    a jump to Build with no docs. Work that does not add or change behavior (a typo, a config /
    dependency bump, a rename, a single-line fix) is exempt.
- **`limits`** — `iteration_cap` and `budget` (token / wall-clock), chosen up front.
- **`knowledge_refs`** — links into `docs/knowledge/` for sources ingested for this task.
- **`status`** — the loop's current phase: `framing` (authoring goal + exit) → `primed`
  (knowledge ingested, ready) → `looping` (iterating) → `stuck` (hit a no-progress / cap /
  budget exit, escalated) → `done` (exit verified + human gate passed, **nothing deferred**) |
  `done-partial` (exit verified + human gate passed **for the loop's scope**, but ≥1 follow-up
  was scoped OUT and is recorded in `## Deferred` — see `deferred` below). `done-partial` is NOT
  an unmet exit: every `exit_condition` row is still `met`; the deferred items were never exit
  criteria. It exists so a reader sees at the top that the task closed *for its scope* with named
  follow-ups left, instead of a bare `done` that reads as "nothing remains". This is the one
  mutable field outside the append-only log.
- **`iterations`** — the **append-only audit log**. One `### N` block per iteration; never
  rewrite history. Each block:
  - `ran` — the lifecycle skill(s) this iteration ran from the Skill Discovery flowchart
    (e.g. `test-driven-development → code-review-and-quality`). The audit trail of *which* part
    of the SDLC executed.
  - `waiver` — use **instead of** `ran` only when a change was made without running the
    flowchart's indicated skill: `<reason> (user-approved <date>)`.
  - `change` — one line: what this iteration changed.
  - `evidence` — artifact path(s) the checker read (test report, build log, drift report).
  - `exit_met` — `yes` | `no`. The fresh-context checker's verdict for this iteration.
  - `next` — the unmet gap that drives the next iteration.
- **`next`** — the resume pointer for a non-terminal run: what the next run does first while the
  loop is still open. At a terminal status it reads DONE; a `done-partial` resume enters from
  `## Deferred`, not here.
- **`deferred`** (`## Deferred / out of scope`) — the scoped-OUT follow-up list, written by the
  **maker** (not the checker). Two groups: **before-prod / needs-a-decision** (genuine deferred
  scope — a user-deferred open question, an out-of-scope concern, an integration step that cannot
  be verified in this loop) and **post-ship admin** (push / PR / JIRA — neo leaves these to the
  human). These are explicitly NOT `exit_condition` criteria and do not gate the loop; they are
  what remains after it closes for its scope. Empty (or the section absent) when nothing was
  deferred.

## Rules

- The **fresh-context checker** is the only writer of `exit_condition[].status` → `met` and of
  each iteration's `exit_met`.
- `iterations` is **append-only** — never rewrite history; it is both the audit trail and the
  no-progress signal.
- **No-progress** = the last ~3 iterations log `exit_met: no` with the same `next:` gap (no real
  change) — the readable form of LOOP.md's "repeating `(action, observation)`" check. It forces
  the human gate (`status: stuck`). See `loop-engineering.md`.
- `status` is the only mutable field outside the append.
- **Deferred ⇒ done-partial.** If `## Deferred / out of scope` carries any item when the loop
  closes, `status` MUST be `done-partial`, not `done` — a checkable consistency rule folded into
  the process-integrity consistency pass (`loop-engineering.md`). A bare `done` asserts nothing
  remains, so it must not coexist with a non-empty Deferred list.
- A change-producing iteration MUST carry `ran:` (the skill[s] it ran) or `waiver: <reason>
  (user-approved <date>)`. A logged change with neither is malformed. This is **enforced at
  exit** by the process-integrity gate (presence + phase-order + consistency + authenticity;
  see `loop-engineering.md`) — a silent skip fails the gate and forces the human gate. A run that
  does **not add or change behavior** may use ONE `waiver: trivial — <reason> (user-approved
  <date>)` to cover the phases it skips rather than one per phase; Define stays non-waivable for
  feature work.
- Keep entries short: STATE.md is a log, not a report — the report is the diff the loop produced.
  If a block exceeds a few lines, the iteration was too big; take a smaller slice next.
- `status: stuck` must be accompanied by the blocker + last evidence and a human escalation.
