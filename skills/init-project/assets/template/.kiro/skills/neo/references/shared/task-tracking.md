# Shared: Task Tracking — Build Progress Axis + the Card Task-File

**Single source of truth for the `Build` progress axis, the `Build Plan` (the developer work-breakdown), and the per-card task-file (`docs/tasks/<card-id>/plan.md`).** Referenced by the Business Analyst (the sole writer of the task-file) and the Orchestrator (reads it to route + resume card-keyed work). This file owns the **definitions**; the role/SKILL prose that cites it keeps its own enforcement.

**This is NOT the `Status` field.** `ac-status.md` §1 is explicit: the AC `Status` encodes **dependency-readiness** (`Ready | Blocked`), never progress, and never any other value. The `Build` axis defined here is a **separate, orthogonal** dimension — it records *implementation progress*, lives **only** in the task-file (never in the AC document), and must never be written into the AC's `Status` field. Readiness answers "can this AC be implemented now?"; Build answers "has it been implemented + verified yet?".

## 1. Scope — card-keyed work only

The task-file exists **only** for work that carries a JIRA card ID. Ad-hoc / general requests (no card) keep the existing flow and never get a task-file. For card-keyed work the task-file is **mandatory before the Build phase** — the orchestrator enforces this with a pre-Build guard that mirrors the All-Blocked guard (an unnamed routing check, not a numbered gate): card-keyed work with no current task-file → the orchestrator dispatches BA to create it before any Build.

**One AC document, many cards.** A usecase's AC document can be shared by several cards (e.g. sub-operations each tracked by a different card). Card X's task-file lists **only the ACs that card X tracks** — those whose AC `JIRA Ref` (the ac-card `jira` value) includes X — not every AC in the document. Scope the rows from the `jira` field, never the document as a whole. **Pointer / cross-ref ACs:** an AC pulled in only because it cross-references this card while its real implementation is another AC (e.g. `AC-014` is a pointer to `AC-007`) still gets its row, but its `Build` is the reference `→ AC-007` (not a progress value) and it is **excluded from both roll-up tallies** (`Readiness` and `Build`) — a visibility row, not a counted work item, so the work and its readiness are tallied once on the AC that owns it. Its row still shows the mirrored `Readiness` value so the cross-reference stays visible.

## 2. The task-file — `docs/tasks/<card-id>/plan.md`

- **One markdown file per card.** Markdown **by design** — the orchestrator reads it to route/resume, exactly as it reads `docs/design/INDEX.md` / `VERSION.md`. It is **out of scope of `lint.py` / `docverify.py`** and is a registered markdown exception (`html-output.md` §8). **Never** author it as `.html`; never point the HTML verifiers at `docs/tasks/`.
- **Sole writer = Business Analyst.** The Developer and QA produce deliverables (code, test docs), not tracking state; the orchestrator is write-forbidden. So every task-file write/refresh is a BA dispatch. Content spec: `~/.kiro/skills/neo/references/templates/task-file-template.md`.
- **Reader = the orchestrator**, to decide resume vs. fresh and to scope continued work. Humans read it as the card's resume index.

## 3. Columns (per AC row)

| Column | Owns | Source |
|---|---|---|
| `Readiness` | a mirror of the AC `Status` (`Ready`/`Blocked`) | the AC document — read, not re-derived |
| `Build` | the progress axis — `pending` -> `in-progress` -> `done` | the task-file (the state machine in §4) |
| `Depends-on` | cross-AC ordering (e.g. AC-002 needs AC-019) | the AC's `Blocker:` dependency id (`ac-status.md` §2 format) + obvious build order |

`Readiness` is a **mirror, not a second writer** of readiness: the AC document stays the source of truth; the task-file copies it. When readiness changes (a blocker resolves), the same BA dispatch that mutates the AC document also refreshes this column (see §7).

**The dev work-breakdown is not a column.** Buildable steps live in the `## Build Plan` section (§5) **above** the Tasks table — one work-item list in build order — not crammed into a table cell. The Tasks table stays a per-AC status/resume index; the Build Plan is the per-work-item dev view.

