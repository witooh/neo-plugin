# Shared: AC Status — Ready / Blocked State Machine

**Single source of truth for the AC `Status` field and its propagation.** Referenced by Business Analyst (assignment), QA (propagation + sign-off), the Orchestrator (Dev-Loop scope, SKILL.md § Verification — All-Blocked guard), and the re-entry workflow (`phase-map.md` § Re-entry). The gates that cite this file keep their own **enforcement**; this file owns the **definitions**.

## 1. Semantics

- `Status` encodes **dependency-readiness, not progress**. Every AC is exactly one of `Ready` | `Blocked` — no other value, never absent.
- **Ready** — every upstream dependency exists; the AC is implementable and testable now.
- **Blocked** — an upstream dependency (an external contract, another team's endpoint, an unfinalized spec) is missing; the AC is fully specified now but implemented/tested later.
- **Legacy compatibility** — if an AC document has NO `Status` field anywhere (predates this schema), treat every AC as `Ready` and note the assumption once in the document's Notes section. Never silently mix conventions; a *partial* Status state → return `NEEDS_CONTEXT` to have BA backfill.

## 2. Assignment (Business Analyst, at AC-generation time)

Apply this deterministic decision tree:

1. **Default = Ready.** Downgrade to Blocked only via a trigger below.
2. **Trigger A — user-declared blocker.** The prompt names a blocked AC ("AC-002 is blocked by GI-53") → set `Blocked`, copy the user's exact dependency reference into `Blocker`. No Open Question.
3. **Trigger B — external-contract dependency without evidence.** The AC body calls an external service/endpoint owned by another team. Check for either (a) an existing API-contract doc covering that endpoint, or (b) a prompt reference to a ticket/MR proving the dependency is finalized. If NEITHER exists → raise the Open Question below (do NOT default to Blocked on your own; honors Never-Guess — preamble §1).
4. **Forbidden uses of Blocked:** "unsure how to write it" → Open Question; "might change later" → VERSION.md; "defer to a later sprint" → Out of Scope section. Blocked is only for a real upstream dependency.
5. **Blocker format** (required when `Blocked`): `<dependency-id> — <specific missing piece>` — e.g. `GI-53 (PS contract) — response shape when campaign_eligible_list is empty is not yet confirmed`.
6. A Blocked AC still requires a complete, testable spec (GIVEN/WHEN/THEN, Business Rule, Priority). **Blocked defers implementation, not specification quality.**

**Open Question template (Trigger B)** — emit when no contract evidence exists:

> **AC-NNN — External contract dependency check**
>
> AC-NNN references [endpoint/service/contract name] owned by team/system [name]. Please approve one of:
>
> (a) This contract is finalized — provide a reference (ticket ID, doc path, or MR link) so the AC can be marked Ready
> (b) The contract isn't ready — provide the upstream ticket/work item that is blocking this AC, to mark Status=Blocked + the Blocker field
>
> **Reference:** AC-NNN (`<sub-operation name>`)
> **Why it matters:** if the AC stays Ready while the contract isn't settled, the Dev Loop will implement on an assumption and the test will fail; if it's marked Blocked while the contract is actually ready, we defer the work needlessly

## 3. Propagation to test cases (QA)

QA designs test cases for **ALL ACs regardless of Status** — coverage documentation is the goal.
- **Ready AC** → TC runs in the Dev Loop and counts toward Sign-Off.
- **Blocked AC** → TC is tagged `**Tags:** @blocked` with `**Blocker:**` copied verbatim from the AC; appears in the Test Case Summary with `Status = Blocked`; is **NOT** emitted into E2E spec files; is **NOT** counted in Sign-Off pass/fail; is listed in the execution report's **Deferred Test Cases** section.
- **MUST NOT** silently treat a Blocked AC as Ready (would generate E2E that cannot run), and **MUST NOT** drop Blocked ACs from the test case document (loses coverage trace).

## 4. Sign-Off math

- **QA Sign-Off = Approved** means "every test case for a **Ready** AC passes." Blocked test cases are Deferred and reported separately — a Blocked TC failing or being skipped does NOT block Sign-Off.
- **All-Blocked guard:** if 100% of the input ACs are Blocked, Sign-Off = **Blocked** and the Orchestrator escalates to the user — the Dev Loop cannot validate anything with 0 Ready ACs (SKILL.md § Verification — All-Blocked guard; the pre-Build Ready-count check fires before the Dev Loop).

## 5. Re-entry — Blocker resolved (promotion `Blocked` → `Ready`)

When an upstream dependency finalizes and the user re-invokes scoped to specific AC-IDs (`phase-map.md` § Re-entry owns the dispatch ORDER; this section owns the field mutations):

- **BA** mutates **ONLY** the named AC-IDs: `Status: Blocked → Ready`, remove the `Blocker:` line, update the AC Summary `Status` column + the `(Ready: R / Blocked: B)` tail count, add a `VERSION.md` entry, then run the shared Verification Process. Output the diff (which AC-IDs changed). `JIRA Ref` is **sticky** — see [`jira-ref.md`](jira-ref.md) §5.
- **QA** removes the `@blocked` tag + `Blocker:` field for the promoted TCs, updates the Summary `Status` column, removes them from the Deferred table, updates the count; then (Dev Loop mode) generates E2E specs for the now-Ready TCs only.
- **Dev Loop** is scoped to **ONLY** the promoted AC-IDs, never the whole document.
- **Edge cases** → return an Open Question *before* promoting: contract drift (resolved contract differs from the AC's assumptions), selective promotion (several Blocked ACs share an upstream — promote only the IDs the user named), missing evidence (no actual upstream reference supplied — reuse the Trigger B template in §2).
