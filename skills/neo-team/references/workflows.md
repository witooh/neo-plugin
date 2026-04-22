# Workflow Pipeline Definitions

Each workflow lists the pipeline steps with explicit context-passing notes. Follow the order strictly — parallel steps are marked.

**Doc First principle:** Every workflow with code changes includes a **QA Test Spec** step before Developer. QA generates a test case document following the [`test-case-document.md`](test-case-document.md) template (GIVEN/WHEN/THEN format with test steps, expected results, test data, preconditions, and Workflow Chain for API dependencies). Developer uses this document to implement and write tests. For complex tasks, Developer uses TDD mode (Red-Green-Refactor per test case). For simple tasks, Developer implements normally and uses the spec as reference. During the Review Loop, QA converts test cases into executable E2E API tests following the [`e2e-playwright.md`](e2e-playwright.md) guide.

**Execution Report:** During the Review Loop, after QA runs E2E tests, QA generates an execution report following the [`test-execution-report.md`](test-execution-report.md) template — mapping each test case to its actual result, status, and defect references.

**Document Sync principle:** Every workflow with code changes includes a **Document Sync Phase** after the Review Loop passes. This phase ensures BA's AC document, Architect's system design, and QA's test cases remain accurate after implementation — because code evolves during development and review cycles. See the "Document Sync Phase" section below.

## New Feature

```
Complex task (Brainstorm + BA + Architect + Plan):
1. /brainstorm         → invoke brainstorm skill to explore the idea and clarify direction with the user
2. business-analyst    → structure requirements, generate AC document (acceptance-criteria.md template)
   Context: Brainstorm output (key decisions, constraints, scope)
   IF BA returns Open Questions:
      a. Orchestrator asks user for clarification (relay BA's questions)
      b. Orchestrator re-delegates to BA with user's answers
      c. Repeat until BA has no Open Questions
   Output: AC document written to `docs/design/{usecase}/acceptance-criteria.md` (no Open Questions remaining)
   Verification: BA re-reads generated document, verifies against template + quality gates, fixes issues (mandatory before handoff)
3. architect           → generate system design document (system-design.md template)
   Context: BA's AC document path (hard prerequisite — must read AC before designing)
   Output: API contracts written to `docs/design/{usecase}/api-contracts.md`, shared design to `docs/design/system-design/`
   Verification: Architect re-reads generated document, verifies structure + AC traceability + consistency with AC, fixes issues (mandatory before handoff)
4. /plan               → synthesize Architect's design into an implementation plan, present to user for confirmation
   Include: component breakdown, file changes, API contracts, implementation order
   Wait for user approval before proceeding
5. TEST CASE REVIEW LOOP → QA generates test cases, BA reviews for AC coverage (see Test Case Review Loop section)
   Context to QA: Architect's API contracts + BA's AC document (BOTH required — hard gate)
   Context to BA (reviewer): AC document + QA's test cases
6. developer           → implement code and unit tests (TDD mode)
   Context: Architect's design + confirmed plan + BA's acceptance criteria + QA's test case document (BA-approved)
   [If multiple independent components: spawn parallel developer agents]
7. REVIEW LOOP         → run the review-fix loop (see Review Loop section)
   Input: Developer's changed files + project conventions
8. [If task adds/changes API endpoints: delegate to `api-doc-gen` skill to update docs/api-doc.md]
9. DOCUMENT SYNC PHASE → sync all docs with final code (see Document Sync Phase section)
   Input: Developer's final changed files + INDEX.md (if exists) + all doc paths from prior steps

Simple task (BA first → Architect):
1. business-analyst    → clarify requirements, generate AC document (acceptance-criteria.md template)
   Context: User's request
   IF BA returns Open Questions:
      a. Orchestrator asks user for clarification (relay BA's questions)
      b. Orchestrator re-delegates to BA with user's answers
      c. Repeat until BA has no Open Questions
   Output: AC document written to `docs/design/{usecase}/acceptance-criteria.md` (no Open Questions remaining)
   Verification: BA re-reads generated document, verifies against template + quality gates, fixes issues (mandatory before handoff)
2. architect           → generate system design document (system-design.md template), ensuring design covers every AC-ID
   Context: BA's AC document path (hard prerequisite — must read AC before designing)
   Output: API contracts written to `docs/design/{usecase}/api-contracts.md`, shared design to `docs/design/system-design/`
   Verification: Architect re-reads generated document, verifies structure + AC traceability + consistency with AC, fixes issues (mandatory before handoff)
3. TEST CASE REVIEW LOOP → QA generates test cases, BA reviews for AC coverage (see Test Case Review Loop section)
   Context to QA: Architect's API contracts + BA's AC document (BOTH required — hard gate)
   Context to BA (reviewer): AC document + QA's test cases
4. developer           → implement code and unit tests
   Context: Architect's design + BA's AC document + QA's test case document (BA-approved)
   [If multiple independent components: spawn parallel developer agents]
5. REVIEW LOOP         → run the review-fix loop (see Review Loop section)
   Input: Developer's changed files + project conventions
6. [If task adds/changes API endpoints: delegate to `api-doc-gen` skill to update docs/api-doc.md]
7. DOCUMENT SYNC PHASE → sync all docs with final code (see Document Sync Phase section)
   Input: Developer's final changed files + INDEX.md (if exists) + all doc paths from prior steps
```

