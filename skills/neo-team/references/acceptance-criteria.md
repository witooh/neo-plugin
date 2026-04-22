# Acceptance Criteria — [Usecase Name]

**Usecase folder:** `docs/design/[usecase]/`
**Version:** [version]
**Created Date:** [date]
**Created By:** Business Analyst
**Version History:** see `docs/design/VERSION.md`

---

**Usecase Scope Rule:** 1 AC document = 1 usecase folder. See `business-analyst.md` § Usecase Scope Rule and § Folder Organization Rule for the full decision tree (when to append vs. when to create a new usecase folder, folder-naming smell patterns).

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

---

#### AC-001: [Scenario name — happy path]

**GIVEN** [initial context / precondition]
**WHEN** [action is taken]
**THEN** [expected outcome]
**AND** [additional outcome if needed]

**Business Rule:** [underlying rule this validates — must be explicit and testable]
**Priority:** P0 (Critical) | P1 (High) | P2 (Medium)

---

#### AC-002: [Scenario name — error/edge case]

**GIVEN** [initial context / precondition]
**WHEN** [action is taken]
**THEN** [expected outcome — include specific error code/message if applicable]

**Business Rule:** [underlying rule this validates]
**Priority:** P0 (Critical) | P1 (High) | P2 (Medium)

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

| ID | Sub-operation | Scenario | Priority | Business Rule |
|----|---------------|----------|----------|---------------|
| AC-001 | [sub-operation or "—" if single-op] | [scenario name] | P0 | [short rule ref] |
| AC-002 | [sub-operation or "—" if single-op] | [scenario name] | P1 | [short rule ref] |

**Total Acceptance Criteria:** N

---

## Notes

- [dependency notes, assumptions, or open questions]
- [if sourced from an existing design doc, reference it here: e.g., "Derived from docs/solution-design.md Section 3.2"]
