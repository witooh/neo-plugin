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

## Propagation Rules

- **Sequential by default.** Each role waits for the previous role's output, with a checkpoint in between (Review / Continue / Stop).
- **Dev loop** is the only auto-continuous segment: **Developer → QA → Code Reviewer** runs without inner checkpoints until QA passes AND Code Reviewer has no blockers. One combined checkpoint is shown after the loop ends.
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
