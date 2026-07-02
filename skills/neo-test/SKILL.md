---
name: neo-test
description: >
  Entry point for the Verify phase of the neo workflow — prove behavior with
  tests. Delegates to `test-driven-development` as the method (write a failing
  test, implement, verify; the Prove-It pattern for bugs) and composes
  `browser-testing-with-devtools` for browser issues and `e2e-playwright` for
  AC-driven HTTP acceptance testing. Use when writing or running tests, when a
  bug report arrives, when verifying a task against its acceptance criteria, or
  when you invoke /neo-test. The method itself is `test-driven-development`.
---

# Neo Test — test-driven verification entry point

## Overview

This is the neo entry point for the Verify phase. It orchestrates
`test-driven-development` as the underlying method and composes the right
verifier for the surface under test — `browser-testing-with-devtools` for
browser-facing behavior and `e2e-playwright` for AC-driven HTTP acceptance
testing. It does **not** reimplement the test method; the method lives in
`test-driven-development`.

## When to Use

- When implementing logic, fixing a bug, or changing behavior.
- When verifying a task against its acceptance criteria.
- When you invoke `/neo-test`.
- Route elsewhere: for the bare TDD method → `test-driven-development`; for
  browser runtime checks → `browser-testing-with-devtools`; for AC-traceable HTTP
  e2e → `e2e-playwright`.

## The Workflow

**For new features:**
1. Write tests that describe the expected behavior (they should FAIL).
2. Implement the code to make them pass.
3. Refactor while keeping tests green.

**For bug fixes (Prove-It pattern):**
1. Write a test that reproduces the bug (it must FAIL).
2. Confirm the test fails.
3. Implement the fix.
4. Confirm the test passes.
5. Run the full test suite for regressions.

For browser-related issues, also invoke `browser-testing-with-devtools` to verify
with the Chrome DevTools MCP. For HTTP/API acceptance testing driven by
acceptance criteria (a service with a Jest + Playwright-`request` e2e harness),
also invoke `e2e-playwright` to author and run the AC-traceable suite and map
pass/fail to each AC.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I'll write the test after the code." | A test written after the fact rarely fails first — you can't prove it tests anything. Write the failing test first. |
| "This bug is obvious, just fix it." | Without a reproducing test that fails first (Prove-It), you can't prove the fix works or guard against regression. |
| "The feature tests pass, skip the full suite." | Regressions surface outside the feature — run the whole suite. |

## Red Flags

- Tests written after the implementation, never seen to fail.
- A bug fix with no reproducing test.
- Skipping the regression run after a fix.
- Claiming an acceptance criterion is met with no test that exercises it.

## Verification

- Each new test was seen to FAIL before the implementation made it PASS.
- The full suite is green (no regressions).
- Every HTTP-observable acceptance criterion is exercised by a passing test
  (via `e2e-playwright` where an e2e harness exists).
- `test-driven-development`'s own verification is satisfied.
