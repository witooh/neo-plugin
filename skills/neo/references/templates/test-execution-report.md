# Output Format — interactive HTML

This execution report is emitted as **`test-report.html`** (interactive HTML), **not** markdown. **Build per [`html-output.md`](../html-output.md)** — the worked example below is the CONTENT spec; the guide is the FORM. Mapping:

- Each result → `div.card` with `id="TC-NNN"` + `data-status`; Expected / Actual / Status / Executed Date / JIRA Ref / Defect Ref / Notes → `dl.field-row`s.
- Status badge mapping (only `ready|blocked|pending` exist): **✅ Pass → `data-status="ready"`**, **❌ Fail → `data-status="blocked"`**, **⏸ Deferred / ⚠️ Blocked → `data-status="pending"`**. Keep the ✅/❌/⏸ emoji in the text too.
- Execution Summary / Defect Summary / Deferred Test Cases → `table.data-table[data-sortable]`.
- Pass / Fail / Blocked / Not-Run / Deferred totals → `.stat-grid` > `.stat-card` (optionally a `.bar` > `.bar__seg.ready|.blocked`). The `⏸ Deferred` count covers `@blocked` TCs (which are also listed in the separate Deferred Test Cases table); omit the Deferred stat-card when the count is 0.
- **Verify:** `python3 <ASSET_DIR>/lint.py docs/design` until `PASS`. Escape `<`/`>`/`&` in prose (§6).

---

**Module:** Savings Account
**Version:** 1.0.0
**Execution Date:** 2026-03-17
**Build / Release:** v1.2.0

---

## Test Suite 1: Product Configuration

---

#### TC-001: Configuring the primary denomination of the product

**Expected Result:** Product is saved with denomination = THB
**Actual Result:** Product is saved with denomination = THB as expected
**Status:** ✅ Pass
**Executed Date:** 2026-03-17
**JIRA Ref:** PROJ-123
**Defect Ref:** N/A
**Notes:** -

---

#### TC-002: Account opening with configured primary denomination

**Expected Result:** HTTP 200, account status = OPEN, denomination = THB
**Actual Result:** HTTP 200, account status = OPEN, denomination = THB
**Status:** ✅ Pass
**Executed Date:** 2026-03-17
**JIRA Ref:** PROJ-123, PROJ-456
**Defect Ref:** N/A
**Notes:** -

---

## Test Suite 2: Transaction Validation

---

#### TC-003: Accepting a credit or debit in a primary denomination

**Expected Result:** HTTP 200, transaction status = ACCEPTED
**Actual Result:** HTTP 200, transaction status = ACCEPTED
**Status:** ✅ Pass
**Executed Date:** 2026-03-17
**JIRA Ref:** PROJ-789
**Defect Ref:** N/A
**Notes:** -

---

#### TC-004: Rejecting a credit or debit in a non-primary denomination

**Expected Result:** HTTP 400, error = "Invalid denomination"
**Actual Result:** HTTP 200 returned instead of HTTP 400 — the system did not reject the transaction
**Status:** ❌ Fail
**Executed Date:** 2026-03-17
**JIRA Ref:** PROJ-789
**Defect Ref:** BUG-042
**Notes:** Occurs only with denomination = USD; tested EUR and it rejects normally. Screenshot attached: `tc004-fail-20260317.png`

---

## Execution Summary

| ID     | Description                                    | Status  | JIRA Ref           | Defect Ref |
| ------ | ---------------------------------------------- | ------- | ------------------ | ---------- |
| TC-001 | Configure primary denomination                 | ✅ Pass | PROJ-123           | N/A        |
| TC-002 | Open account with configured denomination      | ✅ Pass | PROJ-123, PROJ-456 | N/A        |
| TC-003 | Accept transaction in primary denomination     | ✅ Pass | PROJ-789           | N/A        |
| TC-004 | Reject transaction in non-primary denomination | ❌ Fail | PROJ-789           | BUG-042    |

_The JIRA Ref column is inherited from each TC's test case document entry (which inherits from the source AC). Use `—` (em dash) when the source TC has no JIRA Ref._

**Total:** 4 | ✅ Pass: 3 | ❌ Fail: 1 | ⚠️ Blocked: 0 | ⬜ Not Run: 0 | ⏸ Deferred: 0

---

## Defect Summary

| Defect Ref | TC-ID  | Severity | Description                                                | Status |
| ---------- | ------ | -------- | ---------------------------------------------------------- | ------ |
| BUG-042    | TC-004 | High     | System does not reject transaction when denomination = USD | Open   |

---
