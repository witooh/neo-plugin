---
name: attack-test
description: >-
  Fires abuse/hack paths over HTTP against a running stack (local/SIT) after the
  happy path works. Hunts money-moves, authz bypass, proof forge, and
  idempotency leaks; reports each finding with reproduce steps plus a fix that
  names the file/check to enforce. Use when the user says try hack, attack-test,
  probe the flow, security probe HTTP, or asks whether skipping step X still
  transfers or completes a protected action. Not for static latent hunts
  (`bug-hunter`), gate audits (`falsifying`), diff review (`code-review`), or
  AC-driven e2e (`e2e-playwright`).
---

# Attack Test

Hit a **running** system over HTTP as an attacker. Do not read ACs to make them
pass — ask whether **skipping a step / forging proof / swapping identity /
abusing idempotency** still moves money or mutates protected state.

Every finding **must** carry:

1. **reproduce** — request sequence another session can replay cold
2. **impact** — money-move / authz bypass / info disclosure / DoS state
3. **fix** — where to change + the invariant to enforce (not "add validation")

Confirmed findings hand off to the **BUG flow**. Do not patch production code
inside this skill unless the user explicitly asks to fix after the report.

## When to use

- "try hack", "attack-test", "can we bypass…", "transfer without bio/OTP?"
- After a money / authz / session / idempotency feature is up on local or SIT
- Before merging an MR that touches confirm, settle, challenge, authz, webhook

## When NOT to use

| Job | Go elsewhere |
|---|---|
| Latent defects in green code without firing HTTP | `bug-hunter` |
| Audit whether a gate/coverage number can go red | `falsifying` |
| Diff-only review | `code-review` |
| Write e2e that prove ACs | `e2e-playwright` |
| No running stack / no contract yet | stand the stack up + read knowledge/api first |

## Ground rules

1. **Live HTTP only** — never mark HACKED from a static code read. Need status + body.
2. **Happy path first** — if the root flow is broken, do not conclude the attack was blocked.
3. **No exploit kits / malware** — only the target system's APIs the user pointed at (local/SIT/this project).
4. **Stay in scope** — sentinel/test customers only; never thrash production data.
5. **Evidence = request/response** — every finding cites status + app error code or settle field.
6. **Fix must point somewhere** — file/function/missing check, or mark `[INFERENCE]` if source was not opened.
7. **Never invent wire fields** — pull names from compose / bruno / e2e / api-spec / knowledge.

## Inputs (collect before firing)

| Required | Example |
|---|---|
| Base URL | `http://localhost:8080` |
| Target flow | transfer biometric, payment confirm, … |
| Normal endpoint order | verify → accept → result → confirm |
| ≥ 2 test identities | owner / other customer (header or token) |
| Protected value | settle money, change destination, unlock session |
| Auth scheme for that env | `X-Customer-ID`, bearer, mTLS, … |

Missing inputs → stop and ask. Do not invent.

## Process

### 1) Baseline (happy path)

1. Confirm stack health.
2. Walk the normal flow until a real success side effect (e.g. confirm returns `core_reference_number`).
3. Record IDs: `transaction_id`, token, session, idempotency key.

If baseline fails → stop attacking; report **BASELINE_FAIL**.

### 2) Build the attack matrix (minimum)

Cut against the real flow. Cover at least these six groups:

| Group | Question |
|---|---|
| **Skip-step** | Skip challenge/OTP/approve — does the final action still succeed? |
| **Forge-proof** | Fake proof (random UUID, forged success status, empty signature) — accepted? |
| **Replay** | Reuse token/session/idem key after success or after fail |
| **Confused deputy / IDOR** | Identity B uses A's ids (tx, session, order) |
| **Tamper body** | Change amount/destination/customer on a late step |
| **State abuse** | Confirm after fail, double settle, parallel confirm |

Add domain-specific cases when present: webhook re-delivery, two-tab race, expired session, mass assignment.

### 3) Fire and record

Each case keeps:

```text
case:
actor: owner|other|anonymous
steps: ...
expect_blocked: true|false
http_status:
app_code:
side_effect: none|settled|leaked_fields|state_changed
evidence: (trim body — never dump long secrets)
```