## 4. `Build` state machine

- `pending` — not started (the default at task-file creation).
- `in-progress` — the Dev Loop has begun this AC but it has not yet exited green.
- `done` — the AC's Dev Loop has **exited green** (its E2E passes and code review + security are clean — the same exit condition the orchestrator already uses). `done` means **built + verified**, not merely "code written".

A `Blocked` AC (Readiness) cannot reach `in-progress` / `done`; it stays `pending` until its blocker resolves and it is promoted to `Ready` via the existing Blocker-resolved re-entry flow. Progress is never inferred from readiness, and readiness is never inferred from progress.

## 5. Build Plan — the dev work-breakdown (the dev surface)

The `## Build Plan` section is the card's **developer work-breakdown** — buildable work in **build order**, where the unit is a **code change / surface, not an AC**. It **replaces** the former per-AC sub-task checklists **and** the Shared-prerequisites lane (both are absorbed here), so all "what to build / which layer / what order" lives in **one** place instead of scattered across sub-task sections, a prereq table, and Notes. Place it **above** the `## Tasks` table; the Tasks table stays the per-AC status/resume index.

Two tiers:
- **`### Ready to build now`** — one item per buildable unit whose serving AC(s) are all `Readiness = Ready` and not yet `done`. A **vertical GFM checklist** (`- [ ]` / `- [x]`) — ticking gives intra-AC / intra-session resume (the role the old sub-task checkboxes played). Each item names its **layer · file/method** and the **AC-IDs it serves**; list order **is** build order (no order column). A small single-surface AC gets a one-line item too — there is **no "big-AC only" gate** (every Ready, unbuilt unit is a line), which is what stops most ACs from being invisible work. Empty tier → write `none — all unblocked work done; see Blocked on upstream`.
- **`### Blocked on upstream`** — buildable work gated by a pending upstream field / contract (the absorbed Shared-prerequisites lane). A **table** `Work item | Unblocks AC | Waits for`. **Not** elaborated to file level — a blocked item is far from build, and file-level detail on far work only drifts.

**Done** items are not duplicated elsewhere — the Tasks-table `Build = done` is the record; in the Build Plan they read `- [x]`. **Pointer / cross-ref ACs** (e.g. `AC-014 → AC-007`, §1) contribute **no** Build Plan item — their work belongs to the target AC's item. **Multi-card:** a card's Build Plan lists only items serving the ACs that card tracks (§1).

## 6. Build Plan derivation + drift containment

**Derivation — no new Architect artifact.** Both tiers come from data the Architect **already** produces in `traceability.html`: the **`### Ready to build now`** items from the per-AC design-element mapping (the `AC -> File / Method` table — the concrete layer/file each Ready AC touches); the **`### Blocked on upstream`** table from the "Pending Items Surface" (`Pending item | Blocks AC | Surface area`) plus shared `Depends-on` (two or more ACs sharing a blocker = one shared item that unblocks them all). The Architect role and its templates are **unchanged**; the BA reads the existing traceability to fill both tiers. (Where no dedicated "pending items" surface exists, derive the blocked tier from the design-element mapping + shared dependencies.)

**Build-window scoping (the drift control).** Only the **`### Ready to build now`** tier is elaborated to layer/file — it is the small, short-lived set of work actually in front of the developer. Blocked items stay coarse (surface area, no file detail); done items are not re-stated. So the synced, drift-prone surface stays minimal: the BA **regenerates** the Build Plan from traceability on each refresh rather than hand-maintaining a parallel copy.

**Two progress views stay consistent.** The Tasks-table `Build` (§4) is the **canonical per-AC** progress (`done` only when the Dev Loop exits green); the Build Plan checklist is the finer **per-item** breakdown. An AC's serving items being built ⟺ that AC is built, so the two never contradict — and the BA writes **both** in the same tracker-sync dispatch (§7), never as two independent writers.