## Bug Fix

```
Complex bug (multi-file, ambiguous root cause, multiple fix strategies):
1. system-analyzer     → diagnose root cause
2. /plan               → synthesize root cause into a fix plan, present to user for confirmation
   Include: root cause summary, affected files/lines, proposed fix approach, risk assessment
   Wait for user approval before proceeding — bugs can have multiple valid fixes with different trade-offs
3. qa (test spec)      → generate test case document (test-case-document.md template)
   Context: System Analyzer's root cause + confirmed fix plan
   Mode: Test case document only — no test code, no review. Focus on regression test cases.
4. developer           → implement fix and unit/regression tests (TDD mode)
   Context: System Analyzer's root cause + confirmed fix plan + QA's test case document
   [If multiple independent fixes: spawn parallel developer agents]
5. REVIEW LOOP         → run the review-fix loop (see Review Loop section)
   Input: Developer's changed files + project conventions + System Analyzer's root cause (for QA regression test design)
6. [If fix changes API endpoints: delegate to `api-doc-gen` skill to update docs/api-doc.md]
7. DOCUMENT SYNC PHASE → sync all docs with final code (see Document Sync Phase section)
   Input: Developer's final changed files + INDEX.md (if exists) + all doc paths from prior steps
   Note: Bug Fix may not have BA/Architect docs — only sync agents whose docs exist for the affected usecase

Simple bug (single file, obvious root cause, straightforward fix):
1. system-analyzer     → diagnose root cause
2. qa (test spec)      → generate test case document (test-case-document.md template)
   Context: System Analyzer's root cause + affected files/lines
   Mode: Test case document only — no test code, no review. Focus on regression test cases.
3. developer           → implement fix and unit/regression tests
   Context: System Analyzer's root cause + affected files/lines + QA's test case document
4. REVIEW LOOP         → run the review-fix loop (see Review Loop section)
   Input: Developer's changed files + project conventions + System Analyzer's root cause (for QA regression test design)
5. [If fix changes API endpoints: delegate to `api-doc-gen` skill to update docs/api-doc.md]
6. DOCUMENT SYNC PHASE → sync all docs with final code (see Document Sync Phase section)
   Input: Developer's final changed files + INDEX.md (if exists) + all doc paths from prior steps
   Note: Bug Fix may not have BA/Architect docs — only sync agents whose docs exist for the affected usecase
```

## PR Review

Review-only workflow for external PRs — no code changes, no review loop. The goal is to provide structured feedback.
Typically invoked through the gitlab skill (or gh CLI), which provides the diff as input context.

