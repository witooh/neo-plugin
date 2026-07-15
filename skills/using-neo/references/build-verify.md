# Build and Verify Contracts

Read only the section selected by `using-neo`.

## Build

Invoke `incremental-implementation` and `test-driven-development`. Repository
guidance and the approved plan remain authoritative.

### Select the mode

- **single:** implement the next pending task, then stop.
- **auto:** execute the approved plan in dependency order after one explicit
  approval.
- If mode is omitted, infer it only from clear wording: “next task” selects
  single; “implement the approved/full plan” selects auto. Otherwise ask.

### Single task

1. Read the task, its AC IDs, and relevant context.
2. Write a failing test for the expected behavior and prove RED.
3. Implement the minimum change and prove GREEN.
4. Run regression tests and the build.
5. Commit only if the user has authorized it and repository rules allow it.
6. Mark the task complete and sync any decision, scope, or blocker change across
   task documents; then stop.

### Auto plan

1. Require `docs/tasks/<card>/spec.md`; a README is not a substitute.
2. Check `git status --porcelain`. If unrelated work could be absorbed, stop and
   ask how to isolate it.
3. Generate `plan.md` with `planning-and-task-breakdown` only when missing.
4. Present the complete plan and require an unambiguous approval.
5. Execute each task in dependency order using the same RED -> GREEN ->
   regression -> build -> status-sync loop as single mode.
6. Stage precisely and make one commit per task only when the approval and
   repository rules authorize agent commits; never use blind staging.
7. Stop when a test/build failure lacks an obvious bounded fix, the spec is
   ambiguous, or the work reaches a high-risk/irreversible operation. Use
   `debugging-and-error-recovery` or `doubt-driven-development` as appropriate.
8. Resume from the next pending task after the blocker is resolved. Finish with
   completed tasks, tests, commits, skipped work, and risks.

**Exit evidence:** every completed task has RED/GREEN proof, regression and
build results, synchronized status, and no unrelated changes or unauthorized
commits.

## Verify

Invoke `test-driven-development` for new behavior and bug fixes.

### New behavior

1. Write a test that describes the expected outcome and prove it fails.
2. Implement the minimum behavior that makes it pass.
3. Refactor only while the suite remains green.

### Bug fix — Prove-It

1. Write a reproduction test and prove the reported failure.
2. Implement the smallest root-cause fix.
3. Prove the reproduction passes and run the full regression suite.

### Runtime companions

- Browser-facing behavior also invokes `browser-testing-with-devtools` for DOM,
  console, network, accessibility, and visual runtime evidence.
- AC-driven HTTP acceptance behavior invokes `e2e-playwright` when the service
  has the Jest + Playwright-request harness; map every result back to its AC ID.

**Exit evidence:** no skipped tests, failure-before/fix-after proof exists,
regressions are green, and runtime or AC evidence is recorded when applicable.
