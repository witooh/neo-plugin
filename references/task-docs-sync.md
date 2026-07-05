# Task-Docs Sync

A standing rule for keeping a card's working documents consistent: when a fact
about the work changes, **every document that states that fact gets updated in
the same pass** — never just the nearest one. The documents of one card form a
single record split across files; updating one and leaving the others stale
plants a contradiction that a future session will read and act on.

The failure this prevents is real: an ingest landed in `docs/knowledge/` and
`todo.md` was ticked, but `spec.md` (Sources) and `plan.md` (update note,
decisions, task line, dependency graph, risk table) still said "not yet
ingested — blocked". The next reader either re-blocks the task or re-asks the
user for a source that was already captured.

## Trigger events

Run the sync whenever one of these happens, in any phase, in or out of a skill:

- A **source is ingested** (satisfies a "not yet ingested" / ⛔ item).
- An **open question (OQ) is resolved** or a **decision is made mid-flow**
  (user answer in conversation counts — it doesn't need a formal review).
- The **scope changes** (a case deferred, a channel dropped, a boundary moved).
- A **task changes state** (started, done, re-blocked, re-scoped).
- A **risk is resolved** or materially changed.

## The doc set to sweep

For the affected `<card>`, check **all** of these — update every place the
changed fact appears:

- `docs/tasks/<card>/spec.md` — Sources entries, and any decision anchor or AC
  note that states the old fact.
- `docs/tasks/<card>/plan.md` — the dated update note in the header, the
  decisions/assumptions list, every affected task line, the dependency graph,
  and the risk table.
- `docs/tasks/<card>/todo.md` — the header note and the task line.
- `docs/knowledge/` — the requirement entry's **Related** block and `INDEX.md`.

## Method

1. Pick the identifiers of the changed fact: the source basename/topic, the OQ
   id, the decision id, the task id.
2. Grep those identifiers — plus the stale-state markers (`⛔`,
   "not yet ingested", "TBD", "blocked") — across the doc set above. Grep is
   the finder, not the whole sweep: counters and summary lines ("N ingests
   remaining", "X blockers left") carry no identifier — walk the doc-set list
   above item by item as well.
3. Update every hit that states the old fact. Add, don't erase: a **dated
   history note stays as written** (it is a changelog line, correct for its
   date); append the new dated note beside it instead of rewriting history.
4. New decisions continue the existing numbering scheme of the plan they land
   in; a resolution names its trigger ("resolved 2026-07-05, user-designated")
   so provenance survives.

## Verification

- Re-grep the identifiers and stale markers: **zero** remaining statements of
  the old state for the resolved fact (dated history notes excepted).
- Every doc in the set that mentioned the fact now shows the new state or a
  dated note recording the change.

## Red Flags

- Updating only the file nearest to the work (todo ticked, spec/plan stale).
- Syncing `docs/knowledge/` but not `docs/tasks/<card>/` — capture recorded,
  trackers still blocked.
- Rewriting or deleting a dated history note instead of appending a new one.
- Declaring the change recorded without the re-grep sweep.
- Silently superseding a conflicting source instead of raising the conflict.
