# neo-dev-toolkit

Opinionated Claude Code plugin that bundles nine composable skills for end-to-end software development — from idea to merged MR.

## What's inside

| Skill | Purpose | Triggers on |
|-------|---------|-------------|
| **`neo`** | Route a software-development task to specialist agents (BA, Architect, Developer, QA, Code Reviewer, Security, System Analyzer, Librarian) via phase-based analysis. No fixed workflow — supports single-role calls (สร้าง AC, gen test cases, review PR, fix bug) and multi-role tasks (เพิ่ม endpoint, refactor). Auto Dev loop (Dev → QA → Code Reviewer). Single entry point for GitLab MR **create** and **review** (with a JIRA card → AC/TC compliance; without → code + security + regression), calling the `gitlab` skill for glab I/O. For JIRA-card work, persists a resumable task-file (`docs/tasks/<card-id>/plan.md`) + enforces plan+task before coding. Ingests external sources (JIRA / Confluence / image / verbal) once into `docs/knowledge/` (Librarian) for all roles to reuse. | Any dev task that touches AC, design, code, tests, API, or security; "สร้าง MR", "review MR"; "continue ABC-123" to resume a tracked card; "ingest <source>" / "remember this"; or explicit `/neo` |
| **`brainstorm`** | Turn vague requests into actionable outputs via adaptive guided questioning. Prompt / Explore / Focused modes. | "brainstorm", "ช่วยคิด", "I have an idea", "let's explore" |
| **`improve`** | Iteratively refine any output (code, prose, data, config) until a measurable finish-line condition holds — autonomous improve → self-evaluate loop modeled on `/goal`. | "improve this", "make it better", "ปรับปรุง", "iterate" |
| **`openapi-doc`** | Scan Go handler/router/usecase source → an **OpenAPI 3.2** split-YAML spec in `bruno/openapi/` (root `openapi.yaml` + one Path Item per path + one schema per type), or update/validate against the code. Business logic in `x-business-logic`, per-sentinel errors in `x-error-catalog`. Three-layer verify. Reads Go directly — Go is the source of truth. | "gen openapi", "สร้าง openapi spec", "openapi from go", "swagger spec from code", "อัปเดต openapi", "เช็ค openapi ตรงกับ code" |
| **`open-collection`** | Generate a **runnable** Bruno OpenCollection *from* the `bruno/openapi/` spec (runnable-only — URLs/params/body/auth/envs, no `docs:` blocks), or validate it. Three-layer verify. | "gen open collection", "สร้าง open collection", "สร้าง bruno จาก openapi spec", "bruno from openapi", "scaffold opencollection from spec" |
| **`confluence-api-doc`** | Publish API docs to Confluence — from the `bruno/openapi/` spec (reads `x-business-logic`/`x-error-catalog`) — one endpoint = one page under domain parents, via `acli` + REST. Three-layer verify (pre-flight + round-trip + fresh-eyes + completeness). | "publish api doc", "sync api doc", "push doc to confluence", "publish openapi to confluence", "อัปเดต api doc ไป confluence" |
| **`gitlab`** | Low-level GitLab `glab` execution arm — neo invokes it for MR create + review-comment posting; also usable directly for read/summarize, update description, list MRs, CI status/logs, approve. (Create / review / fix / feedback now route through `neo`.) | Bare MR URL, "อ่าน MR", "อัพเดท MR", "list MRs", "check pipeline" |
| **`commit`** | Smart git commit workflow — protected-branch guard, auto `feature/*` branching, rebase onto base, secret-aware staging, conventional commit messages, optional push. | "commit", "/commit", "commit and push", "ช่วย commit", "เสร็จแล้ว" |
| **`atlassian`** | Drive Jira + Confluence from the terminal via the `acli` CLI — view/search/create/edit/transition/assign work items, manage sprints/boards/projects, read pages + manage spaces. A thin shell over `acli --help` that carries the command map + JQL/workflow/safety judgment; also the acli reference `neo` points to. (Verifying a JIRA card in a dev workflow → `neo`; publishing API docs to Confluence → `confluence-api-doc`.) | "ดู issue ของฉัน", "view my issues", "transition ไป In Progress", "search ด้วย JQL", "ดู Confluence page", any raw acli op |

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
│   ├── openapi-doc/         # Go → OpenAPI 3.2 split spec in bruno/openapi/ (source of truth)
│   ├── open-collection/     # bruno/openapi spec → runnable Bruno collection
│   ├── confluence-api-doc/  # bruno/openapi spec → Confluence pages
│   ├── gitlab/              # glab execution arm (invoked by neo)
│   ├── commit/              # smart git commit workflow
│   └── atlassian/           # acli reference + Jira/Confluence CLI ops
├── legacy/
│   └── neo-team/            # dormant v2.6 backup (kept for reference, not auto-discovered)
├── LICENSE
└── README.md
```

## Author

Witoo Harianto · witoo@plimble.com

## License

MIT
