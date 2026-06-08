# Shared: Task Tracking — Build Progress Axis + the Card Task-File

**Single source of truth for the `Build` progress axis and the per-card task-file (`docs/tasks/<card-id>/plan.md`).** Referenced by the Business Analyst (the sole writer of the task-file) and the Orchestrator (reads it to route + resume card-keyed work). This file owns the **definitions**; the role/SKILL prose that cites it keeps its own enforcement.

**This is NOT the `Status` field.** `ac-status.md` §1 is explicit: the AC `Status` encodes **dependency-readiness** (`Ready | Blocked`), never progress, and never any other value. The `Build` axis defined here is a **separate, orthogonal** dimension — it records *implementation progress*, lives **only** in the task-file (never in the AC document), and must never be written into the AC's `Status` field. Readiness answers "can this AC be implemented now?"; Build answers "has it been implemented + verified yet?".

## 1. Scope — card-keyed work only

The task-file exists **only** for work that carries a JIRA card ID. Ad-hoc / general requests (no card) keep the existing flow and never get a task-file. For card-keyed work the task-file is **mandatory before the Build phase** — the orchestrator enforces this with a pre-Build guard that mirrors the All-Blocked guard (an unnamed routing check, not a numbered gate): card-keyed work with no current task-file → the orchestrator dispatches BA to create it before any Build.

**One AC document, many cards.** A usecase's AC document can be shared by several cards (e.g. sub-operations each tracked by a different card). Card X's task-file lists **only the ACs that card X tracks** — those whose AC `JIRA Ref` (the ac-card `jira` value) includes X — not every AC in the document. Scope the rows from the `jira` field, never the document as a whole. **Pointer / cross-ref ACs:** an AC pulled in only because it cross-references this card while its real implementation is another AC (e.g. `AC-014` is a pointer to `AC-007`) still gets its row, but its `Build` is the reference `→ AC-007` (not a progress value) and it is **excluded from both roll-up tallies** (`Readiness` and `Build`) — a visibility row, not a counted work item, so the work and its readiness are tallied once on the AC that owns it. Its row still shows the mirrored `Readiness` value so the cross-reference stays visible.

## 2. The task-file — `docs/tasks/<card-id>/plan.md`

- **One markdown file per card.** Markdown **by design** — the orchestrator reads it to route/resume, exactly as it reads `docs/design/INDEX.md` / `VERSION.md`. It is **out of scope of `lint.py` / `docverify.py`** and is a registered markdown exception (`html-output.md` §8). **Never** author it as `.html`; never point the HTML verifiers at `docs/tasks/`.
- **Sole writer = Business Analyst.** The Developer and QA produce deliverables (code, test docs), not tracking state; the orchestrator is write-forbidden. So every task-file write/refresh is a BA dispatch. Content spec: `../templates/task-file-template.md`.
- **Reader = the orchestrator**, to decide resume vs. fresh and to scope continued work. Humans read it as the card's resume index.

## 3. Columns (per AC row)

| Column | Owns | Source |
|---|---|---|
| `Readiness` | a mirror of the AC `Status` (`Ready`/`Blocked`) | the AC document — read, not re-derived |
| `Build` | the progress axis — `pending` -> `in-progress` -> `done` | the task-file (the state machine in §4) |
| `Depends-on` | cross-AC ordering (e.g. AC-002 needs AC-019) | the AC's `Blocker:` dependency id (`ac-status.md` §2 format) + obvious build order |

`Readiness` is a **mirror, not a second writer** of readiness: the AC document stays the source of truth; the task-file copies it. When readiness changes (a blocker resolves), the same BA dispatch that mutates the AC document also refreshes this column (see §7).

**Sub-tasks are not a column.** A big AC's intra-AC steps live in a `### <AC-ID> — sub-tasks` section **below the Tasks table** (§5), so the checklist renders as a real vertical task-list instead of being crammed into a single table cell.

## 4. `Build` state machine

- `pending` — not started (the default at task-file creation).
- `in-progress` — the Dev Loop has begun this AC but it has not yet exited green.
- `done` — the AC's Dev Loop has **exited green** (its E2E passes and code review + security are clean — the same exit condition the orchestrator already uses). `done` means **built + verified**, not merely "code written".

A `Blocked` AC (Readiness) cannot reach `in-progress` / `done`; it stays `pending` until its blocker resolves and it is promoted to `Ready` via the existing Blocker-resolved re-entry flow. Progress is never inferred from readiness, and readiness is never inferred from progress.

## 5. Sub-tasks — adaptive, big-AC only

