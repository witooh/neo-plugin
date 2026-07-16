# Ingest, Define, and Plan Contracts

Read only the section selected by `using-neo`.

## Ingest

Use when the request names an external source not yet curated in
`docs/knowledge/`.

1. Identify the exact URL, Jira/Confluence item, file, image, or brief.
2. Invoke `markitdown`; it owns provenance, placement, verbatim contract
   clauses, Related links, `docs/knowledge/INDEX.md`, and rejection of ephemeral
   noise.
3. Confirm the source is captured and repair any Related link that was waiting
   for it.
4. If the ingest resolves a question, decision, dependency, or plan task, sync
   `spec.md`, `plan.md`, and `todo.md` per `references/task-docs-sync.md`.

Do not reimplement curation in `using-neo`.

**Exit evidence:** the curated entry and index exist, provenance is present,
required clauses are verbatim, links resolve, and no tracker still says the
source is missing.

## Define

Use for a new feature or significant change without an approved spec.

1. If a named source is not curated, offer Ingest first. Continue without it
   only when the user explicitly chooses that tradeoff.
2. Read `docs/knowledge/INDEX.md`, relevant entries, existing task documents,
   design docs, and code before asking questions.
3. Invoke `spec-driven-development` to establish objective, audience,
   constraints, boundaries, behavior, and success criteria.
4. Preserve every source acceptance criterion without merging or inventing
   requirements. Give independently testable criteria stable IDs `AC-001`,
   `AC-002`, and so on.
5. Include a Sources section linking every knowledge entry used. Save the
   confirmed result to `docs/tasks/<card>/spec.md`.
6. For HTTP behavior, invoke `api-spec` in Draft mode. Keep endpoint wire
   contracts in `docs/api/`; the task spec retains business intent and AC IDs.
7. When amending a spec, sync every changed decision, scope statement, source,
   and task status across `plan.md`, `todo.md`, and knowledge Related blocks.

**Exit evidence:** the user approved the spec, all ACs are stable and testable,
Sources are complete, no unresolved question is hidden, and any HTTP contract
has a valid `docs/api/` draft.

## Plan

Use when an approved `docs/tasks/<card>/spec.md` exists but implementable tasks
do not.

1. Enter read-only planning mode and inspect the spec plus relevant code.
2. Invoke `planning-and-task-breakdown` to map dependencies and slice work
   vertically.
3. Give every task acceptance criteria, verification commands, dependencies,
   likely files, and a scope small enough for one focused implementation.
4. Add a coverage verification task and checkpoint. Discover and record the
   canonical command, baseline, scope, and existing exclusions; require the
   repository's stricter threshold or at least 80% project-wide unit line coverage.
   If the baseline is lower, plan tests that raise the whole project; otherwise
   add a blocking gate that prevents regression below the threshold.
5. Keep all first-party source in scope and respect only existing generated,
   vendor, and third-party exclusions. A new or expanded exclusion is a material
   open question, never a substitute for adding tests.
6. Add checkpoints between major groups.
7. End every new or revised plan with a phase titled exactly
   `Phase N — Documentation sync and final gates`, where `N` follows the
   preceding phase. This mandatory phase must include:
   - a documentation task that performs a final consistency sweep across the
     card's spec, plan, todo, and relevant knowledge links;
   - a final-gates task and checkpoint that apply the project Definition of Done
     plus every applicable repository verification command; and
   - explicit completion evidence and any remaining commit, ship, human-review,
     or deployment stop.
   Continue synchronizing documentation when facts change throughout earlier
   phases; this final phase verifies consistency instead of deferring updates.
8. Present the plan for approval.
9. Save `docs/tasks/<card>/plan.md` and `todo.md`.
10. When revising an existing plan, preserve completed tasks and dated history;
   sync resulting decisions or scope changes back to the spec and todo list.

**Exit evidence:** plan and todo files agree, dependencies are ordered, no task
is oversized or unverifiable, the coverage task preserves at least the project
threshold, the mandatory final documentation-and-gates phase is present, and
the user approved the plan.
