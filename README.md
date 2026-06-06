# neo-dev-toolkit

Opinionated Claude Code plugin that bundles six composable skills for end-to-end software development — from idea to merged MR.

## What's inside

| Skill | Purpose | Triggers on |
|-------|---------|-------------|
| **`neo`** | Route a software-development task to specialist agents (BA, Architect, Developer, QA, Code Reviewer, Security, System Analyzer) via phase-based analysis. No fixed workflow — supports single-role calls (สร้าง AC, gen test cases, review PR, fix bug) and multi-role tasks (เพิ่ม endpoint, refactor). Auto Dev loop (Dev → QA → Code Reviewer). Single entry point for GitLab MR **create** and **review** (with a JIRA card → AC/TC compliance; without → code + security + regression), calling the `gitlab` skill for glab I/O. | Any dev task that touches AC, design, code, tests, API, or security; "สร้าง MR", "review MR"; or explicit `/neo` |
| **`brainstorm`** | Turn vague requests into actionable outputs via adaptive guided questioning. Prompt / Explore / Focused modes. | "brainstorm", "ช่วยคิด", "I have an idea", "let's explore" |
| **`improve`** | Iteratively refine any output (code, prose, data, config) until a measurable finish-line condition holds — autonomous improve → self-evaluate loop modeled on `/goal`. | "improve this", "make it better", "ปรับปรุง", "iterate" |
| **`api-doc`** | Two commands, each with a two-layer verify. **gen**: scan Go handler/router/usecase source → a runnable Bruno OpenCollection workspace (with embedded `docs:`), or validate it against the code. **publish**: sync that collection to Confluence pages via `acli` + REST. (For hand-authoring or curl/Postman conversion, use `bruno`.) | "gen api doc", "สร้าง api doc", "gen open collection", "api doc outdated" → gen; "sync api doc", "push doc to confluence" → publish |
| **`gitlab`** | Low-level GitLab `glab` execution arm — neo invokes it for MR create + review-comment posting; also usable directly for read/summarize, update description, list MRs, CI status/logs, approve. (Create / review / fix / feedback now route through `neo`.) | Bare MR URL, "อ่าน MR", "อัพเดท MR", "list MRs", "check pipeline" |
| **`commit`** | Smart git commit workflow — protected-branch guard, auto `feature/*` branching, rebase onto base, secret-aware staging, conventional commit messages, optional push. | "commit", "/commit", "commit and push", "ช่วย commit", "เสร็จแล้ว" |

## Companion pieces

- `/neo <task>` — invokes the `neo` orchestrator skill directly
- `SessionStart` hook — injects a short reminder on `startup | clear | compact` so Claude proactively picks the right skill

## Installation

Install the plugin straight from this GitHub repo — no local clone needed:

```bash
# From inside Claude Code
/plugin marketplace add witooh/neo-plugin
/plugin install neo-dev-toolkit@neo
```

`witooh/neo-plugin` is the GitHub `owner/repo` shorthand. Claude Code reads `.claude-plugin/marketplace.json` from the default branch and resolves the plugin from there.

If the repo is private or you prefer an explicit URL:

```bash
/plugin marketplace add https://github.com/witooh/neo-plugin.git
/plugin install neo-dev-toolkit@neo
```

### Updating

```bash
# 1. Pull the latest marketplace listing from GitHub
/plugin marketplace update neo

# 2. Reinstall so the new plugin version is loaded
/plugin uninstall neo-dev-toolkit@neo
/plugin install neo-dev-toolkit@neo
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
│   └── marketplace.json     # marketplace listing consumed by Claude Code
├── hooks/
│   ├── hooks.json           # SessionStart registration
│   ├── session-start        # bash script that injects skill overview
│   └── run-hook.cmd         # cross-platform polyglot wrapper
├── skills/
│   ├── neo/                 # phase-based orchestrator → specialist agents
│   ├── brainstorm/          # guided ideation
│   ├── improve/             # iterative refinement
│   ├── api-doc/             # gen OpenCollection from code + publish to Confluence
│   ├── gitlab/              # glab execution arm (invoked by neo)
│   └── commit/              # smart git commit workflow
├── legacy/
│   └── neo-team/            # dormant v2.6 backup (kept for reference, not auto-discovered)
├── LICENSE
└── README.md
```

## Author

Witoo Harianto · witoo@plimble.com

## License

MIT