Do **not** give every AC a sub-task checklist — most ACs map to a single surface and need none (a one-field validation, a pointer / superseded AC, a wire-up to an existing method). Materialize a checklist **only for a big AC**: one whose design touches **two or more new or independent surfaces**, read from the Architect's per-AC design-element mapping in `traceability.html`. Signals of "big": an AC that needs a new adapter *and* a new port field *and* new selection logic; an AC with several independent layers (e.g. a multi-layer idempotency path). **Layout:** render each big AC's checklist as a `### <AC-ID> — sub-tasks` section **below the Tasks table** (never a table column — a markdown cell can't hold a readable multi-line checklist), one vertical GFM checklist per big AC in document order, each item `- [ ]` / `- [x]`. Ticking them gives intra-session resume for the few ACs large enough that one session may not finish them.

## 6. Shared prerequisites lane

Some implementation work is **not owned by a single AC** — it unblocks several. A new adapter, a new port field, or a new request DTO field may each be a prerequisite for two or more ACs. Track these in a **Shared prerequisites** table (prereq | `Build` | which ACs it unblocks), so resume sees "build this once -> unblocks AC-001 / AC-004 / AC-019" instead of scattering the same work across AC rows.

**Derivation — no new Architect artifact.** The lane is derived from data the Architect **already** produces: the per-AC design-element mapping (AC -> concrete element) in `traceability.html`, plus the `Depends-on` column. A prerequisite that unblocks two or more ACs is visible as **two or more ACs sharing the same dependency**. The Architect role and its templates are **unchanged**; the BA reads the existing traceability to fill this lane. (Do not assume a dedicated "pending items" surface exists — derive from the design-element mapping + shared dependencies.)

## 7. Lifecycle — who writes when (every write is a BA dispatch)

1. **At the Spec phase** (card-keyed work): BA writes one row per AC with `Readiness` (mirrored from the AC), `Build = pending`, and `Depends-on` (from each AC's `Blocker:` id).
2. **Sub-tasks + Shared-prerequisites — fill them whenever the design exists on disk**, i.e. whenever `docs/design/<usecase>/traceability.html` is present (**NOT** only when the Design phase ran in this session — a re-run on an already-analysed card has it on disk): read its per-AC design-element mapping -> fill sub-task checklists for big ACs + the Shared-prerequisites lane. **Also seed the Shared-prerequisites lane from the shared `Blocker:` refs** already in the file — two or more ACs sharing a blocker/dependency are a shared prerequisite, derivable even before any traceability exists.
3. **After each Dev-Loop batch exits green**: the orchestrator dispatches BA in **tracker-sync** mode to set those ACs' `Build = done` and tick their sub-tasks. Updating per batch (not only at the end) keeps progress crash-resilient across sessions.
4. **At Blocker-resolved re-entry**: after the existing re-entry flow mutates the AC document (`Blocked -> Ready`), the **same** BA dispatch mirrors the promoted ids into the task-file (`Readiness -> Ready`, **preserve** `Build`).

**Defer only when design is genuinely absent.** If no `traceability.html` exists yet (a true greenfield Spec-only run), write the skeleton — still seed the Shared-prerequisites lane from shared `Blocker:` refs — and note `sub-task checklists pending Design`. **Never write "pending Design" when `traceability.html` already exists on disk** (a re-run on an already-analysed card): fill the sub-tasks immediately. (Build cannot occur in a Spec-only run anyway, so the skeleton state is still valid.)

## 8. Completeness sweep — include the task-file

For a **scoped change** that retires or renames an AC id on card-keyed work, the stale-reference completeness sweep (the same grep the doc roles run for retire / rename tasks) must also cover `docs/tasks/<card-id>/plan.md` — a retired AC id left in the task-file is a stale reference. Markdown only; never convert it to `.html` to "match" the design docs.

## 9. Sections beyond the table — Notes (optional), no copied blockers

Beyond the header, roll-up, `Shared prerequisites`, and `Tasks` table, the task-file may end with **one optional `Notes` section** — a few lean tracking-level bullets (e.g. the All-Blocked-guard status, cross-AC build order, a "this blocker is independent" caveat). Keep it scannable: bullets, not prose.

Do **not** add a `Blockers` section that copies each AC's blocker text out of the AC document. Blocker detail is owned by the AC document (the `<blocker>` body is the source of truth); duplicating it here is redundant, drifts out of sync when the AC changes, and breaks the "tracking index, not prose" rule. The task-file captures the blocker only as **structure** — the `Depends-on` column (the dependency id) and the `Shared prerequisites` lane (the pending work); for the full reason an AC is blocked, the reader follows `Source AC`.
