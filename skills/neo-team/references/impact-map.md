# Impact Map

The **Impact Map** is the authoritative source the Orchestrator uses to decide which roles to dispatch for a given task. It encodes the relationships between **artifacts** (what changes) and **roles** (who must respond) in propagation order.

This replaces the v1 workflow catalog. Tasks are no longer matched to a fixed pipeline — they are matched to an impact row, and only the roles touched by that impact are dispatched.

## How the Orchestrator Uses This

1. Parse the user's task → identify the **action** (create / modify / fix / review / refactor / analyze) and **target artifact(s)** (AC, system design, endpoint, code, test cases, API contract, security, PR/MR).
2. Find the matching row in the table below.
3. The right-hand column lists impacted roles **in propagation order** — dispatch them sequentially, with a checkpoint after each (except inside the Dev loop).
4. If no row matches confidently, **ask the user** to clarify intent. Never guess the row.

## Impact Table

| # | Trigger / Artifact touched          | Impacted roles (propagation order)                                                  | Notes                                                                                              |
| - | ----------------------------------- | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 1 | Create or modify **AC**             | BA → Architect → QA                                                                  | Architect re-validates design covers updated ACs; QA updates test cases for AC coverage.            |
| 2 | Create or modify **System Design**  | Architect → QA → Developer                                                            | QA reassesses testability of new design; Developer updates implementation if already started.       |
| 3 | Create or modify **Test Cases**     | QA → BA (for AC coverage review)                                                      | BA reviews to ensure tests cover every AC-ID; no Developer dispatch unless tests reveal AC gaps.    |
| 4 | Add **new endpoint** (full spec)    | BA → Architect → QA → Developer → Code Reviewer → Security                            | Full chain. Dev loop kicks in for Developer → QA → Code Reviewer.                                   |
| 5 | Modify **existing Code**            | Developer → QA → Code Reviewer → (BA / Architect if behavior is impacted)             | Dev loop. BA/Architect propagation is **conditional** — see "Behavior-impact decision" below.       |
| 6 | Modify **API contract**             | Architect → Developer → QA → Security                                                 | Security is mandatory whenever API surface changes.                                                 |
| 7 | **Bug fix**                         | System Analyzer → Developer → QA → Code Reviewer                                      | System Analyzer first to find root cause; then Dev loop.                                            |
| 8 | **Review PR / MR**                  | Code Reviewer → Security                                                              | Read-only. No Developer dispatch unless the user explicitly asks to fix findings.                   |
| 9 | **Refactor**                        | Code Reviewer → Developer → QA                                                        | Code Reviewer first to identify scope; Developer to apply; QA to confirm no behavior change.        |
| 10 | **AC Blocker resolved** (Blocked → Ready promotion) | BA → Architect (conditional) → QA → Developer → Code Reviewer | BA mutates ONLY the named AC-IDs (Status: Blocked → Ready, removes Blocker line, updates Summary + Total + VERSION.md entry). Architect runs only if the previously-Blocked AC's design did not exist yet. QA untags `@blocked` and generates E2E specs for the now-Ready TCs. Dev Loop is scoped to ONLY the promoted AC-IDs — not the whole document. See § Re-entry Workflow below. |

## Propagation Rules

- **Sequential by default.** Each role waits for the previous role's output, with a checkpoint in between (Review / Continue / Stop) — enforced by Orchestrator HARD-GATE 6.
- **Dev loop** is the only auto-continuous segment: **Developer → QA → Code Reviewer** runs without inner checkpoints. Exit condition (enforced by Orchestrator HARD-GATE 5) — BOTH must hold:
  - QA Sign-Off = Approved (E2E pass + ACs validated)
  - Code Reviewer Verdict = Approved (zero Blocker AND zero Critical)

  On failure: Orchestrator re-dispatches Developer with concrete findings folded in, then re-runs QA + Code Reviewer. **Max 3 iterations** — after the 3rd round fails, the Orchestrator STOPS the loop and escalates to user. One combined checkpoint after exit. Warning/Info findings do NOT block exit.
- **Conditional roles** (the parenthesized entries in row 5) are dispatched only when the trigger condition is met. If the Orchestrator is unsure whether the condition is met, it surfaces the decision to the user at the relevant checkpoint instead of auto-including or auto-skipping the role.
- **User override.** If the user names a specific role in their request ("ให้ QA gen test cases เลย"), route directly to that role even if the Impact Map says additional roles are touched — but surface the discrepancy in the plan or in chat so the user can opt in to the extra roles if they want.

## Behavior-impact Decision (row 5)

When the user modifies existing code, the Orchestrator must decide whether the change touches **observable behavior** (which would require updating AC/system design) or is internal-only (which would not).

| Code change pattern                                   | Behavior impact? | Propagate to BA/Architect? |
| ----------------------------------------------------- | ---------------- | -------------------------- |
| Rename internal variable, format change, doc string   | No               | No                         |
| Refactor internal helper, no signature change         | No               | No                         |
| Add new branch / condition that changes output        | Yes              | Yes                        |
| Change validation rule, error message, status code    | Yes              | Yes                        |
| Add/remove fields from response, change shape         | Yes              | Yes (and Security if PII)  |
| Change side effect (DB write, external call, timing)  | Yes              | Yes                        |
| Performance optimization with identical I/O contract  | No               | No                         |