## 7. Lifecycle — who writes when (every write is a BA dispatch)

1. **At the Spec phase** (card-keyed work): BA writes one row per AC with `Readiness` (mirrored from the AC), `Build = pending`, and `Depends-on` (from each AC's `Blocker:` id).
2. **Build Plan — fill it whenever the design exists on disk**, i.e. whenever `docs/design/<usecase>/traceability.html` is present (**NOT** only when the Design phase ran in this session — a re-run on an already-analysed card has it on disk): read its per-AC design-element mapping + Pending Items Surface -> fill both Build Plan tiers (§5–§6). **Also seed the `Blocked on upstream` tier from the shared `Blocker:` refs** already in the file — two or more ACs sharing a blocker/dependency are one shared item, derivable even before any traceability exists.
3. **After each Dev-Loop batch exits green**: the orchestrator dispatches BA in **tracker-sync** mode to set those ACs' `Build = done` **and** tick their `### Ready to build now` items (`- [x]`). Updating per batch (not only at the end) keeps progress crash-resilient across sessions.
4. **At Blocker-resolved re-entry**: after the existing re-entry flow mutates the AC document (`Blocked -> Ready`), the **same** BA dispatch mirrors the promoted ids into the task-file (`Readiness -> Ready`, **preserve** `Build`) **and moves their Build Plan items from `### Blocked on upstream` to `### Ready to build now`** (elaborating them to layer/file now that they are buildable).

**Defer only when design is genuinely absent.** If no `traceability.html` exists yet (a true greenfield Spec-only run), write the skeleton — still seed the `Blocked on upstream` tier from shared `Blocker:` refs — and note `Build Plan pending Design`. **Never write "pending Design" when `traceability.html` already exists on disk** (a re-run on an already-analysed card): fill the Build Plan immediately. (Build cannot occur in a Spec-only run anyway, so the skeleton state is still valid.)

## 8. Completeness sweep — include the task-file

For a **scoped change** that retires or renames an AC id on card-keyed work, the stale-reference completeness sweep (the same grep the doc roles run for retire / rename tasks) must also cover `docs/tasks/<card-id>/plan.md` — a retired AC id left in the task-file is a stale reference. Markdown only; never convert it to `.html` to "match" the design docs.

## 9. Sections beyond the table — Notes (optional), nothing re-narrated from elsewhere

Beyond the header, roll-up, `Build Plan`, and `Tasks` table, the task-file may end with **one optional `Notes` section** — a few lean tracking-level bullets (e.g. the All-Blocked-guard status, cross-AC build order, a "this blocker is independent" caveat). Keep it scannable: bullets, not prose.

**A Notes bullet earns its place only when it is tracking-level structure with no other home.** Anything already **owned elsewhere** is referenced — by id / column / section — **never re-narrated** here; re-narrating it is redundant, drifts out of sync when the source changes, and breaks the "tracking index, not prose" rule:

- a **blocker** → owned by the AC document (the `<blocker>` body); captured here only as the `Depends-on` column + the Build Plan `### Blocked on upstream` tier. **Never a `Blockers` section** copying the AC's blocker text; for the full reason an AC is blocked, the reader follows `Source AC`.
- a **decision / resolution / ADR** → owned by its decision record (the ADR · the `VERSION.md` changelog · `gap-analysis.md`); cite it by id, do not restate the rationale, who-approved, or the chosen-vs-rejected options.
- **what was built / progress** → owned by the `Tasks`-table `Build` column + the Build Plan item (its `- [x]` and any built-here note); don't add a parallel status / "what landed" narrative in Notes.
- a **changelog** → `VERSION.md`; a **doc-vs-code gap** → `gap-analysis.md`.

**No duplication with the Build Plan.** A Notes bullet must not restate what a Build Plan item already owns (its `layer · file/method · serves AC` detail) — §5's "Done items are not duplicated elsewhere" binds Notes too. When in doubt, cut the bullet and let the reader follow the id.
