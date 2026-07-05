---
name: neo-plan
description: >
  Entry point for the Plan phase of the neo workflow — turn an approved spec
  into ordered, verifiable tasks. Delegates to `planning-and-task-breakdown` as
  the method and applies neo conventions: read docs/tasks/<card>/spec.md, slice
  work vertically (one complete path per task), then write docs/tasks/<card>/plan.md
  and docs/tasks/<card>/todo.md. Use when a spec exists and you need a task
  breakdown, when work feels too large to start, or when you invoke /neo-plan.
  The method itself is `planning-and-task-breakdown`.
---

# Neo Plan — task-breakdown entry point

## Overview

This is the neo entry point for the Plan phase. It orchestrates
`planning-and-task-breakdown` as the underlying method and layers neo's task-file
conventions on top (the `docs/tasks/<card>/` layout, vertical slicing, per-task
verification). It does **not** reimplement planning; the method lives in
`planning-and-task-breakdown`.

## When to Use

- When an approved spec exists and you need to break it into implementable tasks.
- When work feels too large to start, or parallel work is possible.
- When you invoke `/neo-plan`.
- Route elsewhere: for the bare planning method with no neo task-file conventions
  → `planning-and-task-breakdown`; to start implementing → `neo-build`; if there
  is no spec yet → `neo-spec`.

## The Workflow

Ask the user for the feature name or JIRA card id to use as the task-folder name
(`<card>`). Read `docs/tasks/<card>/spec.md` and the relevant codebase sections.
Then:

1. Enter plan mode — read only, no code changes.
2. Identify the dependency graph between components.
3. Slice work **vertically** — one complete path per task, not horizontal layers.
4. Write tasks with acceptance criteria and verification steps.
5. Add checkpoints between phases.
6. Present the plan for human review.

Save the plan to `docs/tasks/<card>/plan.md` and the task list to
`docs/tasks/<card>/todo.md`.

Re-planning a card whose `plan.md` already exists? Preserve dated history notes
and completed-task lines, and sync any decision or scope change this revision
introduces into `spec.md` and `todo.md` per `references/task-docs-sync.md` — a
revised plan must not silently contradict the docs around it.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The plan is in my head, I don't need plan.md." | The persisted `plan.md`/`todo.md` are what let Build resume across sessions and what `/neo-build auto` reads. |
| "Horizontal layers are easier to plan." | Vertical slices (one working path per task) keep every task independently verifiable; horizontal layers can't be tested alone. |
| "Tasks don't each need acceptance criteria." | A task with no verification step can't be proven done — Build needs a per-task bar. |

## Red Flags

- Starting to implement with no `docs/tasks/<card>/plan.md`.
- Tasks sliced by layer (all models, then all handlers) instead of by path.
- Tasks with no acceptance criteria or verification step.
- Editing code during planning (plan mode is read-only).

## Verification

- `docs/tasks/<card>/plan.md` and `docs/tasks/<card>/todo.md` are written.
- Every task has acceptance criteria and a verification step.
- Tasks are vertical slices in dependency order, with checkpoints between phases.
- `planning-and-task-breakdown`'s own verification is satisfied and the plan was
  presented for human review.
- On a re-plan: dated history and completed-task lines survived, and
  `spec.md`/`todo.md` carry no state the revision superseded
  (`references/task-docs-sync.md`).
