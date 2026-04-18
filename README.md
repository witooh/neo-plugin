# neo-team-claude

Orchestrate a specialized software development agent team inside Claude Code. The plugin ships one skill (`neo-team-claude`), one slash command (`/neo`), and a SessionStart hook that reminds Claude to invoke the orchestrator whenever a task has more than one concern.

## What it does

`neo-team-claude` turns Claude Code into an **Orchestrator** that never implements code itself. Instead it:

1. Reads project context (`CLAUDE.md`, `AGENTS.md`, `docs/design/INDEX.md`)
2. Classifies the user's request into a workflow (New Feature, Bug Fix, PR Review, Refactoring, Requirement Clarification, Review Loop)
3. Delegates each pipeline step to a specialist agent via the `Agent` tool:
   - **Business Analyst** — requirements, acceptance criteria, edge cases
   - **Architect** — system design, API contracts, ADRs
   - **Developer** — implementation, unit tests
   - **QA** — test case docs, E2E test code, execution reports
   - **Code Reviewer** — convention compliance (read-only)
   - **Security** — security review, secrets detection
   - **System Analyzer** — diagnose issues across envs (read-only)
4. Merges outputs, runs the Review Loop, syncs documentation, and returns a single assembled summary

## Installation

### Local (development)

```bash
# From inside Claude Code
/plugin marketplace add /Users/witoo.h/dev/witooh/neo-plugin
/plugin install neo-team-claude@neo-team-claude-dev
```

### After publishing to a git remote

```bash
/plugin marketplace add <your-org>/<your-repo>
/plugin install neo-team-claude@neo-team-claude-dev
```

## Usage

Three ways to trigger the team:

1. **Automatic** — the SessionStart hook tells Claude to invoke the skill whenever a request has multiple concerns
2. **Slash command** — `/neo <task description>` explicitly starts the orchestrator
3. **Ask directly** — "ใช้ neo-team จัดการเคสนี้ให้หน่อย" / "orchestrate the team to add this endpoint"

## Structure

```
.
├── .claude-plugin/
│   ├── plugin.json          # plugin manifest
│   └── marketplace.json     # dev marketplace for local install
├── commands/
│   └── neo.md               # /neo slash command
├── hooks/
│   ├── hooks.json           # SessionStart registration
│   ├── session-start        # bash script that injects context
│   └── run-hook.cmd         # cross-platform polyglot wrapper
├── skills/
│   └── neo-team-claude/
│       ├── SKILL.md         # orchestration rules
│       └── references/      # specialist prompts + workflow templates
├── LICENSE
└── README.md
```

## Author

Witoo Harianto · witoo@plimble.com

## License

MIT
