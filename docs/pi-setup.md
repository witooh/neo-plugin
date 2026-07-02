# Using neo with pi

This guide explains how to use neo with [pi](https://pi.dev) — a minimal, extensible AI coding-agent CLI. neo ships as a **pi package**: its skills load directly, and pi selects and runs them on demand.

## Overview

pi is skill-first and aggressively extensible: capabilities are packaged as skills, prompts, extensions, and themes, and installed from npm, git, or a local path. neo's `skills/<name>/SKILL.md` files already match pi's skill format (`name` + `description` frontmatter), so every neo skill loads in pi with no conversion.

pi has no native slash-command, subagent, or hook system, so — as with OpenCode — neo runs here as an **agent-driven workflow**: skills are selected automatically from intent rather than invoked by command.

---

## Installation

neo declares a pi package manifest (`package.json` with a `pi` field), so it installs as a package.

**Install from the repo (git):**

```bash
pi install git:github.com/witooh/neo-plugin
```

**Install from a local clone:**

```bash
git clone https://github.com/witooh/neo-plugin.git
pi install ./neo-plugin
```

By default `pi install` writes to user settings (`~/.pi/agent/settings.json`), making neo's skills available in every project.

**Use without installing (project-local):**

pi auto-discovers skills from a project's `.pi/skills/` directory. The neo repo already includes a `.pi/skills` symlink to its `skills/` directory, so opening neo itself in pi exposes all skills with no install step.

---

## How It Works

### 1. Skill Discovery

pi scans skill locations at startup, reads each skill's `name` + `description`, and lists the available skills in its system prompt. When a task matches, pi loads the full `SKILL.md` on demand (progressive disclosure) — the skill body stays out of context until it's needed.

### 2. Automatic Skill Invocation

pi maps each request to the appropriate skill and follows it. You do **not** invoke skills by name:

- "build a feature" → `incremental-implementation` + `test-driven-development`
- "design a system" → `spec-driven-development`
- "fix a bug" → `debugging-and-error-recovery`
- "review this code" → `code-review-and-quality`

### 3. Lifecycle Mapping (Implicit Commands)

neo's slash commands don't exist in pi; the lifecycle is expressed through skills instead:

- INGEST → `markitdown`
- DEFINE → `spec-driven-development`
- PLAN → `planning-and-task-breakdown`
- BUILD → `incremental-implementation` + `test-driven-development`
- VERIFY → `debugging-and-error-recovery`
- REVIEW → `code-review-and-quality`
- SHIP → `shipping-and-launch`

---

## Load neo at session start (no SessionStart hook)

Claude Code auto-loads the `using-neo` meta-skill through its `SessionStart` hook. pi has no hook system, but it reads `AGENTS.md` (or `CLAUDE.md`) as always-on context, so add the rule below to either file so neo drives the flow instead of relying on ad-hoc discovery:

> At the start of every session, before acting on any task, **load the neo meta-skill `skills/using-neo/SKILL.md`** and keep it in context for the whole session. Route every task through its **Skill Discovery** flowchart: identify the phase, then load and follow the matching `skills/<name>/SKILL.md` exactly — if a skill applies at all, it runs first; never jump straight to implementation. Obey the meta-skill's **Core Operating Behaviors** at all times. This rule is non-negotiable and persists past the first message.

Because no hook enforces it, this depends on model compliance — weaker than Claude Code's hook, but the closest hook-free equivalent.

---

## Limitations

pi packages support only skills, prompts, extensions, and themes — so some neo surfaces don't carry over:

- **No native slash commands** — `/spec`, `/plan`, etc. are replaced by intent-driven skill selection.
- **No agent personas** — neo's `agents/` (code-reviewer, security-auditor, …) aren't installed as pi subagents; the equivalent review skills still apply.
- **No lifecycle hooks** — neo's `hooks/` are Claude Code-specific and don't run in pi. See *Load neo at session start* above for the instruction-based replacement (add the rule to `AGENTS.md` / `CLAUDE.md`).
- Skill invocation depends on model compliance, as with any agent-driven setup.

---

## Recommended Workflow

Just describe what you want in natural language:

- "Design a feature"
- "Plan this change"
- "Implement this"
- "Fix this bug"
- "Review this"

pi selects and runs the matching neo skill automatically.

---

## Summary

neo integrates with pi as a package:

- neo skills load unchanged (shared `SKILL.md` format)
- install via `pi install git:…` / local path, or use the bundled `.pi/skills` symlink
- an agent-driven workflow replaces slash commands, closely matching the OpenCode experience
