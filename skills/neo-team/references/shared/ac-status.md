# Shared: AC Status — Ready / Blocked State Machine

**Single source of truth for the AC `Status` field and its propagation.** Referenced by Business Analyst (assignment), QA (propagation + sign-off), the Orchestrator (Dev-Loop scope, SKILL.md GATE 5), and the re-entry workflow (`impact-map.md` row 10). The gates that cite this file keep their own **enforcement**; this file owns the **definitions**.

## 1. Semantics

- `Status` encodes **dependency-readiness, not progress**. Every AC is exactly one of `Ready` | `Blocked` — no other value, never absent.
- **Ready** — every upstream dependency exists; the AC is implementable and testable now.
- **Blocked** — an upstream dependency (an external contract, another team's endpoint, an unfinalized spec) is missing; the AC is fully specified now but implemented/tested later.
- **Legacy compatibility** — if an AC document has NO `Status` field anywhere (predates this schema), treat every AC as `Ready` and note the assumption once in the document's Notes section. Never silently mix conventions; a *partial* Status state → return `NEEDS_CONTEXT` to have BA backfill.

## 2. Assignment (Business Analyst, at AC-generation time)

Apply this deterministic decision tree:

1. **Default = Ready.** Downgrade to Blocked only via a trigger below.
2. **Trigger A — user-declared blocker.** The prompt names a blocked AC ("AC-002 ถูก block โดย GI-53") → set `Blocked`, copy the user's exact dependency reference into `Blocker`. No Open Question.
3. **Trigger B — external-contract dependency without evidence.** The AC body calls an external service/endpoint owned by another team. Check for either (a) an existing API-contract doc covering that endpoint, or (b) a prompt reference to a ticket/MR proving the dependency is finalized. If NEITHER exists → raise the Open Question below (do NOT default to Blocked on your own; honors the Universal Rule — Never Guess).
4. **Forbidden uses of Blocked:** "unsure how to write it" → Open Question; "might change later" → VERSION.md; "defer to a later sprint" → Out of Scope section. Blocked is only for a real upstream dependency.
5. **Blocker format** (required when `Blocked`): `<dependency-id> — <specific missing piece>` — e.g. `GI-53 (PS contract) — response shape when campaign_eligible_list is empty is not yet confirmed`.
6. A Blocked AC still requires a complete, testable spec (GIVEN/WHEN/THEN, Business Rule, Priority). **Blocked defers implementation, not specification quality.**

**Open Question template (Trigger B)** — emit in Thai when no contract evidence exists:

> **AC-NNN — External contract dependency check**
>
> AC-NNN อ้างถึง [ชื่อ endpoint/service/contract] ของทีม/ระบบ [ชื่อ]. ขออนุมัติทางใดทางหนึ่ง:
>
> (a) Contract นี้ finalized แล้ว — โปรดระบุ reference (ticket ID, doc path, หรือ MR link) เพื่อให้ AC ถูก mark เป็น Ready
> (b) Contract ยังไม่พร้อม — โปรดระบุ upstream ticket/work item ที่ block AC นี้อยู่ เพื่อ mark Status=Blocked + Blocker field
>
> **Reference:** AC-NNN (`<sub-operation name>`)
> **Why it matters:** ถ้า AC อยู่ใน Ready โดยที่ contract ยังไม่นิ่ง Dev Loop จะ implement บน assumption และ test จะ fail; ถ้า mark Blocked โดยที่ contract พร้อมแล้ว เราจะ defer งานโดยไม่จำเป็น

## 3. Propagation to test cases (QA)

QA designs test cases for **ALL ACs regardless of Status** — coverage documentation is the goal.
- **Ready AC** → TC runs in the Dev Loop and counts toward Sign-Off.
- **Blocked AC** → TC is tagged `**Tags:** @blocked` with `**Blocker:**` copied verbatim from the AC; appears in the Test Case Summary with `Status = Blocked`; is **NOT** emitted into E2E spec files; is **NOT** counted in Sign-Off pass/fail; is listed in the execution report's **Deferred Test Cases** section.
- **MUST NOT** silently treat a Blocked AC as Ready (would generate E2E that cannot run), and **MUST NOT** drop Blocked ACs from the test case document (loses coverage trace).

## 4. Sign-Off math

- **QA Sign-Off = Approved** means "every test case for a **Ready** AC passes." Blocked test cases are Deferred and reported separately — a Blocked TC failing or being skipped does NOT block Sign-Off.
- **All-Blocked guard:** if 100% of the input ACs are Blocked, Sign-Off = **Blocked** and the Orchestrator escalates to the user — the Dev Loop cannot validate anything with 0 Ready ACs (SKILL.md GATE 5 § Scope clarification; pre-loop guard fires at Orchestrator Flow step 5.5).

## 5. Re-entry — Blocker resolved (promotion `Blocked` → `Ready`)

When an upstream dependency finalizes and the user re-invokes scoped to specific AC-IDs (`impact-map.md` row 10 owns the dispatch ORDER; this section owns the field mutations):

- **BA** mutates **ONLY** the named AC-IDs: `Status: Blocked → Ready`, remove the `Blocker:` line, update the AC Summary `Status` column + the `(Ready: R / Blocked: B)` tail count, add a `VERSION.md` entry, then run the shared Verification Process. Output the diff (which AC-IDs changed). `JIRA Ref` is **sticky** — see [`jira-ref.md`](jira-ref.md) §5.
- **QA** removes the `@blocked` tag + `Blocker:` field for the promoted TCs, updates the Summary `Status` column, removes them from the Deferred table, updates the count; then (Dev Loop mode) generates E2E specs for the now-Ready TCs only.
- **Dev Loop** is scoped to **ONLY** the promoted AC-IDs, never the whole document.
- **Edge cases** → return an Open Question *before* promoting: contract drift (resolved contract differs from the AC's assumptions), selective promotion (several Blocked ACs share an upstream — promote only the IDs the user named), missing evidence (no actual upstream reference supplied — reuse the Trigger B template in §2).
