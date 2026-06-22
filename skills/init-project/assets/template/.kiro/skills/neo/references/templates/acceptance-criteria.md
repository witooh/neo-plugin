# Acceptance Criteria — [Usecase Name]

**Usecase folder:** `docs/design/[usecase]/`
**Version:** [version]
**Created Date:** [date]
**Created By:** Business Analyst
**Version History:** see `docs/design/VERSION.md`

---

## Output Format — interactive HTML

This document is emitted as **`acceptance-criteria.html`** (interactive HTML), **not** markdown. **Build it per [`html-output.md`](../html-output.md)** — every rule below defines the CONTENT (which ACs, ordering, fields, status); the HTML guide defines the FORM (components, page shell, stamping, verify). Do not emit a `.md` file. The markdown structure shown below is the **content spec** — read it for fields/ordering, then render as HTML using this mapping:

- Each AC → **`<ac-card>`** (custom element in `assets/js/components.js`): `<ac-card id="AC-NNN" status="ready|blocked" priority traces subop jira label>` with child `<g>/<w>/<t>` (+ `<a>`) for GIVEN/WHEN/THEN, `<rule>` for the business rule, and optional `<blocker>`. It expands to the canonical `.card` (`is-<status>` + every `data-*` + badge/chips/chevron + `.gwt` + field-rows) — **status/priority/traces written ONCE then derived, so they can't drift**. Full HTML form + rendered structure: `html-output.md` §5.
- Business Rule (`<rule>` child), JIRA Ref (`jira=` attr) and Priority/Status (derived) render as **`dl.field-row`s** inside `.card__body`; a Blocker (`<blocker>` child) renders a `.callout[data-kind="blocked"]` — all emitted by the element; you supply only the children/attrs.
- AC Summary → **`<ac-summary>`** with one **`<ac ref="AC-NNN" subop rule [blocker]>`** per AC. Scenario/Priority/Status/JIRA are **derived from the matching `<ac-card>`** (written once on the card → can't drift): Status → `.status-badge`, Priority → `.chip[data-tone="p0|p1"]` (P2 = plain `.chip`), JIRA → `.chip[data-tone="jira"]`. You author only `subop` (sub-operation name; omit → "—") and `rule` (short Business-Rule ref); `blocker="<dep>"` appends "(blocked by <dep>)" to the rule cell. Renders `.table-wrap > table.data-table[data-sortable]`. The section's **Total line → `<ac-total></ac-total>`** (empty) — counts the page's `<ac-card>`s by status, so "Total Acceptance Criteria: N (Ready: R / Blocked: B)" can't go stale.
- Business Rules / Edge Cases / Out of Scope → `h2` + lists. **Apply [`html-output.md`](../html-output.md) §5.1 before any `<callout-box>`** — version/changelog and doc-vs-code-gap notes do NOT belong on the page (they fail `docverify.py`).
- **Notes** (the `## Notes` section below) → a single **`<h2 id="notes">Notes</h2>` + `<ul>`** at the page end — the ONLY home for cross-cutting spec notes (§5.1). `id="notes"` is load-bearing; omit the section when there are none.
- Also create the usecase's `index.html` overview and register the usecase group in `nav.js` (html-output.md §4, §9).
- **Verify:** run `python3 <ASSET_DIR>/lint.py docs/design` then `python3 <ASSET_DIR>/docverify.py docs/design/<usecase>` until `PASS — 0 error(s)`, then the semantic self-check (html-output.md §7). In `<g>/<w>/<t>/<rule>` prose, inline `<b>`/`<code>` are fine but **bare `&` → `&amp;`** (§6).

---

**Usecase Scope Rule:** 1 AC document = 1 usecase folder. See `~/.kiro/agents/business-analyst.md` § Determinism Rules (**Usecase Scope** + **Folder Organization**) for the full decision tree (when to append vs. when to create a new usecase folder, folder-naming smell patterns).

If this usecase has **multiple sub-operations** (e.g., `management/` covers CRUD parent + version + activate), group ACs under `## Sub-operation N:` headings below. For simple usecases with a single operation, skip Sub-operation headings and list ACs directly under the Acceptance Criteria section.

## Sub-operation 1: [Sub-operation Name]

_(Optional heading — include only when the usecase has multiple sub-operations. Skip for single-operation usecases.)_

### User Story

As a [actor / role],
I want to [action],
So that [business value].

### Acceptance Criteria

**Scenario Ordering Rule — AC-IDs MUST follow this fixed order:**

1. **Happy paths** — successful end-to-end flows (AC-001, AC-002, ...)
2. **Input validation errors** — format, missing fields, type mismatch
3. **External service errors** — third-party API rejection, timeout, unavailable
4. **Domain logic errors** — OTP incorrect, OTP expired, attempt limits
5. **State guard errors** — locked, already completed, duplicate prevention
6. **Cross-cutting concerns** — audit logging, notifications (always as a single combined AC per concern, never split by outcome)

Number AC-IDs sequentially within this order (AC-001, AC-002, ...). Never reorder scenarios outside these groups.

**Audit Logging Rule:** Audit logging is always ONE combined AC that covers both success and failure outcomes. Never split audit into separate ACs per outcome type (e.g., do not create separate ACs for "audit success" and "audit failure").

**Status Semantics — every AC has a dependency-readiness status (`Ready` | `Blocked`).** Full rules: [`~/.kiro/skills/neo/references/shared/ac-status.md`](../shared/ac-status.md). In brief — **Ready** (default): all upstream artifacts exist; flows through Architect → QA → Developer normally. **Blocked**: depends on a contract/artifact from another work item not yet finalized; documented for visibility, excluded from the Dev Loop until resolved, and MUST declare a `Blocker` field (dependency-readiness only, NOT progress tracking). When `Status: Blocked`, the orchestrator skips Developer for that AC, has QA generate an `@blocked`-tagged test case, and reports it in the Pre-Finalization Checklist's "Blocked ACs" section.

---

#### AC-001: [Scenario name — happy path]

**GIVEN** [initial context / precondition]
**WHEN** [action is taken]
**THEN** [expected outcome]
**AND** [additional outcome if needed]

**Business Rule:** [underlying rule this validates — must be explicit and testable]
**Priority:** P0 (Critical) | P1 (High) | P2 (Medium)
**Status:** Ready | Blocked
**Blocker:** [REQUIRED when Status=Blocked — format: `<ticket-id-or-artifact-ref> — <what's missing>`. OMIT this line entirely when Status=Ready]
**JIRA Ref:** [OPTIONAL — one or more JIRA card IDs that originated or track this AC. Format: comma-separated IDs (e.g., `PROJ-123` or `PROJ-123, PROJ-456`). OMIT this line entirely when no JIRA reference exists]

---

#### AC-002: [Scenario name — error/edge case]

**GIVEN** [initial context / precondition]
**WHEN** [action is taken]
**THEN** [expected outcome — include specific error code/message if applicable]

**Business Rule:** [underlying rule this validates]
**Priority:** P0 (Critical) | P1 (High) | P2 (Medium)
**Status:** Ready | Blocked
**Blocker:** [REQUIRED when Status=Blocked — format: `<ticket-id-or-artifact-ref> — <what's missing>`. OMIT this line entirely when Status=Ready]
**JIRA Ref:** [OPTIONAL — comma-separated JIRA card IDs; OMIT this line entirely when no JIRA reference exists]

---

### Business Rules

1. [rule 1 — explicit, testable, no ambiguity]
2. [rule 2 — if it involves validation, state exactly what values are valid/invalid]
3. [rule 3 — if it involves state transitions, list all valid transitions]

### Edge Cases

Cover at minimum these categories (skip only if genuinely not applicable):

1. **Empty/missing input** — empty strings, null, missing fields
2. **Whitespace/formatting** — leading/trailing whitespace, unexpected characters
3. **Concurrent requests** — same user sends multiple requests simultaneously
4. **Post-expiry behavior** — action attempted after a time-based lock/expiry ends
5. **Unexpected external errors** — third-party returns non-standard error (not timeout, not rejection)
6. **Boundary values** — exact limit (e.g., correct input on last attempt before lock)
7. **No active session** — action attempted without prerequisite step (e.g., submit OTP without requesting verification)

List edge cases in this category order. For each, include the expected behavior.

### Out of Scope

- [what is explicitly NOT included in this usecase]

---

## Sub-operation 2: [Sub-operation Name]

_(Repeat the same structure for each sub-operation. Omit this section entirely when the usecase has only one operation.)_

---

## AC Summary

| ID | Sub-operation | Scenario | Priority | Status | JIRA Ref | Business Rule |
|----|---------------|----------|----------|--------|----------|---------------|
| AC-001 | [sub-operation or "—" if single-op] | [scenario name] | P0 | Ready | PROJ-123 | [short rule ref] |
| AC-002 | [sub-operation or "—" if single-op] | [scenario name] | P1 | Blocked | PROJ-123, PROJ-456 | [short rule ref] (blocked by GI-XX) |

_When Status=Blocked, append the Blocker reference to the Business Rule cell as `(blocked by <dependency-id>)` so readers can scan dependencies without opening every AC._

_The JIRA Ref column mirrors the per-AC `JIRA Ref:` field. Write a comma-separated ID list when one or more refs exist (e.g., `PROJ-123` or `PROJ-123, PROJ-456`). Write `—` (em dash, not blank, not `N/A`) when the AC has no JIRA reference._

**Total Acceptance Criteria:** N  (Ready: R / Blocked: B)

---

## Notes

- [dependency notes, assumptions, or open questions]
- [if sourced from an existing design doc, reference it here: e.g., "Derived from docs/solution-design.md Section 3.2"]
