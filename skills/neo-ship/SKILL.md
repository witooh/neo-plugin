---
name: neo-ship
description: >
  Entry point for the Ship phase of the neo workflow — a fan-out orchestrator
  that runs three specialist subagents (`code-reviewer`, `security-auditor`,
  `test-engineer`) in parallel, then merges their reports into one go/no-go
  decision with a mandatory rollback plan. Delegates to `shipping-and-launch` for
  the checklist; on API drift it reconciles docs/api/ via `api-spec`
  Update-from-code, then refreshes deliverables via `open-collection` and
  `confluence-api-doc`. Use when preparing a production-bound change, for a
  pre-launch review, or when you invoke /neo-ship. The checklist method is
  `shipping-and-launch`.
---

# Neo Ship — pre-launch fan-out orchestrator entry point

## Overview

This is the neo entry point for the Ship phase. It is a fan-out orchestrator:
three specialist subagents review the change in parallel, then the main agent
merges their reports into a single go/no-go decision with a rollback plan. It
delegates to `shipping-and-launch` for the checklist and, on API drift, reconciles
`docs/api/` via `api-spec` and refreshes the api-doc deliverables. It does **not**
reimplement the checklist method.

## When to Use

- When preparing a production-bound change, or running a pre-launch review.
- When you invoke `/neo-ship`.
- Route elsewhere: for the bare launch checklist → `shipping-and-launch`; for
  ad-hoc commits (not releases) → `neo-commit`; for a single-axis code review →
  `neo-review`.

## The Workflow

### Phase A — Parallel fan-out

Spawn three subagents concurrently using the Agent tool. **Issue all three Agent
calls in a single turn so they execute in parallel** — sequential calls defeat
the purpose. In Claude Code each call passes `subagent_type` matching the
specialist's `name`:

1. **`code-reviewer`** — five-axis review (correctness, readability, architecture,
   security, performance) on the staged changes or recent commits.
2. **`security-auditor`** — vulnerability + threat-model pass (OWASP Top 10,
   secrets, auth/authz, dependency CVEs).
3. **`test-engineer`** — test-coverage analysis (happy path, edge cases, error
   paths, concurrency gaps).

In harnesses without an Agent tool, run each specialist's pass sequentially and
treat the outputs as if returned in parallel — the merge still works. Subagents
cannot spawn other subagents; each returns only its report. If you have your own
`code-reviewer` / `security-auditor` / `test-engineer` defined, those take
precedence.

### Phase B — Merge in main context

Once all three reports are back, the main agent (not a sub-persona) synthesizes:
Code Quality (aggregate Critical/Important + failing tests/lint/build), Security
(promote Critical/High to blockers), Performance (the review's perf axis + CWV if
applicable), Accessibility, Infrastructure (env, migrations, monitoring, flags),
and Documentation. If the service has a `docs/api/` spec, verify it still matches
the shipped code; on drift, reconcile via `api-spec` Update-from-code (structural
sync-back — sync routes/fields/types, preserve hand-authored M/O,
`business_logic`, `remark`, `errors`), then refresh deliverables via
`open-collection` and `confluence-api-doc` if maintained.

### Phase C — Decision and rollback

Produce one output: **Ship Decision: GO | NO-GO**, then Blockers (must fix),
Recommended fixes (should fix), Acknowledged risks (shipping anyway), a
**Rollback plan** (trigger conditions, procedure, recovery-time objective), and
the full specialist reports.

### Rules

- The three Phase A subagents run in parallel, never sequentially.
- Subagents don't call each other; the main agent merges in Phase B.
- The rollback plan is mandatory before any GO.
- If any subagent returns a Critical finding, the default is NO-GO unless the user
  explicitly accepts the risk.
- **Skip the fan-out only if all are true:** ≤2 files, <50 lines, and it doesn't
  touch auth, payments, data access, or config/env. Otherwise default to fan-out.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I'll run the three reviews one after another." | Issue all three Agent calls in one turn — sequential calls defeat the parallel fan-out. |
| "The diff looks small, skip the fan-out." | Skip only if ≤2 files, <50 lines, and no auth/payments/data/config — otherwise fan out. |
| "GO — I'll figure out rollback if it breaks." | The rollback plan is mandatory before any GO decision. |
| "A Critical finding, but let's ship anyway." | A Critical finding defaults to NO-GO unless the user explicitly accepts the risk. |

## Red Flags

- Running the three specialists sequentially instead of one parallel turn.
- A GO decision with no rollback plan.
- Shipping past a Critical finding without explicit user sign-off.
- A `docs/api/` spec that drifted from the shipped code and wasn't reconciled.

## Verification

- All three specialist reports were produced (in parallel where an Agent tool exists).
- The merge covers code quality, security, performance, accessibility,
  infrastructure, and documentation.
- The output is a single GO/NO-GO with blockers, risks, and a mandatory rollback plan.
- Any `docs/api/` drift was reconciled via `api-spec` (and deliverables refreshed
  if maintained).
