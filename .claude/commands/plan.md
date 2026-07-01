---
description: Break work into small verifiable tasks with acceptance criteria and dependency ordering
---

Invoke the neo:planning-and-task-breakdown skill.

Ask the user for the feature name or JIRA card id to use as the task folder name (`<card>`). Read the existing spec at `docs/tasks/<card>/spec.md` and the relevant codebase sections. Then:

1. Enter plan mode — read only, no code changes
2. Identify the dependency graph between components
3. Slice work vertically (one complete path per task, not horizontal layers)
4. Write tasks with acceptance criteria and verification steps
5. Add checkpoints between phases
6. Present the plan for human review

Save the plan to `docs/tasks/<card>/plan.md` and task list to `docs/tasks/<card>/todo.md`.
