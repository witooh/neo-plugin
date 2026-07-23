---
name: e2e-playwright
description: "Author, update, and run HTTP end-to-end tests — one per acceptance criterion — for a service with a Jest + Playwright-request e2e harness (Playwright's HTTP client run by Jest, not the @playwright/test runner). Each test title carries the stable prefix '[<CARD> - AC-NNN] <desc> → <expected>' so every AC is traceable. Reads ACs from the neo spec (docs/tasks/<card>/spec.md) or a legacy docs/design/ layout, authors specs from those + the api-spec contract, runs the suite, maps pass/fail to each AC; a task with no AC section runs without the AC gate. Three-layer verify: e2echeck.py coverage tripwire + fresh-eyes + completeness. Only HTTP-observable ACs are gated; a non-observable one (log/PII) is a declared it.skip with a reason. Use when you write, generate, or run AC-driven HTTP e2e ('write e2e', 'run e2e', 'เขียน e2e', 'รัน e2e', 'e2e ตาม AC'), or when neo's Verify phase delegates e2e. NOT here: unit/logic → tdd; browser-UI testing is out of scope; api-spec → api-spec."
compatibility:
  environment: claude-code
  tools:
    - Read
    - Glob
    - Grep
    - Edit
    - Write
    - Bash
    - Agent
    - AskUserQuestion
---

# E2E Playwright (AC-driven HTTP e2e)

Author + **run** HTTP end-to-end tests, **one per acceptance criterion**, against a running service.
Each test is titled `[<CARD> - AC-NNN] <desc> → <expected>` so every AC is traceable from the
card to a green test. The suite is the project's **real** acceptance gate — a passing Go/unit test
can never stand in for it. Every run rests on **evidence (a deterministic coverage script) + an
independent fresh-eyes pass + a completeness sweep**, never on the running agent's confidence.

**Stack reality (read this first):** the harness is **Jest the test runner** driving
**Playwright's HTTP `request` API** as the client (`globalThis.apiContext = await
request.newContext()` from `@playwright/test`; specs use Jest `describe/it/expect` + a thin
`ApiClient` helper). Generate **Jest `it()`**, never `@playwright/test` `test()`. This skill does
not open a browser — it asserts on HTTP responses.

`ASSET_DIR` = `<skill base dir>/assets`, `SKILL_DIR` = `<skill base dir>` (the skill-load message
gives the "Base directory for this skill"). `e2echeck.py` is **stdlib-only** — no dependency to
install.

## Discover the project's e2e layout (the per-project contract values)

The structure (Jest + Playwright-`request` + pg) is fixed; the *values* are per-project. Before
anything, read them from the target repo — never assume paths:

- **e2e root** — the dir holding the harness (default `tests/e2e/`; confirm via a `jest.config.ts`
  whose `testMatch` ends in `*.e2e.ts`). In a monorepo, scope to the chosen service.
- **runner + scripts** — `tests/e2e/package.json` `scripts.test` (the run command, e.g.
  `jest --runInBand --forceExit`); `jest.config.ts`; `jest.global-setup.ts` (health-wait + DB
  seed) and `jest.setup.ts` (the `apiContext`).
- **helpers** — `tests/e2e/helpers/` (`api-client.ts` → `ApiClient`, `db-helper.ts` → `DbHelper`).
  Reuse these; never introduce a second HTTP client.
- **fixtures** — `tests/e2e/fixtures/{seed,cleanup}.sql`.
- **config** — `tests/e2e/.env.test` (`API_BASE_URL`, `DB_*`).
- **infra targets** — grep the repo `Makefile` for the compose / migration targets (e.g.
  `compose-up`, `migration-up`); these bring the service + DB up.

**No e2e harness present** → report what is missing and **STOP**. Scaffolding a brand-new harness
is out of scope (tell the user; do not invent one).

## Mode

Auto-detect (user can override): no spec for this card's usecase yet → **Generate**; a spec exists
and the request says run/validate ("run e2e", "รัน e2e") → **Run**; otherwise → **Update**.

## Step 1 · Locate the source-of-intent

What the specs must reflect — read it yourself, never from a summary:

- **Acceptance criteria (dual-source, in this order):**
  1. **neo spec** — the numbered **Acceptance Criteria section** of `docs/tasks/<card>/spec.md`
     (`<card>` = the task folder). Its `AC-NNN` ids are the test targets.
  2. **legacy Kiro layout** — the card's Ready ACs in `docs/design/<usecase>/`
     (`acceptance-criteria.*` + `test-cases.*`; often HTML — read them as text).
  3. **no AC section anywhere → no-AC mode** — the task has no acceptance criteria. Do **not** stop:
     author + run e2e from the api-spec contract + the endpoints under test, without the AC gate (see
     the no-AC notes in Steps 2-4). e2e does **not** invent or number ACs — numbered ACs are the
     spec's responsibility.
- **Wire contract** — the api-spec at `docs/api/<domain>/<endpoint>.yaml` (authored by the
  `api-spec` skill): the method/path, request/response field shape, status codes, and the stable
  **error codes** the AC expects. Assert against this, not a guess.
- **Card** — `<card>` is the task-folder / JIRA id; it appears as `<CARD>` in the title prefix. Pull
  it from the task folder name / the spec / `docs/knowledge/`.

Never invent endpoints or acceptance criteria.

## Step 2 · Author / update the e2e specs

Write per [`references/e2e-template.md`](references/e2e-template.md). In short:

- **One `it()` per testable AC case**, titled `[<CARD> - AC-NNN] <desc> → <expected>` (spaces
  around the dash). One AC may have **several** `it()`s; a single test may **co-cover** ACs by
  listing the extra ids on the same line (`// also AC-008`).
