# E2E spec contract (Jest + Playwright `request`)

The authoring rules the `e2e-playwright` skill writes against, and the rule book the L1 script
(`e2echeck.py`) and the L2 fresh-eyes verifier both read. The harness is **Jest the runner +
Playwright's HTTP `request` API as the client** — NOT the `@playwright/test` runner, and never a
browser. Match the project's existing specs; this file is the contract, the repo is the reference.

## Layout (per-project values are discovered, not assumed)

```
tests/e2e/
  specs/<usecase>.e2e.ts        # one spec file per usecase/endpoint group
  helpers/{api-client,db-helper}.ts   # REUSE — never add a second HTTP client
  fixtures/{seed,cleanup}.sql
  jest.config.ts · jest.global-setup.ts · jest.setup.ts
  .env.test                     # API_BASE_URL, DB_* — read from here, never hardcode
```

`jest.global-setup.ts` waits for `GET /health` and seeds the DB; `jest.setup.ts` exposes
`globalThis.apiContext`. A spec consumes those — it does not re-create them.

## The test-title prefix (the traceability contract)

Every test that exercises an acceptance criterion is titled:

```
[<CARD> - AC-NNN] <short behavior> → <expected outcome>
```

- **Spaces around the dash**: `[GI-74 - AC-001]`, not `[GI-74-AC-001]`.
- `<CARD>` = the JIRA card (e.g. `GI-74`, `BFID-5`) **or** the task-folder slug when the work has no
  JIRA key (`[awareness-answer-resp - AC-001]`). A leading test-case id is allowed too
  (`[TC-028 - GI-52 - AC-001]`) — the AC id must be the **last** segment in the bracket; the card is
  read as the last JIRA-style key in the label.
- **Table-driven tests** may interpolate the AC id — `` it(`[GI-74 - ${tc.ac}] …`) `` — provided the
  loop reads `for (const tc of TABLE)` and `TABLE` is an array literal holding literal
  `ac: "AC-NNN"` entries. The tripwire follows that chain; any other shape is reported as
  unresolvable rather than credited.
- `<expected outcome>` names the HTTP result the AC asserts — e.g. `→ 400 INVALID_DATE_RANGE`,
  `→ 200 StandardResponse`. Keep the **stable error code** in the title; it doubles as documentation.
- **One AC → several `it()`** is fine (e.g. a gate tested on the keep-path and the exclude-path).
- **One `it()` → several ACs** (co-coverage): put the extra ids in a comment on the **same line**
  as the `it(` so the tripwire credits them, e.g.
  `it("[GI-74 - AC-001] full flow → 200 ...", async () => { // also AC-008`.

## Non-HTTP-observable ACs (decision: count only what HTTP can check)

An AC whose effect cannot be seen in an HTTP response — a masked log line, a PII redaction, an
internal-only side effect — is **declared, not omitted**:

```ts
it.skip("[GI-74 - AC-017] masked tracer log on every failed path (log sink not observable over HTTP)", () => {});
```

The reason goes **in the title** after the prefix. The L1 tripwire requires the reason to be
present; the **L2 verifier judges whether it is legitimate** (a genuinely unobservable effect) vs a
lazy excuse for an AC that actually *is* HTTP-testable. Such ACs are not counted against the gate,
but they must still be covered elsewhere (the unit suite) — that is the project's concern, recorded
in the run report, not silently dropped.

## Deferred ACs (the feature is not built this round)

An `it.skip` says "HTTP cannot see this". It is the wrong tool for "we decided not to build this
yet" — there is nothing to skip, because the behavior does not exist. Declare those in the AC
source instead, on one machine-readable line:

```markdown
Deferred-ACs: AC-011, AC-012, AC-013 — biometric evaluation + challenge protocol deferred (D10)
```

The tripwire reports them as **declared deferred** and does not count them as uncovered. The reason
is required — a deferral with no reason is how an AC gets silently dropped — and the L2 verifier
judges whether it matches a real decision in the spec. Deferring is a **spec** edit, so it travels
with the task-docs sync: un-deferring means deleting the id from this line in the same pass as
writing the test.

