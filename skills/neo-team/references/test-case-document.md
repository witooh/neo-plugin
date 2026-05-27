**Module:** Savings Account
**Version:** 1.0.0
**Created Date:** 2026-03-17

---

## Test Suite 1: Product Configuration

---

#### TC-001: Configuring the primary denomination of the product

**GIVEN** a bank offers a savings product
**WHEN** configuring the product
**THEN** the bank can specify the primary denomination in which the account will transact

**Endpoint:** `POST /v1/products`
**Request Body:**
```json
{
  "name": "Savings Account",
  "denomination": "THB"
}
```
**Expected Response:**
```json
HTTP 201
{
  "id": "PROD-001",
  "name": "Savings Account",
  "denomination": "THB",
  "status": "ACTIVE"
}
```

**Test Steps:**

1. Log in as Bank Admin
2. Create a new savings product via `POST /v1/products`
3. Set primary denomination = THB
4. Verify the response status and body

**Expected Result:** Product is saved with denomination = THB
**Test Data:** `denomination: "THB"`
**Precondition:** None
**Traces To:** AC-001

---

#### TC-002: Account opening with configured primary denomination

**GIVEN** a bank offers a savings product
**AND** the primary denomination of the product is configured as THB
**WHEN** an account is opened with denomination = THB
**THEN** the account should be opened successfully in Vault

**Endpoint:** `POST /v1/accounts`
**Request Body:**
```json
{
  "product_id": "PROD-001",
  "denomination": "THB",
  "customer_id": "CUST-001"
}
```
**Expected Response:**
```json
HTTP 200
{
  "account_id": "ACC-001",
  "status": "OPEN",
  "denomination": "THB"
}
```

**Test Steps:**

1. Call the account opening API via `POST /v1/accounts` with denomination = THB
2. Verify the response status = 200
3. Verify the account record: status = OPEN, denomination = THB

**Expected Result:** HTTP 200, account status = OPEN, denomination = THB
**Test Data:** `account_id: "ACC-001"`, `denomination: "THB"`
**Precondition:** TC-001 must pass
**Traces To:** AC-002

---

## Test Suite 2: Transaction Validation

---

#### TC-003: Accepting a credit or debit in a primary denomination

**GIVEN** there is an account where the primary denomination is THB
**WHEN** a credit or debit is attempted in THB
**THEN** the transaction is accepted

**Endpoint:** `POST /v1/accounts/{account_id}/transactions`
**Request Body:**
```json
{
  "type": "CREDIT",
  "amount": 1000,
  "denomination": "THB"
}
```
**Expected Response:**
```json
HTTP 200
{
  "transaction_id": "TXN-001",
  "status": "ACCEPTED",
  "amount": 1000,
  "denomination": "THB"
}
```

**Test Steps:**

1. Call `POST /v1/accounts/ACC-001/transactions` with denomination = THB, amount = 1000
2. Verify the response status = 200 and transaction status = ACCEPTED

**Expected Result:** HTTP 200, transaction status = ACCEPTED
**Test Data:** `amount: 1000`, `denomination: "THB"`
**Precondition:** TC-002 must pass
**Traces To:** AC-003

---

#### TC-004: Rejecting a credit or debit in a non-primary denomination

**GIVEN** there is an account where the primary denomination is THB
**WHEN** a credit or debit is attempted in USD
**THEN** the transaction is rejected

**Endpoint:** `POST /v1/accounts/{account_id}/transactions`
**Request Body:**
```json
{
  "type": "CREDIT",
  "amount": 100,
  "denomination": "USD"
}
```
**Expected Response:**
```json
HTTP 400
{
  "error": "Invalid denomination",
  "message": "Account ACC-001 only accepts THB"
}
```

**Test Steps:**

1. Call `POST /v1/accounts/ACC-001/transactions` with denomination = USD, amount = 100
2. Verify the response status = 400 and error = "Invalid denomination"

**Expected Result:** HTTP 400, error = "Invalid denomination"
**Test Data:** `amount: 100`, `denomination: "USD"`
**Precondition:** TC-002 must pass
**Traces To:** AC-004

---

#### TC-005: Reject transaction in a denomination not yet on-boarded (Blocked AC — documented but not executed)