If the Orchestrator cannot decide confidently from the diff or task description, it MUST ask the user at the checkpoint after Developer (before deciding whether to include BA/Architect downstream).

## Re-entry Workflow (Blocker resolved)

When a previously-Blocked AC becomes implementable (the upstream dependency in the Blocker field is now finalized), the user re-invokes `/neo-team` with a message like:

```
/neo-team AC-002 unblocked — promote to Ready and run Dev Loop scoped to AC-002
```

This triggers **row 10** of the Impact Map. The Orchestrator dispatches roles in this order:

1. **BA** (mandatory first) — reads the AC document, mutates ONLY the named AC-IDs:
   - `Status: Blocked` → `Status: Ready`
   - Remove the `Blocker:` line from each promoted AC
   - Update AC Summary table `Status` column for the promoted rows
   - Update `Ready: R / Blocked: B` tail count
   - Add a `VERSION.md` entry: `vN.M: <usecase> — promoted AC-NNN from Blocked to Ready (upstream <ticket-id> finalized YYYY-MM-DD)`
   - Run § Document Verification & Fix (GATE BA3) on the modified doc
   - Output the diff (which AC-IDs changed) so downstream specialists know the scope

   **JIRA Ref persistence during promotion:** the `JIRA Ref:` field is **sticky** — it persists across Blocker resolution UNCHANGED. Do NOT add, modify, or remove `JIRA Ref` values during promotion unless the user's promotion message explicitly supplies new JIRA IDs (e.g., "promote AC-002 with JIRA Ref PROJ-700"). If the user supplies new JIRA IDs in the promotion message, follow the standard JIRA Ref Capture Rule (see `references/business-analyst.md` § JIRA Ref Capture Rule — merge new IDs with existing, deduplicate). The Blocker field (upstream dependency) and the JIRA Ref field (AC tracking ticket) are independent — resolving one does not affect the other.

2. **Architect** (conditional) — re-dispatched only if the promoted AC's behavior is NOT already covered in `docs/design/<usecase>/api-contracts.md` (this happens if the Blocked AC was a placeholder and design was deferred). If contract is already there, skip.

3. **QA** — re-dispatched in **two modes back-to-back**:
   - First in **Test Spec mode**: removes the `@blocked` tag, removes the `Blocker:` field, updates Test Case Summary `Status` column for the promoted TC-IDs, removes the rows from the Deferred Test Cases table, updates the `Ready: R / Blocked: B` count.
   - Then later in **Dev Loop mode** (after Developer): generates E2E specs ONLY for the promoted TCs, runs them.

4. **Developer** — dispatched with a prompt scoped to ONLY the newly-Ready AC-IDs (paste the AC bodies verbatim). Developer MUST NOT modify code paths covered by other ACs unless the implementation crosscuts. Run in TDD mode if a QA test spec exists for the promoted TC.

5. **Code Reviewer** — reviews only the new diff from step 4.

6. **Pre-Finalization Checklist** — Blocked ACs section now reflects the reduced count (or is empty if all were unblocked).

### Edge cases

- **Contract drift** — if the resolved Blocker is finalized but the actual contract differs from BA's original AC body assumptions, BA returns Open Questions BEFORE promoting. Do NOT silently promote when scenario semantics changed.
- **Selective promotion** — if multiple Blocked ACs share the same upstream and only one is being resolved, the user MUST specify which AC-IDs to promote. Do NOT batch-promote all that share the upstream without user direction.
- **Missing evidence** — if the user requests promotion but the upstream evidence is not actually available (e.g., they say "promote AC-002" but no contract reference exists), BA returns an Open Question asking for the reference (same Trigger B template as initial Blocked detection — `references/business-analyst.md` § Status Assignment Rule § 6).

## Single-Role Shortcuts

These tasks resolve to a **single role** — the Orchestrator dispatches immediately without the plan UI:

| Task example                                              | Single role          |
| --------------------------------------------------------- | -------------------- |
| "สร้าง AC ของ <usecase>" (no design yet)                  | BA                   |
| "อัปเดต AC ตาม requirement ใหม่"                          | BA (then checkpoint asks whether to propagate to Architect/QA) |
| "Generate test cases for AC-001..AC-005"                  | QA                   |
| "Review this diff" / "Review PR #N" (review only)         | Code Reviewer        |
| "Diagnose why /accounts returns 500"                      | System Analyzer      |
| "Security audit on /auth endpoints"                       | Security             |

Even for single-role calls, a checkpoint is shown after the role completes — the user can choose to propagate to the next downstream role suggested by the Impact Map, review the output, or stop.

## Fallback — No Matching Row

If the user's task does not clearly match any row:

1. Surface 2–3 likely interpretations to the user with AskUserQuestion (e.g., "นี่คือการแก้ AC หรือเปลี่ยน system design?")
2. If the user is still exploring, suggest `/brainstorm` first to refine the task — then return to `/neo-team` with the refined input.
3. Never invent a row or default to a workflow chain — the Impact Map is the contract.

## Extending the Map

When a recurring task pattern emerges that does not fit any row, add a new row here (with explicit propagation order and notes). Do not edit `SKILL.md` to encode workflow-like behavior — the routing logic lives here.