The word "deferred" in prose is **not** scanned, deliberately. A real spec line reads *"Was: defer
AC-007/008/013 … AC-007 + AC-008 un-deferred … AC-013 remains deferred"* — any line-level match
gets all three wrong.

## Referring to another card's AC — keep the card id on the same line

The tripwire harvests the AC ids it must cover from the spec text, and treats `AC-NNN` as
**another card's** only when a different card id appears just before it **on the same line**
(`GI-445 AC-008`, or `the GI-445 verify-session (AC-008)`). If markdown wrapping pushes the card
id onto the previous line —

```markdown
- [`docs/tasks/GI-445/spec.md`](../GI-445/spec.md) — sibling verify spec; its
  AC-008 verify-session is consumed here
```

— the reference is harvested as one of **this** card's criteria and reported as a phantom
UNCOVERED, sending someone hunting for a test that should not exist. Write `GI-445 AC-008` on
the same line. The look-behind is deliberately not widened past the line: doing so would let a
card's own ACs be swallowed by a neighbouring mention, and a dropped AC is a false PASS — the
failure direction that matters.

## No-AC mode

A task with no acceptance criteria has no coverage to gate. Title its tests `[<CARD>] <desc> →
<expected>` — card prefix, no AC segment — and the tripwire reports `No-AC mode — coverage gate
N/A`, still checking title grammar and card consistency. If the task really does have ACs, number
them `AC-001…` in the spec first; No-AC mode is for tasks that genuinely have none, not a way
around an unnumbered spec.

## Spec skeleton

```ts
import { ApiClient, SuccessEnvelope, ErrorEnvelope } from "../helpers/api-client";
import { DbHelper } from "../helpers/db-helper";

const PATH = "/products/eligibles";

describe("GET /products/eligibles — Eligible Products [GI-74]", () => {
  let api: ApiClient;
  beforeAll(() => { api = new ApiClient(globalThis.apiContext); });

  describe("Happy path", () => {
    it("[GI-74 - AC-001] full 3-gate flow → 200 StandardResponse", async () => {
      const res = await api.get<SuccessEnvelope<EligibleData>>(`${PATH}?customer_id=${C001}`);
      expect(res.status).toBe(200);
      expect(res.body.status).toBe("Success");
      // assert the contract shape the api-spec defines …
    });
  });

  describe("Validation & errors", () => {
    it("[GI-74 - AC-010] missing customer_id → 400 CUSTOMER_NOT_FOUND", async () => {
      const res = await api.get<ErrorEnvelope>(PATH);
      expect(res.status).toBe(400);
      expect(res.body.errors.map((e) => e.code)).toContain("CUSTOMER_NOT_FOUND");
    });
  });
});
```

## Authoring rules

1. **Assert the contract, not a guess.** Status code **and** the StandardResponse envelope **and**
   the api-spec's stable error `code` (`res.body.errors[].code`), per the AC's expected outcome. A
   test that only checks `res.status` is half a test.
2. **Reuse helpers.** `new ApiClient(globalThis.apiContext)`; `DbHelper` for seed/assert. Do not
   `import { test } from "@playwright/test"` and do not new up a second HTTP client.
3. **Group by AC area** with `describe` blocks; keep each `it()` to one AC case.
4. **Reach error paths honestly.** Use the project's fault **sentinels** (special ids the fake
   adapters recognise, e.g. `NODEFAIL` → downstream failure, `MISMATCH` → readback differs) to make
   an error AC HTTP-observable. Never assert a 500 you cannot actually trigger.
5. **Own your data.** A spec that creates rows tracks them and deletes them in `afterAll`
   (versions before parents when there is no cascade). Tests must not depend on another spec's
   leftovers.
6. **Config from `.env.test`** via the helpers; never hardcode a base URL or DB credentials.
7. **No vacuous tests.** `it.skip(..., () => {})` is only for declared non-observable ACs (with a
   reason); never to silence a failing test.