**GIVEN** there is an account whose primary denomination is THB
**AND** denomination support for JPY is pending on-boarding by the FX team
**WHEN** a credit is attempted in JPY
**THEN** the transaction is rejected with a denomination-not-supported error

**Endpoint:** `POST /v1/accounts/{account_id}/transactions`
**Request Body:**
```json
{
  "type": "CREDIT",
  "amount": 5000,
  "denomination": "JPY"
}
```
**Expected Response:**
```json
HTTP 422
{
  "error": "DENOMINATION_NOT_SUPPORTED",
  "message": "JPY is not yet on-boarded for this account"
}
```

**Test Steps:**

1. Call `POST /v1/accounts/ACC-001/transactions` with denomination = JPY
2. Verify response status = 422 and error code = DENOMINATION_NOT_SUPPORTED

**Expected Result:** HTTP 422, error code = DENOMINATION_NOT_SUPPORTED
**Test Data:** `amount: 5000`, `denomination: "JPY"`
**Precondition:** TC-002 must pass
**Traces To:** AC-005
**AC Status:** Blocked
**Tags:** @blocked
**Blocker:** FX-104 (FX on-boarding contract) — error code/message for unsupported denominations is not yet finalized by the FX team

---

## Workflow Chain (Optional — Per Test Suite)

When a test suite requires calling APIs to create prerequisite data before the actual test cases can run, document the API call chain here. QA uses this table to generate `{usecase}.precondition.ts` code (see [`e2e-playwright.md`](e2e-playwright.md)).

Include this section when test cases have `Precondition: TC-XXX must pass` that involves calling APIs to create data. Skip if the only preconditions are static data or configuration.

### Test Suite 2: Transaction Validation — Prerequisite API Calls

| Step | Method | Endpoint       | Body / Ref                                                                                   | Capture      |
|------|--------|----------------|----------------------------------------------------------------------------------------------|--------------|
| 1    | POST   | /v1/products   | `{ "name": "Savings Account", "denomination": "THB" }`                                      | -> productId |
| 2    | POST   | /v1/accounts   | `{ "product_id": "{productId}", "denomination": "THB", "customer_id": "CUST-001" }`         | -> accountId |

**Conventions:**
- Steps run in order; each step can reference captured values from previous steps using `{variableName}`
- `Body / Ref` can be inline JSON or a path to a fixture file (e.g., `__fixtures__/customer.json`)
- `Capture` column uses `-> fieldName` to indicate which response field to store for later use
- Teardown runs in reverse step order (step 2 first, then step 1)

---

## Test Case Summary

| ID     | Suite                  | Description                                    | Precondition | Traces To | Status  |
| ------ | ---------------------- | ---------------------------------------------- | ------------ | --------- | ------- |
| TC-001 | Product Configuration  | Configure primary denomination                 | None         | AC-001    | Ready   |
| TC-002 | Product Configuration  | Open account with configured denomination      | TC-001       | AC-002    | Ready   |
| TC-003 | Transaction Validation | Accept transaction in primary denomination     | TC-002       | AC-003    | Ready   |
| TC-004 | Transaction Validation | Reject transaction in non-primary denomination | TC-002       | AC-004    | Ready   |
| TC-005 | Transaction Validation | Reject transaction in not-yet-onboarded denom  | TC-002       | AC-005    | Blocked |

**Total Test Cases:** 5  (Ready: 4 / Blocked (Deferred): 1)

---

## Deferred Test Cases (Blocked ACs)

| TC-ID  | Traces To | Blocker                                                                  | Upstream Reference            |
| ------ | --------- | ------------------------------------------------------------------------ | ----------------------------- |
| TC-005 | AC-005    | error code/message for unsupported denominations is not yet finalized    | FX-104 (FX on-boarding)       |

These test cases are not executed in the Dev Loop. Re-evaluate once the upstream reference is resolved — see [`impact-map.md`](impact-map.md) row 10 (AC Blocker resolved) for the re-entry workflow.

---

## Notes

- TC-003 and TC-004 require TC-002 to pass first
- Test data uses the staging environment only
- TC-005 is deferred; do NOT generate an E2E spec for it. The corresponding AC (AC-005) will be promoted to Ready once FX-104 is finalized — at that point QA is re-dispatched to generate the E2E spec and execute it
