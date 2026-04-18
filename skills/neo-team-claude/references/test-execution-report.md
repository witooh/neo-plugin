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
**Defect Ref:** N/A
**Notes:** -

---

#### TC-002: Account opening with configured primary denomination

**Expected Result:** HTTP 200, account status = OPEN, denomination = THB
**Actual Result:** HTTP 200, account status = OPEN, denomination = THB
**Status:** ✅ Pass
**Executed Date:** 2026-03-17
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
**Defect Ref:** N/A
**Notes:** -

---

#### TC-004: Rejecting a credit or debit in a non-primary denomination

**Expected Result:** HTTP 400, error = "Invalid denomination"
**Actual Result:** HTTP 200 returned instead of HTTP 400 — the system did not reject the transaction
**Status:** ❌ Fail
**Executed Date:** 2026-03-17
**Defect Ref:** BUG-042
**Notes:** Occurs only with denomination = USD; tested EUR and it rejects normally. Screenshot attached: `tc004-fail-20260317.png`

---

## Execution Summary

| ID     | Description                                    | Status  | Defect Ref |
| ------ | ---------------------------------------------- | ------- | ---------- |
| TC-001 | Configure primary denomination                 | ✅ Pass | N/A        |
| TC-002 | Open account with configured denomination      | ✅ Pass | N/A        |
| TC-003 | Accept transaction in primary denomination     | ✅ Pass | N/A        |
| TC-004 | Reject transaction in non-primary denomination | ❌ Fail | BUG-042    |

**Total:** 4 | ✅ Pass: 3 | ❌ Fail: 1 | ⚠️ Blocked: 0 | ⬜ Not Run: 0

---

## Defect Summary

| Defect Ref | TC-ID  | Severity | Description                                                | Status |
| ---------- | ------ | -------- | ---------------------------------------------------------- | ------ |
| BUG-042    | TC-004 | High     | System does not reject transaction when denomination = USD | Open   |

---