- **Reuse the project helpers** — `new ApiClient(globalThis.apiContext)`, `DbHelper` for
  seed/assert; follow the existing spec's per-spec **created-data teardown** in `afterAll`. Reach
  error paths through the project's fault **sentinels** when they exist (e.g. a `NODEFAIL` id) — do
  not fake a 500.
- **Assert the contract** — status code + the StandardResponse envelope + the api-spec's stable
  **error `code`** (not just the HTTP status), per the AC's expected outcome.
- **Non-HTTP-observable ACs** — an AC whose effect cannot be seen in an HTTP response (log/PII
  masking, an internal side effect) is recorded as an `it.skip("[<CARD> - AC-NNN] … (why it is not
  HTTP-observable)")` **with the reason in the title** — a visible, declared classification, never a
  silent omission. (Whether the reason is *legitimate* is the L2 verifier's call.)
- **Update** — touch the minimum; preserve hand-authored assertions; re-run L1 after.
- **No-AC mode** — with no ACs, title tests `[<CARD>] <desc> → <expected>` (card prefix, no AC
  segment) and group by endpoint; the Step-4 coverage gate is then N/A.

## Step 3 · Run + map to AC

1. **Ensure the service is up.** Check `GET $API_BASE_URL/health`. If it is not healthy, bring the
   stack up with the **discovered** make targets (e.g. `make compose-up && make migration-up`),
   then wait for `/health` (the harness's `global-setup` also polls it and seeds the DB).
2. **Run the suite** with the discovered script, capturing output as the **evidence artifact**:

   ```
   ( cd <e2e-root> && npm test ) 2>&1 | tee docs/tasks/<card>/e2e-run.txt
   ```

3. **Map results → AC.** Cross the run's pass/fail (from the Jest output) with the coverage from L1
   to emit an **AC → status** table: `pass` · `fail` · `uncovered` · `non-observable (skip)`. This
   table is the evidence for neo's **Verify-phase HTTP acceptance gate** — a real green run, not a
   claim, is what closes it. **No-AC mode:** emit a plain pass/fail table (no AC column).

## Step 4 · Three-layer verify

### verify-L1 · Script tripwire (when ACs exist)

```
python3 <ASSET_DIR>/e2echeck.py <e2e-root>/specs <ac-source> --card <CARD>
```

`<ac-source>` is the resolved Step-1 source — `docs/tasks/<card>/spec.md` (neo) or the legacy
`docs/design/<usecase>/` dir. It confirms every AC in the source is traced by an `it()` (active) or
an `it.skip()` with a reason (declared non-observable), validates the `[<CARD> - AC-NNN]` title
grammar, and prints a coverage table. **Tripwire, not ground truth.**

- **exit 0** → `PASS` → go to L1.5.
- **exit 1** → for each `ERROR`, add the missing test (or a justified `it.skip`), then re-run.
  **Loop until exit 0, OR ~3 rounds with no progress → STOP and escalate.** Never fake coverage.
- **No-AC mode:** skip L1 — there are no ACs to cover (coverage N/A). Go straight to L1.5.

### verify-L1.5 · Offer fresh-eyes (default yes)

Ask once via `AskUserQuestion`: *"Run an independent fresh-eyes verify of the e2e specs? (default:
yes)"* — **no** → skip L2 (mark "skipped by user"); **yes** → L2.

### verify-L2 · Fresh-eyes semantic verifier (independent agent)

Dispatch a verifier that did **not** author the specs — it re-reads the AC source + the specs
independently and judges what the script cannot: does each test actually **assert the AC's expected
status + error code** (not a vacuous test), and is each `it.skip` reason a *real* HTTP-unobservable
case (not a lazy excuse for a testable AC)?

```
Agent(subagent_type: "general-purpose", description: "verify e2e specs", prompt: """
# Role: E2E Semantic Verifier
Read first: <SKILL_DIR>/references/e2e-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the e2e specs just authored against their acceptance criteria. Check ONLY
semantic fidelity (not e2echeck.py's coverage/grammar checks). Read the AC source AND the specs
yourself.

## Under review
<e2e-root>/specs/*.e2e.ts

## Source-of-intent
<paste: docs/design/<usecase>/ (acceptance-criteria + test-cases) + the api-spec endpoint YAML>

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
""")
```

`SKILL_DIR` is mandatory — without it the verifier cannot read its role file. The verifier is
read-only → **you** reconcile the specs → re-run `e2echeck.py`. Offer a second round (default yes),
then escalate.

### verify-L3 · Completeness sweep (omission critic)

L1/L2 inspect what is present; L3 catches what is **missing entirely**. Re-enumerate the **full
Ready-AC inventory** from the source-of-intent and confirm: every Ready AC has either a passing
`it()` or a justified `it.skip`; every endpoint the ACs touch has at least one test; no whole AC was
silently dropped. Report any gap; fix → re-run L1. **No-AC mode:** with no AC inventory, sweep the
**endpoint inventory** instead — every endpoint the api-spec under test defines has at least one `it()`.

### Output

```
## E2E Playwright — <Generate / Update / Run>
**Suite:** <e2e-root> (N specs)   **Card:** <CARD>   **Source-of-intent:** <what it was authored from>
**Changes:** Created … / Updated … / —
**Run:** <npm test result: N passed / M failed / K skipped>   **Evidence:** docs/tasks/<card>/e2e-run.txt
**AC → status:** <pass count> pass · <fail> fail · <uncovered> uncovered · <skip> non-observable   (N/A in no-AC mode — report plain pass/fail)
**Verification (three-layer):**
- L1 e2echeck.py: ✅ PASS (0 error) / ❌ ESCALATED (N error after ~3 rounds) · loop rounds: 0-3
- L2 fresh-eyes: ✅ Faithful / ⚠️ N gaps fixed / ⏭ Skipped / ⏸ Not run
- L3 completeness sweep: ✅ every Ready AC covered / ⚠️ N silent omissions fixed
- Verdict: ✅ all HTTP-observable ACs green / ⚠️ gaps to reconcile / ⏸ escalated
**Warnings:** failing ACs, ACs declared non-observable (with reasons), service/infra that had to be brought up
```

---

## What this skill is NOT

- **Not** a unit / business-logic test writer — that is **`tdd`** (the Go/unit
  suite). This skill is the HTTP acceptance gate; the two are complementary, not substitutes.
- **Not** a browser / DOM / UI tester — browser testing is out of scope here; Playwright is
  only an HTTP client in this harness.
- **Not** an api-spec author — the wire contract is authored by **`api-spec`** (`docs/api/*.yaml`);
  this skill *reads* it to know the status codes + error codes to assert.
- **Not** a harness scaffolder — if no `tests/e2e` Jest+Playwright harness exists, it reports and
  stops rather than inventing one.
