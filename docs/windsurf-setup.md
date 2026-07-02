# Using neo with Windsurf

## Setup

### Project Rules

Windsurf uses `.windsurfrules` for project-specific agent instructions:

```bash
# Create a combined rules file from your most important skills
cat /path/to/neo/skills/test-driven-development/SKILL.md > .windsurfrules
echo "\n---\n" >> .windsurfrules
cat /path/to/neo/skills/incremental-implementation/SKILL.md >> .windsurfrules
echo "\n---\n" >> .windsurfrules
cat /path/to/neo/skills/code-review-and-quality/SKILL.md >> .windsurfrules
```

### Global Rules

For skills you want across all projects, add them to Windsurf's global rules:

1. Open Windsurf → Settings → AI → Global Rules
2. Paste the content of your most-used skills

## Load neo at session start (no SessionStart hook)

Claude Code auto-loads the `using-neo` meta-skill through its `SessionStart` hook. Windsurf has no equivalent, so add the rule below to the top of `.windsurfrules` so neo drives the flow instead of the agent improvising:

> At the start of every session, before acting on any task, **load the neo meta-skill `skills/using-neo/SKILL.md`** and keep it in context for the whole session. Route every task through its **Skill Discovery** flowchart: identify the phase, then load and follow the matching `skills/<name>/SKILL.md` exactly — if a skill applies at all, it runs first; never jump straight to implementation. Obey the meta-skill's **Core Operating Behaviors** at all times. This rule is non-negotiable and persists past the first message.

Because no hook enforces it, this depends on model compliance — weaker than Claude Code's hook, but the closest hook-free equivalent.

## Recommended Configuration

Keep `.windsurfrules` focused on 2-3 essential skills to stay within context limits:

```
# .windsurfrules
# Essential neo for this project

[Paste test-driven-development SKILL.md]

---

[Paste incremental-implementation SKILL.md]

---

[Paste code-review-and-quality SKILL.md]
```

## Usage Tips

1. **Be selective** — Windsurf's context is limited. Choose skills that address your biggest quality gaps.
2. **Reference in conversation** — Paste additional skill content into the chat when working on specific phases (e.g., paste `security-and-hardening` when building auth).
3. **Use references as checklists** — Paste `references/security-checklist.md` and ask Windsurf to verify each item.
