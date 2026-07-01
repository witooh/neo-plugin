---
description: Start spec-driven development — write a structured specification before writing code
---

Invoke the neo:spec-driven-development skill.

Begin by understanding what the user wants to build. Ask clarifying questions about:
1. The objective and target users
2. Core features and acceptance criteria
3. Tech stack preferences and constraints
4. Known boundaries (what to always do, ask first about, and never do)

Then generate a structured spec covering all six core areas: objective, commands, project structure, code style, testing strategy, and boundaries.

Ask the user for the feature name or JIRA card id to use as the task folder name (`<card>`). Save the spec to `docs/tasks/<card>/spec.md` (create the folder if it doesn't exist) and confirm with the user before proceeding.
