# Pipeline Completion Guard

<HARD-GATE>
Before declaring a task complete, verify ALL pipeline steps have been executed. This is a hard gate — the Orchestrator CANNOT write the Summary until every checkpoint below is verified with **evidence from actual agent output**, not assumptions.

**Evidence-Based Verification:** "Should pass" ≠ "passes." Every gate must be backed by concrete agent output:
- "All tests pass" must be backed by QA's execution report showing actual test results
- "Review Loop completed" must have actual verdicts from code-reviewer, security, and QA — not "I think it passed"
- "Document verified" must have the agent's confirmation that they re-read and checked the document
- If you cannot point to specific agent output proving a gate is met, the gate is NOT met
</HARD-GATE>

## Checklist (run mentally before writing Summary)

```
For every workflow that includes code changes:
  --- Acceptance Criteria Gate ---
  ✅ BA generated acceptance criteria document? (MANDATORY — BA writes AC doc before Architect starts)
  ✅ AC document has AC-IDs, explicit business rules, and GIVEN/WHEN/THEN format?
  ✅ BA has zero Open Questions remaining? (all clarifications resolved with user)
  ✅ BA verified document? (re-read from disk, checked against template + quality gates, fixed issues)
  ✅ BA Status is DONE? (not BLOCKED or NEEDS_CONTEXT)

  --- System Design Gate ---
  ✅ Architect generated system design document? (MANDATORY — Architect writes design doc before QA starts)
  ✅ System design document covers every AC-ID? (AC Traceability table is complete)
  ✅ Architect verified document? (re-read from disk, checked structure + AC traceability + consistency with AC, fixed issues)
  ✅ Architect Status is DONE? (not BLOCKED or NEEDS_CONTEXT)

  --- Test Case Review Loop Gate ---
  ✅ QA test spec generated? (MANDATORY — QA generates test spec before Developer starts)
  ✅ QA test cases trace to AC-IDs? (every TC has "Traces To: AC-XXX")
  ✅ Test Case Review Loop passed? (BA reviewed and approved test cases)
  ✅ Developer has completed implementation?
  ✅ Developer Status is DONE? (if DONE_WITH_CONCERNS → concerns reviewed before proceeding)

  --- Review Loop Gate (Two-Stage) ---
  ✅ Stage 1 completed? QA invoked with spec compliance check, Sign-Off is Approved
  ✅ Stage 2 completed? Code Reviewer AND Security invoked (MANDATORY if listed in the workflow)
  ✅ Review loop / remediation loop ran? (if any agent returned blocking findings)
  ✅ All blocking findings resolved or escalated to user?
  ✅ API doc updated? (if task adds/changes/removes API endpoints — delegate to api-doc-gen AFTER review passes)

  --- Status Protocol Gate ---
  ✅ No agent returned BLOCKED without resolution? (every BLOCKED status was addressed)
  ✅ No agent returned NEEDS_CONTEXT without follow-up? (context was provided, agent re-dispatched)
  ✅ All DONE_WITH_CONCERNS have been reviewed? (concerns acknowledged, decision made to proceed or address)

  --- Document Sync Gate ---
  ✅ Document Sync Phase invoked? (MANDATORY for all code-changing workflows after Review Loop passes)
  ✅ BA confirmed AC doc is in sync? (output: "updated" or "no change needed" — skip if no AC doc exists)
  ✅ Architect confirmed both shared System Design and per-feature API Contracts are in sync? (output per document: "updated" or "no change needed" — skip if no design docs exist)
  ✅ QA confirmed Test Cases are in sync? (output: "updated" or "no change needed" — skip if no test case doc exists)
  ✅ INDEX.md updated or created? (feature entry with current status and last-updated date)
  ✅ VERSION.md updated? (new version entry prepended with task description + changed files list)
  ✅ No unresolved document consistency conflicts? (if any agent flagged a fundamental mismatch → escalated to user)

  --- E2E Verification Gate (after QA returns) ---
  ✅ QA output contains "E2E Test Execution" section?
  ✅ If QA reports "E2E tests found: Yes" → result is not "Failed"?
     → If E2E failed due to current changes → trigger review/remediation loop (QA is Blocked)
     → If E2E failed due to pre-existing issues → accept as Warning, note in Summary
  ✅ If QA reports "E2E tests found: No" → acceptable, no action needed

If ANY checkbox is ❌ → DO NOT write the Summary. Continue the pipeline.
```

## Common Mistake: Stopping After Developer

The most frequent pipeline failure is stopping after Developer returns successful output. Developer output feels like "the job is done" because the code is written — but **unreviewed code is unfinished work**.

After Developer completes, ALWAYS check: **what's the next step in this workflow?** If verification agents remain, delegate to them immediately in the same response.

## Pipeline Step Tracking

When starting a workflow, mentally track which steps remain:

```
Example: New Feature (Complex)
  [ ] Step 1: /brainstorm
  [ ] Step 2: business-analyst (generate AC document — loop until zero Open Questions)
  [ ] Step 3: architect (generate system design document — must cover every AC-ID)
  [ ] Step 4: /plan (confirm with user)
  [ ] Step 5: TEST CASE REVIEW LOOP (QA writes test cases → BA reviews → loop)
  [ ] Step 6: developer (TDD mode)
  [ ] Step 7: REVIEW LOOP (code-reviewer + security + qa loop)  ← DON'T FORGET THIS
  [ ] Step 8: api-doc-gen (if API impacted)
  [ ] Step 9: DOCUMENT SYNC PHASE (BA → Architect → QA sync docs + update INDEX.md)

Example: New Feature (Simple)
  [ ] Step 1: business-analyst (generate AC document — loop until zero Open Questions)
  [ ] Step 2: architect (generate system design document — must cover every AC-ID)
  [ ] Step 3: TEST CASE REVIEW LOOP (QA writes test cases → BA reviews → loop)
  [ ] Step 4: developer
  [ ] Step 5: REVIEW LOOP (code-reviewer + security + qa loop)  ← DON'T FORGET THIS
  [ ] Step 6: api-doc-gen (if API impacted)
  [ ] Step 7: DOCUMENT SYNC PHASE (BA → Architect → QA sync docs + update INDEX.md)
```

Mark each step as you complete it. Only write the Summary when all steps are marked done.