```
Input: PR/MR diff + changed files (provided by the caller — e.g., gitlab skill, gh CLI)

1. code-reviewer + security + qa → review conventions, security, and test coverage (ALL PARALLEL)
   To all: PR diff + changed files + project conventions
2. Assemble review summary → return to caller
```

## Refactoring

```
Complex (cross-module, extract service, merge duplicates):
1. system-analyzer     → analyze current structure, dependencies, coupling risks
2. architect           → design target structure
   Context: System Analyzer's dependency map + current structure analysis
   Verification: Architect re-reads generated document, verifies structure + consistency with analysis, fixes issues (mandatory before handoff)
3. /plan               → present refactoring plan to user for confirmation
   Include: affected modules, target structure, migration steps, risk areas
   Wait for user approval before proceeding
4. qa (test spec)      → generate test case document (test-case-document.md template)
   Context: Architect's target structure + System Analyzer's dependency map
   Mode: Test case document only — no test code, no review. Focus on behavior preservation tests.
5. developer           → implement refactoring (TDD mode)
   Context: Architect's target structure + confirmed plan + QA's test case document
   [If multiple independent modules: spawn parallel developer agents]
6. REVIEW LOOP         → run the review-fix loop (see Review Loop section)
   Input: Developer's changed files + project conventions
7. [If refactoring changes API contracts: delegate to `api-doc-gen` skill to update docs/api-doc.md]
8. DOCUMENT SYNC PHASE → sync all docs with final code (see Document Sync Phase section)
   Input: Developer's final changed files + INDEX.md (if exists) + all doc paths from prior steps

Simple (single module, extract function, simplify logic):
1. system-analyzer     → analyze current code + identify dependencies
2. architect           → design target structure
   Context: System Analyzer's analysis
   Verification: Architect re-reads generated document, verifies structure + consistency with analysis, fixes issues (mandatory before handoff)
3. qa (test spec)      → generate test case document (test-case-document.md template)
   Context: Architect's target structure + System Analyzer's analysis
   Mode: Test case document only — no test code, no review. Focus on behavior preservation tests.
4. developer           → implement refactoring
   Context: Architect's target structure + QA's test case document
5. REVIEW LOOP         → run the review-fix loop (see Review Loop section)
   Input: Developer's changed files + project conventions
6. [If refactoring changes API contracts: delegate to `api-doc-gen` skill to update docs/api-doc.md]
7. DOCUMENT SYNC PHASE → sync all docs with final code (see Document Sync Phase section)
   Input: Developer's final changed files + INDEX.md (if exists) + all doc paths from prior steps
```

## Requirement Clarification

```
1. business-analyst    → clarify and structure requirements
   IF BA returns Open Questions:
      a. Orchestrator asks user for clarification (relay BA's questions)
      b. Orchestrator re-delegates to BA with user's answers
      c. Repeat until BA has no Open Questions
   Output: Structured requirements with all ambiguities resolved
   Verification: BA re-reads generated document, verifies against template + quality gates, fixes issues (mandatory before handoff)
2. architect           → validate technical feasibility
   Context: BA's structured requirements (fully clarified)
   Verification: Architect re-reads generated document, verifies structure + AC traceability + consistency with AC, fixes issues (mandatory before handoff)
3. Orchestrator updates docs/design/INDEX.md (create if not exists) with the new/updated usecase entry
```

## Test Case Review Loop

Quality gate for test case documents — ensures test cases fully cover acceptance criteria before Developer starts implementation. This loop catches vague assertions, missing business scenarios, and duplicate test cases early, when they're cheap to fix.

