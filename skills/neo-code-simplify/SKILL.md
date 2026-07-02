---
name: neo-code-simplify
description: >
  Entry point for the neo Review-phase simplification pass — reduce complexity
  without changing behavior. Delegates to `code-simplification` as the method and
  applies neo conventions: read CLAUDE.md and project conventions, target
  recently changed code, simplify incrementally running tests after each change,
  then re-review the result via `code-review-and-quality`. Use when code works but
  reads as more complex than it should, when refactoring for clarity, or when you
  invoke /neo-code-simplify. The method itself is `code-simplification`.
---

# Neo Code-Simplify — behavior-preserving simplification entry point

## Overview

This is the neo entry point for the simplification pass in the Review phase. It
orchestrates `code-simplification` as the underlying method and layers neo's
conventions on top (ground in CLAUDE.md, target recent changes, test after each
step, re-review at the end). It does **not** reimplement simplification; the
method lives in `code-simplification`.

## When to Use

- When code works but is harder to read, maintain, or extend than it should be.
- When refactoring recently changed code for clarity without changing behavior.
- When you invoke `/neo-code-simplify`.
- Route elsewhere: for the bare simplification method → `code-simplification`; to
  *find* correctness/quality issues rather than simplify → `neo-review`.

## The Workflow

Simplify recently changed code (or the specified scope) while preserving exact
behavior:

1. Read CLAUDE.md and study project conventions.
2. Identify the target code — recent changes unless a broader scope is specified.
3. Understand the code's purpose, callers, edge cases, and test coverage before
   touching it.
4. Scan for simplification opportunities: deep nesting → guard clauses or
   extracted helpers; long functions → split by responsibility; nested ternaries
   → if/else or switch; generic names → descriptive names; duplicated logic →
   shared functions; dead code → remove after confirming.
5. Apply each simplification incrementally — run tests after each change.
6. Verify all tests pass, the build succeeds, and the diff is clean.

If tests fail after a simplification, revert that change and reconsider. Then
re-review the result via `code-review-and-quality`.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I'll simplify everything, then run tests once at the end." | Incremental changes with tests after each one localize any regression to a single revertible step. |
| "This rename/refactor also improves the logic." | Simplification preserves behavior exactly; a behavior change belongs in a separate, tested step. |
| "While I'm here, I'll clean up adjacent code too." | Stay in scope — target the changed code, not an unsolicited renovation. |

## Red Flags

- Behavior changed (outputs differ) — that is a refactor bug, not a simplification.
- Simplifying without running tests between steps.
- Touching code orthogonal to the target scope.
- Removing code you don't fully understand without confirming it is dead.

## Verification

- All tests pass and the build succeeds after every incremental change.
- Behavior is unchanged (same inputs → same outputs).
- The diff is clean and scoped to the target code.
- The result was re-reviewed via `code-review-and-quality`.
