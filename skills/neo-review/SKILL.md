---
name: neo-review
description: >
  Entry point for the Review phase of the neo workflow — multi-axis code review
  before merge. Delegates to `code-review-and-quality` as the review method, then
  layers neo conventions: six axes (correctness, readability, architecture,
  security via `security-and-hardening`, performance via `performance-optimization`,
  and a neo-added Conventions & Style axis) with findings labeled
  Critical / Important / Suggestion and anchored to file:line. Use when reviewing
  a change before merge, reviewing code you or another agent wrote, or when you
  invoke /neo-review. The review method itself is `code-review-and-quality`.
---

# Neo Review — six-axis review entry point

## Overview

This is the neo entry point for the Review phase. It orchestrates
`code-review-and-quality` as the underlying method and layers neo's conventions
on top — a sixth Conventions & Style axis and severity-labeled, `file:line`-anchored
findings. It does **not** reimplement the review method; the method lives in
`code-review-and-quality`.

## When to Use

- Before merging any change, or when reviewing code you or another agent wrote.
- When you invoke `/neo-review`.
- Route elsewhere: for the bare review method with no neo axis/labeling
  conventions → `code-review-and-quality`; to *simplify* working code rather than
  review it → `neo-code-simplify`; for a full pre-ship gate with parallel
  specialist subagents → `neo-ship`.

## The Workflow

Run `code-review-and-quality` across all six axes on the staged changes or
recent commits:

1. **Correctness** — matches the spec? edge cases handled? tests adequate?
2. **Readability** — clear names, straightforward logic, well organized?
3. **Architecture** — follows existing patterns, clean boundaries, right
   abstraction level?
4. **Security** — input validated, secrets safe, auth checked? (draw on
   `security-and-hardening`)
5. **Performance** — no N+1 queries, no unbounded ops? (draw on
   `performance-optimization`)
6. **Conventions & Style** *(neo-added)* — matches the project's naming,
   formatting, file layout, and idioms; consistent with the linter/formatter
   config and neighboring code. Flag every deviation.

Categorize each finding **Critical / Important / Suggestion** and output it with
a specific `file:line` reference and a fix recommendation.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "Tests pass, so it's reviewed." | Passing tests say nothing about architecture, security, or conventions — run all six axes. |
| "Conventions are just nits, skip axis 6." | Conventions & Style is a named axis; deviations from the linter and neighboring code are findings, not nits. |
| "I wrote it, it reads fine to me." | Authors are blind to their own assumptions — that is exactly what a review catches. |
| "I'll just say LGTM." | A review with no `file:line` evidence and no severity labels is not a review. |

## Red Flags

- A review that runs only the five upstream axes and skips Conventions & Style.
- "LGTM" or approval with no `file:line` evidence.
- Findings with no Critical / Important / Suggestion label.
- Reviewing without reading the spec or acceptance criteria the change claims to satisfy.

## Verification

- All six axes were evaluated (including the neo-added Conventions & Style).
- `code-review-and-quality`'s own verification is satisfied (Critical and
  Important findings resolved or explicitly accepted by the user).
- Every finding carries a severity label and a `file:line` reference.
