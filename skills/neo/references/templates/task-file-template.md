# Task File — [CARD-ID]

**File:** `docs/tasks/<card-id>/plan.md` (one folder per JIRA card; `<card-id>` = the card id, e.g. `GI-52`).
**Format:** **Markdown, never HTML.** This is a deliberate exception to the "design docs are HTML" rule — registered in [`../html-output.md`](../html-output.md) §8. The orchestrator reads it to route/resume, exactly like `docs/design/INDEX.md` / `VERSION.md`. It is **out of scope of `lint.py` / `docverify.py`** — do not run those against `docs/tasks/`, and never author this file as `.html`.
**Written by:** Business Analyst (sole writer). **Read by:** the Orchestrator (route/resume) + humans (resume index).
**Semantics / state machine:** [`../shared/task-tracking.md`](../shared/task-tracking.md). **Scope:** card-keyed work only.

---

## Content spec

Emit `plan.md` with this exact section order. Keep it scannable — it is a tracking index, not prose.

```
# <CARD-ID> - <card title>          [resume index for neo - markdown by design]

Source AC: ../../design/<usecase>/acceptance-criteria.html
Readiness: <R>/<N> Ready   |   Build: <done> done, <wip> in-progress, <rest> pending
Updated: <session marker or YYYY-MM-DD>

## Shared prerequisites

| Prereq                       | Build       | Unblocks               |
|------------------------------|-------------|------------------------|
| <prereq name>                | pending     | AC-NNN, AC-MMM         |

## Tasks

| AC-ID  | Readiness | Build       | Depends-on |
|--------|-----------|-------------|------------|
| AC-001 | Ready     | done        | -          |
| AC-002 | Blocked   | pending     | AC-019     |
| AC-014 | Ready     | → AC-007    | AC-007     |
| AC-016 | Ready     | in-progress | -          |
| AC-019 | Blocked   | pending     | -          |

### AC-016 — sub-tasks
- [x] layer 1
- [x] layer 2
- [ ] layer 3

### AC-019 — sub-tasks
- [ ] step a
- [ ] step b
- [ ] step c

## Notes

- <lean tracking note — e.g. All-Blocked-guard status, build order, an independence caveat>
- <omit this whole section when there is nothing tracking-level to say>
- (never a `Blockers` section — blocker detail stays in the AC document; §9)
```

### Field rules

- **Header line** — `<CARD-ID>` plus a short title; keep the `[resume index ...]` tag so a reader knows it is machine-read and markdown-by-design.
- **`Source AC`** — relative path to the usecase `acceptance-criteria.html` this card maps to (the AC document is the source of `Readiness`).
- **Roll-up line** — counts are over **this card's tracked rows** (a subset of the AC document when the doc is shared by several cards), **excluding pointer rows** (`Build = → AC-NNN`): `Readiness` = Ready / total-tracked, `Build` = done / in-progress / pending. For a single-card usecase this equals the AC document's `(Ready: R / Blocked: B)` tail. Both must match the rows below (no stale roll-up).
- **`Shared prerequisites` section** — work that unblocks **two or more** ACs (`task-tracking.md` §6), derived from the Architect `traceability.html` design-element mapping + shared `Depends-on`. **Omit the whole section** when there are none (e.g. a Spec-only skeleton before Design). `Unblocks` lists the AC ids it gates.
- **`Tasks` table — one row per tracked AC:**
  - `AC-ID` — every AC id **whose `JIRA Ref` includes this card**, in document order (one AC document shared by N cards → each card lists only the ACs it tracks; `../shared/task-tracking.md` §1). A **pointer / cross-ref AC** (its work is another AC, e.g. `AC-014` → `AC-007`) still gets a row — see `Build`.
  - `Readiness` — `Ready` or `Blocked`, **mirrored verbatim** from the AC `Status` (never re-derived). This column is **not** the AC `Status` field; it is a copy. Never write a progress value here.
  - `Build` — `pending` / `in-progress` / `done` (the progress axis, `task-tracking.md` §4). A `Blocked` row stays `pending`. A **pointer AC** carries the reference `→ AC-NNN` instead of a progress value and is **excluded from the roll-up counts** (`../shared/task-tracking.md` §1).
  - `Depends-on` — the AC id(s) this AC must follow (from its `Blocker:` dependency id or obvious build order); `-` when none.
- **`### <AC-ID> — sub-tasks` sections (below the `Tasks` table)** — a **big AC** (`task-tracking.md` §5) gets one: a vertical GFM checklist (`- [ ]` / `- [x]`), one section per big AC in document order, placed after the table and before `## Notes`. Most ACs are not big and get **no** section. **Never** put checkboxes in a table cell. Before Design exists, emit no sub-task sections and add the one-line note `sub-task checklists pending Design` under `## Notes`.
- **`## Notes` (optional)** — the file may end with a few lean tracking bullets (guard status, build order, an independence caveat); bullets, not prose (`../shared/task-tracking.md` §9). **Do NOT** add a `Blockers` section copying the AC document's blocker text — blocker detail lives in the AC document; the task-file carries it only as the `Depends-on` column + the `Shared prerequisites` lane.

### Authoring notes

- **No `Status` column.** `Status` is reserved by `ac-status.md` §1 (readiness, `Ready`/`Blocked`); reusing the name here would collide. Use `Readiness` + `Build`.
- **Language-neutral.** Fill content in the consuming project's working language; this template ships no hardcoded language.
- **Preserve on refresh.** When refreshing (post-Design, tracker-sync, re-entry), keep prior `Build` values and ticked sub-task checkboxes (in their sections); only update what changed.
