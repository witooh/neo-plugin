# neo-dev-toolkit

Opinionated Claude Code plugin that bundles seven composable skills for end-to-end software development — from idea to merged MR.

## What's inside

| Skill | Purpose | Triggers on |
|-------|---------|-------------|
| **`neo-team`** | Orchestrate a specialist agent team (BA, Architect, Developer, QA, Code Reviewer, Security, System Analyzer) across preset workflows (New Feature, Bug Fix, PR Review, Refactoring, Requirement Clarification, Review Loop). | Any multi-concern dev request, or explicit `/neo` |
| **`brainstorm`** | Turn vague requests into actionable outputs via adaptive guided questioning. Prompt / Explore / Focused modes. | "brainstorm", "ช่วยคิด", "I have an idea", "let's explore" |
| **`improve`** | Iteratively refine any output (code, prose, data, config) until measurable criteria are met. | "improve this", "make it better", "ปรับปรุง", "iterate" |
| **`api-doc-gen`** | Scan handler/router source to produce structured Markdown API docs in `docs/api/`, or validate existing docs against the code. | "gen api doc", "สร้าง api doc", "api doc outdated" |
| **`confluence-api-doc`** | Sync the multi-file `docs/api/` structure to Confluence pages via `acli` + REST. | "sync api doc", "push doc to confluence" |
| **`gitlab`** | Drive GitLab via the `glab` CLI — create, update, read, review, fix, CI-fix, and feedback workflows for MRs. | Any MR URL, "สร้าง MR", "review MR", "fix CI" |
| **`commit`** | Smart git commit workflow — protected-branch guard, auto `feature/*` branching, rebase onto base, secret-aware staging, conventional commit messages, optional push. | "commit", "/commit", "commit and push", "ช่วย commit", "เสร็จแล้ว" |

## Companion pieces

- `/neo <task>` — slash command that explicitly invokes the `neo-team` orchestrator
- `SessionStart` hook — injects a short reminder on `startup | clear | compact` so Claude proactively picks the right skill

## Installation

**Local (development):**

```bash
# From inside Claude Code
/plugin marketplace add /Users/witoo.h/dev/witooh/neo-plugin
/plugin install neo-dev-toolkit@neo-dev-toolkit-dev
```

**After publishing to a git remote:**

```bash
/plugin marketplace add <your-org>/<your-repo>
/plugin install neo-dev-toolkit@neo-dev-toolkit-dev
```

**Update (local marketplace):**

Local-path marketplaces have auto-update off, so pulling new changes in the repo is not enough — you must refresh the marketplace listing and reinstall:

```bash
# 1. Make sure your repo is on the commit you want to ship
cd /path/to/neo-plugin
git status   # should be clean

# 2. Refresh the marketplace listing
/plugin marketplace update neo-dev-toolkit-dev

# 3. Reinstall the plugin so the new version is loaded
/plugin uninstall neo-dev-toolkit@neo-dev-toolkit-dev
/plugin install neo-dev-toolkit@neo-dev-toolkit-dev
```

Open a fresh Claude Code session to confirm the updated skills are active.

## Usage

Three ways to kick off work:

1. **Automatic** — the SessionStart hook tells Claude which skill to reach for; just describe the task naturally
2. **Slash command** — `/neo <task description>` runs the full orchestrator
3. **Direct ask** — "ช่วย review MR นี้...", "gen api doc ให้หน่อย", "brainstorm วิธีออกแบบ..."

## Structure

```
.
├── .claude-plugin/
│   ├── plugin.json          # plugin manifest
│   └── marketplace.json     # dev marketplace for local install
├── commands/
│   └── neo.md               # /neo slash command → invokes neo-team skill
├── hooks/
│   ├── hooks.json           # SessionStart registration
│   ├── session-start        # bash script that injects skill overview
│   └── run-hook.cmd         # cross-platform polyglot wrapper
├── skills/
│   ├── neo-team/            # orchestrator (BA → Architect → Dev → QA → Review)
│   ├── brainstorm/          # guided ideation
│   ├── improve/             # iterative refinement
│   ├── api-doc-gen/         # generate API docs from code
│   ├── confluence-api-doc/  # sync docs/api/ to Confluence
│   ├── gitlab/              # glab-backed MR workflows
│   └── commit/              # smart git commit workflow
├── LICENSE
└── README.md
```

## Author

Witoo Harianto · witoo@plimble.com

## License

MIT