### 4) Classify results

| Label | Condition |
|---|---|
| **HACKED** | Valuable outcome without meeting the protection conditions (money moved, excess privilege, wrong unlock) |
| **INFO_LEAK** | No replayed action, but read another party's or settle data |
| **BLOCKED** | Rejected and no bad side effect |
| **TRUST_BOUNDARY** | Passed because design trusts an upstream (e.g. BFF) — name it; do not fake a product bug |
| **BASELINE_FAIL** | Happy path never succeeded |

### 5) Report format (mandatory)

Emit the report in this shape (outer fence is documentation only — do not nest live fences when writing the real report):

````markdown
# Attack Test — <flow> @ <env>

## Baseline
- happy path: PASS|FAIL
- evidence: ...

## Findings

### F1 — <short title> [<HACKED|INFO_LEAK|...>]
**Impact:** ...
**Reproduce:**
1. ...
2. ...

    POST /...
    Header: ...
    Body: ...
    → <status> <code>

**Why it works:** <1–3 lines; cite code if opened>
**Fix:**
- enforce: <invariant, e.g. session.CustomerID == caller>
- where: <path>:<symbol> or layer (usecase confirm gate)
- tests: proposed unit case + negative e2e name
- residual: <if any, e.g. still trusts BFF>

## Blocked (summary table)

| case | result |
|---|---|
| ... | BLOCKED |

## Out of scope / not tested

- ...
````

### 6) Minimum fix guidance by type

| Kind | Direction |
|---|---|
| Skip-step | Server-side state machine; final action checks **state**, not only request fields |
| Forge-proof | Proof issued by server/upstream; client may send only a server-bound handle |
| IDOR | Every read/consume asserts `resource.Owner == caller` |
| Idempotency leak | Idem key lookup scoped by caller/owner before returning a cached body |
| Tamper amount | Lock amount/destination into session at verify; late steps reject overrides |
| Replay | Single-use consume (GETDEL); explicit state transitions |

Never propose bare "add validation" without naming the **invariant**.

## Depth levels

| Level | When | What |
|---|---|---|
| **smoke** | Need it fast | baseline + skip-step + forge-proof on the final action |
| **standard** (default) | Normal ask | + two-identity IDOR + replay + tamper body + idempotency |
| **deep** | Before money release | + paired-request race + expired/TTL + sibling resource + webhook |

## Output rules

- Match the user's language (default Thai if the user wrote Thai).
- Short tables; the report alone must be enough to replay requests.
- Never label HACKED from static reading without an HTTP fire.
- Untested cases go under **not tested** — never guess.
- Post to MR/Jira only when asked; finding body still needs reproduce + fix.
- Hand HACKED / INFO_LEAK to BUG flow (`diagnosing-bugs` → `tdd` repro) unless the user asked to fix now.

## Red flags (skill is broken)

- Only happy path ran, then "looks safe"
- Finding without reproduce
- Finding without fix / floating fix
- Conclusion from code without HTTP
- Real production customers without explicit permission

## Verification (before stop)

- [ ] Baseline passed and recorded (or BASELINE_FAIL stopped the run)
- [ ] Standard groups covered (or depth stated as smoke/deep)
- [ ] Every finding has reproduce + impact + fix
- [ ] HACKED / INFO_LEAK / TRUST_BOUNDARY split cleanly
- [ ] Blocked cases summarized in a table
- [ ] not tested listed explicitly

## Rationalizations

| Thought | Reality |
|---|---|
| "Code checks the state, so skip-step is fine" | Prove it with HTTP. Untested checks are claims. |
| "403 on one call means the flow is safe" | Try the final action directly; middle-step 403 is not the prize. |
| "I'll mark HACKED from the missing if" | Static read → candidate. Live settle/leak → finding. |
| "Fix: add validation" | Name the invariant and the gate that must enforce it. |
| "No second identity handy — skip IDOR" | Then list IDOR under not tested. Do not imply it passed. |
| "Production data is fine, I'm careful" | Sentinel only. Full stop. |