```
Test Case Review Loop:

┌─→ 1. qa (test spec) → generate test case document (test-case-document.md template)
│      Context: Architect's API contracts + BA's AC document (BOTH required — hard gate)
│      Mode: Test case document only — no test code, no review
│      Every test case MUST include "Traces To: AC-XXX" field
│
│   2. business-analyst (review) → review test cases against AC document
│      Check:
│      - Every AC-ID has at least one test case covering it
│      - Test cases use specific HTTP status codes from API contract (not >= 400)
│      - Error test cases assert error body structure (error.code + error.message)
│      - Business rules from AC are fully tested
│      - No duplicate/overlapping test cases
│      Output: Coverage assessment with Approved / Revise verdict
│
│   3. Evaluate:
│      ├── BA approves → DONE (proceed to Developer)
│      └── BA has findings:
│            a. Pass BA's findings to QA
│            b. QA regenerates/fixes test cases based on feedback
└────── c. Loop back to step 2 (BA re-reviews)

Max 3 review cycles. If still unresolved → deliver to user with gaps noted.
```

**Important:** The Test Case Review Loop replaces the old standalone `qa (test spec)` step in all workflows. Wherever you see `TEST CASE REVIEW LOOP` in a workflow, run this sub-workflow.

---

## Review Loop (Two-Stage)

Review-fix loop used as a sub-workflow embedded in other pipelines (e.g., New Feature, Bug Fix). The loop is split into two stages because verifying spec compliance first avoids wasting time reviewing code quality on an implementation that doesn't match the spec — if the spec is wrong, the code will be rewritten anyway.

```
Review Loop:

=== STAGE 1: Spec Compliance (QA) ===

QA verifies that the implementation matches the acceptance criteria and API contracts.

┌─→ 1. qa → generate E2E test code if not yet written (see e2e-playwright.md)
│         → run E2E tests
│         → generate execution report (test-execution-report.md template)
│         → validate AC coverage through API behavior
│      To QA: Developer's changed files + BA's AC document + Architect's API contracts + project conventions
│
│   2. Evaluate QA result:
│      ├── QA approves (Sign-Off: Approved, Status: DONE) → proceed to STAGE 2
│      └── QA has spec violations (Sign-Off: Blocked, Status: DONE_WITH_CONCERNS or BLOCKED):
│            a. Pass QA's spec violation findings to Developer (specific TC-IDs and expected vs actual behavior)
│            b. Developer fixes spec compliance issues
│            c. Developer completes fixes
└────── d. Loop back to Stage 1 step 1 (QA re-verifies)

Max 3 Stage 1 cycles. If still unresolved → escalate to user.

=== STAGE 2: Code Quality + Security (parallel) ===

Only runs AFTER Stage 1 passes. Code-reviewer and Security verify code quality and security in parallel.

┌─→ 1. code-reviewer + security → review conventions and security (PARALLEL)
│      To both: Developer's changed files + project conventions
│      Note: QA does NOT re-run — spec compliance is already verified from Stage 1
│
│   2. Evaluate results:
│      ├── BOTH agents approve → DONE (proceed to next workflow step or Summary)
│      └── ANY agent has blocking findings:
│            a. Collect all blocking feedback into a single prioritized list
│            b. Delegate to Developer to fix (pass specific file:line references)
│            c. Developer completes fixes
└────── d. Loop back to Stage 2 step 1 (re-run code-reviewer + security only)

Max 3 Stage 2 cycles. If still unresolved → escalate to user:

## Review Loop Failed — Needs Your Input

**Stage:** [1 — Spec Compliance | 2 — Code Quality + Security]

**Unresolved Findings:**
- [list of remaining Blocker/Critical/Blocked items with details]

**What was attempted:**
- Cycle 1: Developer fixed X, Y — but Z remains
- Cycle 2: Developer attempted Z — but [reason it failed]

**Recommendation:** [suggested path forward]

Blocking definitions:
- Stage 1 — QA: Sign-Off = "Blocked" or Status = BLOCKED
- Stage 2 — Code Reviewer: Blocker or Critical severity
- Stage 2 — Security: Critical or High severity

Non-blocking findings (Warning/Info/Medium/Low): present to user after the loop completes and ask whether to fix or skip.
```

---

## Document Sync Phase

