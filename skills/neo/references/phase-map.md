# Phase Map — task → phases (authoritative routing)

The orchestrator uses this file to choose which phases the work touches. **Read it before every plan — don't guess.**

## How to use
1. parse the work → **action** (create / modify / fix / review / refactor / analyze) + **target artifact** (AC / system design / endpoint / code / test cases / API contract / security / MR)
2. find the matching row → get the **phase subset** (in propagation order)
3. dispatch in order (checkpoints per SKILL § Flow). No row matches → ask the user (don't invent)

Phases: **Spec**(BA) · **Design**(Architect) · **TestSpec**(QA) · **Build**(Developer) · **Verify**(QA-E2E ∥ Code Reviewer ∥ Security) · **Diagnose**(System Analyzer — bug/incident only).

## Phase Selection Table
| Trigger / artifact | Phases (propagation order) | Notes |
|---|---|---|
| create/modify **AC** | Spec → Design → TestSpec | Architect re-validates the design covers the new AC; QA updates test cases |
| create/modify **System Design** | Design → TestSpec → Build | QA reassesses testability; Developer updates if already started |
| create/modify **Test Cases** | TestSpec → (BA review AC coverage) | BA reviews that tests cover every AC-ID; don't dispatch Developer unless an AC gap is found |
| **add a new endpoint** (full) | Spec → Design → TestSpec → Build → Verify | full chain. Verify = E2E ∥ CR ∥ Security in parallel |
| modify **existing code** | Build → Verify → (Spec/Design if behavior changes) | see § Behavior-impact |
| modify **API contract** | Design → Build → Verify | Security mandatory in Verify (API surface changed) |
| **Bug fix** | Diagnose → Build → Verify | System Analyzer finds the root cause first |
| **Review MR — no card** | Verify (8a: CR ∥ Security ∥ QA-regression, read-only) | see § MR |
| **Review MR — with card** | Verify (8b: CR ∥ Security ∥ QA-compliance, read-only) | + AC/TC compliance table |
| **Create MR** | `Skill(gitlab)` MR Create | no specialist dispatch, no plan UI |
| **Refactor** | Verify(CR identifies scope) → Build → Verify(QA confirms no behavior change) | CR first to scope it |
| **AC Blocker resolved** | Spec(promote) → Design(conditional) → TestSpec → Build → Verify | see § Re-entry |

## Single-phase shortcuts (dispatch directly, no plan UI)
"create AC for <usecase>" → Spec · "gen test cases" → TestSpec · "review this diff" → Verify(CR alone) · "diagnose why /x returns 500" → Diagnose · "security audit /auth" → Verify(Security alone) · "create MR" → gitlab. *(checkpoint after the single role finishes: propagate the next phase / review / stop)*

## Behavior-impact Decision (modifying existing code)
Does the code change touch **observable behavior** (must propagate Spec/Design) or is it internal-only? Reason from input/output/side-effect/error — not from diff size:
| Pattern | Behavior? | Propagate Spec/Design? |
|---|---|---|
| rename var / format / docstring / internal helper (no signature change) · perf opt (same I/O contract) | No | No |
| add a branch that changes output · change validation/error/status code · add-remove a response field · change a side-effect (DB / external call / timing) | Yes | Yes (+ Security if PII) |

Can't decide → ask the user at the checkpoint after Build.

## Verification model (see SKILL § Verification — summary)
**Doc adversarial + loop-on-measurable:** Design verifies Spec (AR7), TestSpec verifies Design (Q7) **before** producing work; BA closes the loop on test cases via the "modify Test Cases" row (BA review). **Semantic** defect → 1 round back → escalate; **measurable** defect (count / grep / CS1 stale reference) → **loop until evidence-green, ~3 rounds → escalate**. **Independent fresh-eyes (L2):** an isolated / last-in-chain writer with no downstream looped-verifier in the subset → orchestrator asks at CP-final, then dispatches the natural downstream role in verify-only mode (collision rule: skip iff a downstream looped verifier is already in the subset). **CS1 completeness sweep:** scoped-change tasks (rename / retire / migrate) self-grep for stale references — docs via BA/Architect/QA, code via Developer + CR (looped by the Dev Loop). **Dev Loop:** Build→Verify auto-loops until E2E passes + CR/Security clean + CS1 green, ~3 rounds then escalate. Cut the budget/max-iter ceremony — keep the independent verify.

## MR Workflows
The single entry point for MR work. **Don't run glab yourself** — call `Skill(gitlab)` for every I/O (fetch / create / update / post comment / CI logs).
- **Intent:** "create MR" (no URL) → Create. "review MR" + URL → Review. A bare URL with no verb → ask the user (quick read vs review). card ID (`ABC-123`) → 8b; none → 8a; unclear → ask (don't guess the card — `shared/jira-ref.md` §6).
- **Create:** `Skill(gitlab)` _"MR Create from current branch"_ (handles branch/uncommitted/push/diff/description/`glab mr create`); with a card → include `JIRA: <ID>`; report the resulting URL.
- **Review (read-only, no auto-fix):**
  1. (8b) resolve the usecase from `docs/design/INDEX.md`, confirm `acceptance-criteria.html` has `JIRA Ref:` = card, keep the paths (`acceptance-criteria.html`, `test-cases.html`, `traceability.html`). card → none / several usecases / unclear → ask the user. Local docs only (don't fetch live JIRA) — this local-only stance is **MR-review-scoped**; the Spec/BA phase **does** fetch JIRA card *content* for AC source-verification (`shared/jira-ref.md` §7)
  2. fetch the MR (`Skill(gitlab)` _"MR Read: <url>"_) → JSON + diff + existing notes (summarize to avoid duplicate reviewers)
  3. plan-confirm (3 roles)
  4. dispatch **CR ∥ Security ∥ QA** in parallel (one message); QA gets the MR-mode flag (8a/8b) + (8b) the 3 paths + card. QA is read-only, writes no doc
  5. 1 checkpoint after all return
  6. compose the comment from `templates/mr-review-template.md` (table-first; 8b includes AC/TC compliance from QA)
  7. post (`Skill(gitlab)` _"Post Comment to <url>: <text>"_) **[CP before post]**; glab fails → hand the text to the user to post themselves
  - want to fix the findings → re-run as Modify-Code / Bug-Fix (Build→Verify)

## Re-entry (AC Blocker resolved)
User re-run such as "/neo AC-002 unblocked — promote + run Dev Loop scoped to AC-002" → phases:
1. **Spec** (BA mandatory) — mutate only the named AC-IDs: `Status: Blocked→Ready`, remove `Blocker:`, update Summary Status + `(Ready:R/Blocked:B)` count + `VERSION.md`; JIRA sticky (`shared/ac-status.md` §5, `shared/jira-ref.md` §5); output the diff
2. **Design** (conditional) — only if the design for the promoted AC doesn't exist yet
3. **TestSpec** (QA) — untag `@blocked` + update the count, then gen E2E only for the promoted TC (after Build)
4. **Build** — scoped to only the promoted AC-IDs (paste the AC body verbatim); never touch another AC's code path
5. **Verify** — CR reviews the new diff
edge: **contract drift** (the contract differs from the original AC body) / **selective promotion** (several AC share an upstream — the user must say which) / **missing evidence** (no real reference) → BA Open Question before promoting (don't promote silently).

## Fallback (no row matches)
1. `AskUserQuestion` offering 2-3 interpretations
2. user is exploring an idea → suggest `/brainstorm` first, then back to `/neo`
3. non-dev task (question / explain / research) → answer directly, don't delegate
