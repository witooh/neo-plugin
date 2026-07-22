# Using neo with pi

This guide explains how to use neo with [pi](https://pi.dev) — a minimal, extensible AI coding-agent CLI. neo ships as a **pi package**: its skills load directly, and a package extension injects the `using-neo` router into every session.

## Overview

pi is skill-first and aggressively extensible: capabilities are packaged as skills, prompts, extensions, and themes, and installed from npm, git, or a local path. neo's `skills/<name>/SKILL.md` files already match pi's skill format (`name` + `description` frontmatter), so every neo skill loads in pi with no conversion.

pi exposes lifecycle events through extensions. neo uses `session_start` to load its router context and `before_agent_start` to append that context before each agent run; method skills are then selected automatically from intent.

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

pi auto-discovers project resources from `.pi/`. The neo repo includes `.pi/skills` and `.pi/extensions` symlinks to its package resources, so opening neo itself in pi loads both the skills and the session-start extension with no install step.

---

## How It Works

### 1. Skill Discovery

pi scans skill locations at startup, reads each skill's `name` + `description`, and lists the available skills in its system prompt. The extension keeps the complete `using-neo` router in context; other skill bodies load on demand when that router selects them.

### 2. Automatic Skill Invocation

pi maps each request to the appropriate skill and follows it. You do **not** invoke skills by name:

- "build a feature" → `incremental-implementation` + `test-driven-development`
- "design a system" → `spec-driven-development`
- "fix a bug" → `debugging-and-error-recovery`
- "review this code" → `code-review-and-quality`

### 3. Lifecycle Mapping

neo is command-free; `using-neo` routes each request into this lifecycle:

- INGEST → `markitdown`
- DEFINE → `spec-driven-development`
- PLAN → `planning-and-task-breakdown`
- BUILD → `incremental-implementation` + `test-driven-development`
- VERIFY → `debugging-and-error-recovery`
- REVIEW → `code-review-and-quality`
- SHIP → `shipping-and-launch`

---

## Load neo at session start

neo ships `extensions/using-neo-session-start.js`, which mirrors the session-context behavior used by the other harness adapters:

1. `session_start` reads the complete `skills/using-neo/SKILL.md` body and, when present, `.kiro/steering/INDEX.md` from the active project.
2. `before_agent_start` appends that context to pi's existing system prompt before every agent run, so the router remains available after long sessions or compaction.

The package manifest loads the extension for installed copies. The `.pi/extensions` symlink loads the same extension when working directly in this repository. No manual `AGENTS.md` fallback is required.

---

## Limitations

pi packages support only skills, prompts, extensions, and themes — so some neo surfaces don't carry over:

- **No native slash commands** — neo is command-free everywhere; `using-neo` selects workflows from intent and repository state.
- **No agent personas** — neo's `agents/` (code-reviewer, security-auditor, …) aren't installed as pi subagents; the equivalent review skills still apply.
- **Different lifecycle API** — pi does not read the Claude/Codex hook manifests; neo provides the equivalent behavior through its bundled pi extension.
- Method-skill selection remains agent-driven, while the `using-neo` router context itself is injected by the extension.

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
- the bundled extension injects `using-neo` plus optional project steering before every agent run
- install via `pi install git:…` / local path, or use the bundled `.pi/skills` and `.pi/extensions` symlinks
- method skills remain agent-driven behind the single `using-neo` router