After the Review Loop passes in any code-changing workflow, this phase ensures all documents still match the final implementation. Code evolves during development and review cycles — AC might have been partially re-scoped, design decisions might have changed, test cases might need new scenarios. This phase catches those drifts.

**Sequential order is mandatory:** BA → Architect → QA. Each agent reads the output of the previous one, preserving the traceability chain (AC → Design → Test Cases).

```
Document Sync Phase:

1. Orchestrator reads docs/design/INDEX.md (if exists) to identify potentially affected usecases
   → Also gathers: Developer's final changed files, all doc paths from prior pipeline steps
   → Determines which document-owning agents have existing docs for the affected usecase(s)

2. business-analyst (doc sync) → review AC document against final code
   Context: AC document path + Developer's changed files summary
   Mode: Doc Review & Update (see business-analyst.md reference)
   Output: "updated" (with path to updated doc) OR "no change needed" (with justification)
   IF updated → Document Verification & Fix applies (same as new document)
   IF no AC doc exists for this usecase → skip

3. architect (doc sync) → review both shared System Design AND per-usecase API Contracts against final code + latest AC
   Context: shared design paths (`docs/design/system-design/`) + usecase API contracts (`docs/design/{usecase}/api-contracts.md`) + Developer's changed files summary + BA's latest AC (from step 2)
   Mode: Doc Review & Update (see architect.md reference)
   Output: per-document assessment — "updated" or "no change needed" for each (shared design + API contracts separately)
   IF updated → Document Verification & Fix applies (same as new document)
   IF no design docs exist for this usecase → skip

4. qa (doc sync) → review Test Cases against final code + latest AC + latest Design
   Context: test case doc path (`docs/design/{usecase}/test-cases.md`) + Developer's changed files summary + BA's latest AC + Architect's latest API contracts (`docs/design/{usecase}/api-contracts.md`)
   Mode: Doc Review & Update (see qa.md reference)
   Output: "updated" (with path to updated doc) OR "no change needed" (with justification)
   IF updated → Verification applies (TC-IDs sequential, Summary table matches)
   IF no Test Case doc exists for this usecase → skip

5. Orchestrator updates docs/design/INDEX.md
   → Create INDEX.md if it does not exist
   → Add or update the usecase entry: usecase name, description, status, AC-IDs, last updated date
   → Follow the INDEX.md format defined in SKILL.md (Document Folder Structure Convention)

6. Orchestrator updates docs/design/VERSION.md
   → Create VERSION.md if it does not exist
   → Auto-increment version (e.g., v1.2 → v1.3)
   → Prepend a new entry at the top (latest version first) with:
     - Version number + date
     - Task description (what the user asked)
     - Usecase(s) touched (folder names under docs/design/)
     - List of changed files (collected from BA/Architect/QA sync outputs)
     - Extension summary — when ACs were appended to an existing usecase, record which AC-IDs were added/modified and what requirement triggered the extension. This preserves historical traceability that would otherwise be lost when appending into an existing folder.
   → Format:
     ## v{X.Y} — {YYYY-MM-DD}
     **Task:** {user's original request}
     **Usecase touched:** {usecase folder name(s)}
     **Changes:**
     - {file path} — {what changed}
     **Extension summary (if applicable):**
     - {usecase}: added AC-XXX..AC-YYY; modified AC-ZZZ
     - Triggering requirement: {short name or reference}
```

**Trust agent judgment:** If an agent reports "no change needed," accept it and move to the next agent. No cross-verification is required.

**Document consistency conflict:** If any agent reports that the document fundamentally conflicts with the implemented code (not just minor drift but a real mismatch that cannot be resolved by updating the doc), the Orchestrator must escalate to the user to decide whether to update the doc or change the code.

**Agent failure:** If a doc sync agent fails or returns empty output, log the gap in the Summary but do NOT block the pipeline. Document Sync is a quality gate, but the code has already passed the Review Loop.

**PR Review workflow:** Excluded from Document Sync — PR Review only reviews code, it does not change it.
