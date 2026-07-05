---
name: neo-build
description: >
  Entry point for the Build phase of the neo workflow — implement tasks
  incrementally, each test-driven, verified, and committed. Composes
  `incremental-implementation` and `test-driven-development`; invoked with no mode
  it asks whether to run autonomously — `single` does the next pending task then
  stops, and `auto` runs the whole docs/tasks/<card>/plan.md in one approved pass
  (single checkpoint, per-task commits, stopping on blockers via
  `debugging-and-error-recovery` and `doubt-driven-development`). Use when a spec
  and plan exist and you are ready to write code, when implementing a task slice,
  or when you invoke /neo-build, /neo-build single, or /neo-build auto. The methods
  are `incremental-implementation` and `test-driven-development`.
---

# Neo Build — incremental, test-driven Build entry point

## Overview

This is the neo entry point for the Build phase. It composes
`incremental-implementation` and `test-driven-development` as the underlying
methods and adds neo's build orchestration: a default one-task-at-a-time mode and
an `auto` mode that runs the whole plan in a single approved pass with per-task
commits. It does **not** reimplement those methods; they live in their own skills.

## When to Use

- When a spec and plan exist and you are ready to write code.
- When implementing the next task slice, or (auto) the whole plan.
- When you invoke `/neo-build` or `/neo-build auto`.
- Route elsewhere: for the bare methods → `incremental-implementation` /
  `test-driven-development`; if no plan exists yet → `neo-plan`; when something
  breaks → `debugging-and-error-recovery`.

## The Workflow

### Modes

- **`/neo-build`** (no mode arg) — **ask first**: "Run autonomously through the
  whole plan (auto), or one task at a time (single)?" Wait for the answer, then run
  that mode. Don't assume a default — the ask is the point.
- **`/neo-build single`** — implement the *next* pending task, then stop (one slice
  at a time). Skips the ask.
- **`/neo-build auto`** — generate the plan if needed, get a single approval, then
  implement *every* task without stopping between them. Skips the ask.

Mode keyword: `auto` (or `all`) selects autonomous mode; `single` (or `one`/`next`)
selects single-task mode; no keyword means ask. Autonomous mode is not faster *per
task* — it runs the same test-driven loop — it only removes the human stepping
*between* tasks.

### Single: one task

Pick the next pending task from the plan, then: (1) read the task's acceptance
criteria; (2) load relevant context (existing code, patterns, types); (3) write a
failing test for the expected behavior (RED); (4) implement the minimum code to
pass (GREEN); (5) run the full test suite for regressions; (6) run the build to
verify compilation; (7) commit with a descriptive message; (8) mark the task
complete and sync the task docs — `todo.md` status, plus `plan.md`/`spec.md`
wherever a decision, scope change, or resolution from this task appears (see
`references/task-docs-sync.md`) — and stop.

### Autonomous: the whole plan (`/neo-build auto`)

1. **Require a spec.** Ask for the feature name or JIRA card id (`<card>`) and
   look only for `docs/tasks/<card>/spec.md`. A README doesn't count. If none
   exists, stop and tell the user to run `/neo-spec` first — don't invent
   requirements.
2. **Establish a clean baseline.** `git status --porcelain`; if there are
   uncommitted changes outside `docs/tasks/<card>/`, stop and ask how to handle
   them (per-task commits must not absorb unrelated work).
3. **Plan if needed.** If there is no `docs/tasks/<card>/plan.md`, invoke
   `planning-and-task-breakdown` to generate one.
4. **Single checkpoint.** Present the full plan and wait for an unambiguous
   affirmative ("approve", "go", "yes"); treat hedged replies as not approved.
   This is the only human gate — after approval, run autonomously. Commit a
   generated `plan.md` as a single preparatory commit so it doesn't bleed into
   the first task.
5. **Execute every task in dependency order.** For each task run the full default
   loop (RED → GREEN → regression → build → commit → mark complete). Stage only
   the files that task touched plus its status update — never `git add -A` — one
   commit per task so any point is a clean rollback. A task whose outcome
   changed a decision, scope, or blocker state also syncs `plan.md`/`spec.md`
   per `references/task-docs-sync.md` in the same commit.
6. **Stop and ask** (don't push through) when a test can't pass or the build
   breaks without an obvious fix (→ `debugging-and-error-recovery`); the spec is
   ambiguous; or a task is high-risk/irreversible — auth, destructive migrations,
   payments, deletions, deploys, secrets, or anything you can't `git revert` (→
   `doubt-driven-development`, get explicit sign-off). After a blocker is
   resolved, re-invoking `/neo-build auto` resumes from the next pending task.
7. **Summarize at the end:** tasks completed, tests added, commits made, anything
   skipped or flagged.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I'll write all the code, then the tests." | Each task earns a failing test first (RED→GREEN) — that's the discipline `auto` preserves, not removes. |
| "auto means I can skip the per-task commits." | Per-task commits are what make any point a clean rollback — one commit per task, staged precisely. |
| "This migration is probably fine, keep going." | High-risk/irreversible steps are a mandatory stop-and-ask, even in auto mode. |
| "No plan yet, I'll just start coding." | Require `docs/tasks/<card>/spec.md` (and a plan); don't invent requirements. |
| "Bare /neo-build, I'll just do one task." | No mode arg means ask auto-vs-single first — don't assume single. |

## Red Flags

- Implementing without a failing test first.
- `git add -A` in a per-task commit, absorbing unrelated changes.
- Pushing through a broken build/test or a high-risk step in auto mode.
- Starting with no spec/plan and inventing requirements.
- Picking a mode on a bare `/neo-build` (no mode arg) instead of asking
  auto-vs-single first.

## Verification

- Every task has a failing-then-passing test and its own commit.
- The full suite is green and the build compiles after each task.
- `incremental-implementation` and `test-driven-development` verifications are
  satisfied per slice.
- In auto mode: one approval gate, per-task commits, and a final summary of what
  was done, skipped, or flagged.
- Task docs are in sync after each task (`references/task-docs-sync.md`): no
  stale decision/scope/blocker state left in `spec.md`/`plan.md`/`todo.md`.
- Invoked with no mode arg, neo-build asks auto-vs-single before doing any work.
