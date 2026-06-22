# Task File — [CARD-ID]

**File:** `docs/tasks/<card-id>/plan.md` (one folder per JIRA card; `<card-id>` = the card id, e.g. `GI-52`).
**Format:** **Markdown, never HTML.** This is a deliberate exception to the "design docs are HTML" rule — registered in [`~/.kiro/skills/neo/references/html-output.md`](../html-output.md) §8. The orchestrator reads it to route/resume, exactly like `docs/design/INDEX.md` / `VERSION.md`. It is **out of scope of `lint.py` / `docverify.py`** — do not run those against `docs/tasks/`, and never author this file as `.html`.
**Written by:** Business Analyst (sole writer). **Read by:** the Orchestrator (route/resume) + humans (resume index).
**Semantics / state machine:** [`~/.kiro/skills/neo/references/shared/task-tracking.md`](../shared/task-tracking.md). **Scope:** card-keyed work only.

---

## Content spec

Emit `plan.md` with this exact section order. Keep it scannable — it is a tracking index, not prose.

```
# <CARD-ID> - <card title>          [resume index for neo - markdown by design]

Source AC: ../../design/<usecase>/acceptance-criteria.html
Readiness: <R>/<N> Ready   |   Build: <done> done, <wip> in-progress, <rest> pending
Updated: <session marker or YYYY-MM-DD>

## Build Plan

### Ready to build now
- [ ] <work item> — <layer · file/method> · serves AC-NNN
- [x] <built item>  — <layer · file/method> · serves AC-MMM
(empty → `none — all unblocked work done; see Blocked on upstream`)

### Blocked on upstream

| Work item                    | Unblocks AC     | Waits for                  |
|------------------------------|-----------------|----------------------------|
| <shared work item>           | AC-NNN/MMM      | <pending upstream field>   |

## Tasks

| AC-ID  | Readiness | Build       | Depends-on |
|--------|-----------|-------------|------------|
| AC-001 | Ready     | done        | -          |
| AC-002 | Blocked   | pending     | AC-019     |
| AC-014 | Ready     | → AC-007    | AC-007     |
| AC-016 | Ready     | in-progress | -          |
| AC-019 | Blocked   | pending     | -          |

## Notes

- <lean tracking note — e.g. All-Blocked-guard status, build order, an independence caveat>
- <omit this whole section when there is nothing tracking-level to say>
- (never re-narrate owned-elsewhere content — a blocker / decision / ADR lives in its own source; §9)
```

### Field rules

- **Header line** — `<CARD-ID>` plus a short title; keep the `[resume index ...]` tag so a reader knows it is machine-read and markdown-by-design.
- **`Source AC`** — relative path to the usecase `acceptance-criteria.html` this card maps to (the AC document is the source of `Readiness`).
- **Roll-up line** — counts are over **this card's tracked rows** (a subset of the AC document when the doc is shared by several cards), **excluding pointer rows** (`Build = → AC-NNN`): `Readiness` = Ready / total-tracked, `Build` = done / in-progress / pending. For a single-card usecase this equals the AC document's `(Ready: R / Blocked: B)` tail. Both must match the rows below (no stale roll-up).
- **`## Build Plan` section (above the `Tasks` table)** — the developer work-breakdown (`task-tracking.md` §5–§6), derived from the Architect `traceability.html` (`#ac-design` File/Method + `#pending` Surface area). Two tiers: **`### Ready to build now`** = a vertical GFM checklist (`- [ ]` / `- [x]`), one line per buildable unit whose serving AC(s) are all `Ready` and unbuilt, each naming `layer · file/method · serves AC-IDs`, list order = build order, with **no "big-AC only" gate** (small ACs get a one-line item too); empty → write `none — all unblocked work done; see Blocked on upstream`. **`### Blocked on upstream`** = a table `Work item | Unblocks AC | Waits for` for work gated by a pending upstream field / contract (not elaborated to file level). **Pointer ACs** contribute no item; **done** items read `- [x]` and are not re-stated elsewhere. Before Design exists, emit only a seeded `Blocked on upstream` tier (from shared `Blocker:` refs) + the note `Build Plan pending Design` under `## Notes`.
- **`Tasks` table — one row per tracked AC:**
  - `AC-ID` — every AC id **whose `JIRA Ref` includes this card**, in document order (one AC document shared by N cards → each card lists only the ACs it tracks; `~/.kiro/skills/neo/references/shared/task-tracking.md` §1). A **pointer / cross-ref AC** (its work is another AC, e.g. `AC-014` → `AC-007`) still gets a row — see `Build`.
  - `Readiness` — `Ready` or `Blocked`, **mirrored verbatim** from the AC `Status` (never re-derived). This column is **not** the AC `Status` field; it is a copy. Never write a progress value here.
  - `Build` — `pending` / `in-progress` / `done` (the progress axis, `task-tracking.md` §4). A `Blocked` row stays `pending`. A **pointer AC** carries the reference `→ AC-NNN` instead of a progress value and is **excluded from the roll-up counts** (`~/.kiro/skills/neo/references/shared/task-tracking.md` §1).
  - `Depends-on` — the AC id(s) this AC must follow (from its `Blocker:` dependency id or obvious build order); `-` when none.
- **`## Notes` (optional)** — the file may end with a few lean tracking bullets (guard status, build order, an independence caveat); bullets, not prose (`~/.kiro/skills/neo/references/shared/task-tracking.md` §9). A bullet earns its place only as tracking-level structure with **no other home**. **Do NOT re-narrate anything owned elsewhere** — a blocker (AC document), a decision / ADR (its decision record · `VERSION.md` · `gap-analysis.md`), or progress / what-landed (the `Build` column + the Build Plan item): reference it by id / column / section, never copy its prose, and never duplicate a Build Plan item. (No `Blockers` section.)

### Authoring notes

- **No `Status` column.** `Status` is reserved by `ac-status.md` §1 (readiness, `Ready`/`Blocked`); reusing the name here would collide. Use `Readiness` + `Build`.
- **Language-neutral.** Fill content in the consuming project's working language; this template ships no hardcoded language.
- **Preserve on refresh.** When refreshing (post-Design, tracker-sync, re-entry), keep prior `Build` values and ticked Build Plan checkboxes; only update what changed.
