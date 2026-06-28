# neo-dev-toolkit

Opinionated Claude Code plugin: **`neo`** is a thin loop wrapper over the `using-agent-skills` SDLC (turn a task into a recursive goal, iterate it against a project-specific exit condition until "done" is proven, hand off at a human gate — concept from Addy Osmani's *loop engineering*), backed by an `ingest` memory primitive, GitLab/Atlassian connectors, API-doc tooling, and Go service scaffolding/migration — plus the upstream **[agent-skills](https://github.com/addyosmani/agent-skills)** lifecycle bundle (24 spec→ship engineering skills, 4 specialist agents, 8 slash commands) that `using-agent-skills` routes.

## What's inside

| Skill | Purpose | Triggers on |
|-------|---------|-------------|
| **`neo`** | A THIN loop wrapper over `using-agent-skills`. Turns a task into a recursive goal and iterates it against a project-specific exit condition (authored by the Business Analyst) until "done" is proven — delegating the ENTIRE SDLC (discovery, lifecycle order, 6 Core Operating Behaviors, verification methodology) to `using-agent-skills`. neo owns only four things: the loop, project memory (`docs/tasks/<slug>/STATE.md` + `docs/knowledge/`), the exit condition, and a human gate at commit/PR. Two roles only: Business Analyst (exit-condition framer) + Librarian (memory primitive). Loop concept from Addy Osmani's *loop engineering*. Resume with `/neo continue <slug>`. | "/neo", "neo", a JIRA card id/URL, a GitLab MR URL, or any task that benefits from a recursive-goal loop with durable memory + a human gate; "continue <slug>" to resume |
| **`ingest`** | Standalone memory primitive: ingest an external source (JIRA card, Confluence page, URL, image, HTML, text, verbal) ONCE into `docs/knowledge/<topic>.md` as curated, reusable context with provenance (source url, fetched_at, version/etag). Pre-warm the KB directly, or neo's Librarian triggers it during the ingest-first gate. Maintains `docs/knowledge/INDEX.md`. | "/ingest", "ingest <source>", "remember this", "add <url> to the knowledge base" |
| **`api-spec`** | **Author** the custom-YAML **API spec** at `docs/api/*.yaml` — the spec-first **source of truth** for every endpoint and the head of the api-doc chain. Create / update / validate `_meta.yaml` + one `<domain>/<endpoint>.yaml` per endpoint (method/path/auth, field tables with **M/O** + Remark, multi-flow `business_logic`, `errors`, optional `covers_ac`). **Not OpenAPI.** Three-layer verify (`apispeccheck.py` + fresh-eyes + completeness). The **producer**; the three skills below are read-only consumers. | "author api spec", "create the api contract", "gen api spec", "สร้าง api spec", "เขียน docs/api", "update api spec", "validate api spec" |
| **`openapi-doc`** | Scan Go handler/router/usecase source and **diff it against** the `docs/api/*.yaml` api-spec (the `api-spec`-authored source of truth) → a **drift report**: added/removed routes, request/response field presence, M/O, and type mismatches. The sync-back detector for when code and spec diverge. **Writes nothing** (report-only). Three-layer verify. | "check go against api-spec", "api drift report", "เช็ค code ตรงกับ api-spec ไหม", "หา drift api", "sync-back api", "verify code against the api-spec" |
| **`open-collection`** | Generate a **runnable, self-documenting** Bruno OpenCollection *from* the `docs/api/*.yaml` api-spec — asks the **source mode** up front: **Spec** (one request per endpoint, each carrying a generated `docs:` rendered from the spec) or **AC-scenario** (one request per Ready AC with `runtime.assertions`, joining the spec with neo's `docs/design/<usecase>/`). Update or validate too. Three-layer verify. | "gen open collection", "สร้าง open collection", "สร้าง bruno จาก api spec", "bruno from the api spec", "gen scenario collection", "สร้าง bruno ตาม AC" |
| **`confluence-api-doc`** | Publish API docs to Confluence — from the `docs/api/*.yaml` api-spec (assembles each page directly from the endpoint's doc-table shape) — one endpoint = one page under domain parents, via `acli` + REST. Three-layer verify (pre-flight + round-trip + fresh-eyes + completeness). | "publish api doc", "sync api doc", "push doc to confluence", "publish api spec to confluence", "อัปเดต api doc ไป confluence" |
| **`gitlab`** | Low-level GitLab `glab` execution arm — neo invokes it for MR create + review-comment posting; also usable directly for read/summarize, update description, list MRs, CI status/logs, approve. (Create / review / fix / feedback now route through `neo`.) | Bare MR URL, "อ่าน MR", "อัพเดท MR", "list MRs", "check pipeline" |
| **`atlassian`** | Drive Jira + Confluence from the terminal via the `acli` CLI — view/search/create/edit/transition/assign work items, manage sprints/boards/projects, read pages + manage spaces. A thin shell over `acli --help` that carries the command map + JQL/workflow/safety judgment; also the acli reference `neo` points to. (Verifying a JIRA card in a dev workflow → `neo`; publishing API docs to Confluence → `confluence-api-doc`.) | "ดู issue ของฉัน", "view my issues", "transition ไป In Progress", "search ด้วย JQL", "ดู Confluence page", any raw acli op |
| **`init-project`** | Scaffold a brand-new **Go hexagonal/DDD microservice** from a bundled frozen template — an empty-but-runnable snapshot of the account-service architecture (clean layers + tooling + infra wiring + `.kiro/` steering + CLAUDE.md), **zero business domains**. Builds + serves `GET /health` immediately, ready for `neo` to add the first domain with no setup. Asks the service identity, runs `scaffold.py` (copy template + substitute sentinels + tidy + build), then verifies (L1 `initcheck.py` + L2 fresh-eyes). (Adding domains / AC / endpoints → `neo`.) | "init project", "/init-project", "scaffold a service", "new service from template", "project boilerplate", "สร้าง project ใหม่", "สร้าง service ใหม่", "โครง service เปล่า" |
| **`migrate-project`** | Refactor an **existing** Go service so its structure conforms to the account-service hexagonal/DDD blueprint — the **brownfield sibling of `init-project`**. Reuses init-project's frozen template + `.kiro/steering/` as the target-structure contract, plans the migration as ordered, independently-verifiable **slices** (one bounded context at a time), executes them on a branch with `git mv` (history- + behavior-preserving), and verifies each slice (go build + test + vet + golangci). Plan-first (approve the slice plan before any code moves) + resumable via `docs/migration/plan.md`. Three-layer verify (L1 `structurecheck.py` + L2 fresh-eyes + L3 completeness). (Empty/new service → `init-project`; adding a domain/AC/endpoint → `neo`.) | "migrate project", "/migrate-project", "migrate structure to account-service", "refactor to hexagonal/clean architecture", "restructure an existing service", "ย้ายโครงสร้างโปรเจกต์", "refactor ให้เหมือน account-service", "จัดโครงสร้างใหม่ตาม account-service" |

## agent-skills lifecycle bundle (spec → ship)

Ported from upstream [`agent-skills` 0.6.2](https://github.com/addyosmani/agent-skills/releases/tag/0.6.2). Twenty-four general engineering-workflow skills organized by development phase, routed by the **`using-agent-skills`** meta-skill. Where the neo skills own *your* project-specific workflows (Jira/Confluence, GitLab MR, api-spec, Go scaffolding), these own *general* engineering practice.

| Phase | Skills |
|-------|--------|
| Discover / ideate | `interview-me`, `idea-refine` *(replaces the old `brainstorm`)* |
| Spec & plan | `spec-driven-development`, `planning-and-task-breakdown`, `context-engineering` |
| Implement | `incremental-implementation`, `frontend-ui-engineering`, `api-and-interface-design`, `source-driven-development`, `doubt-driven-development` |
| Test & debug | `test-driven-development`, `browser-testing-with-devtools`, `debugging-and-error-recovery` |
| Review & harden | `code-review-and-quality`, `code-simplification` *(replaces the old `improve`)*, `security-and-hardening`, `performance-optimization` |
| Ship & sustain | `git-workflow-and-versioning`, `ci-cd-and-automation`, `deprecation-and-migration`, `documentation-and-adrs`, `observability-and-instrumentation`, `shipping-and-launch` |

**Specialist agents** (use via the Agent tool): `code-reviewer`, `security-auditor`, `test-engineer`, `web-performance-auditor`.

**Slash commands:** `/spec`, `/plan`, `/build`, `/test`, `/review`, `/ship`, `/code-simplify`, `/webperf`.

**Shared references** the skills cite live under [`references/`](references/) (security / performance / testing / accessibility / orchestration checklists).

### Optional opt-in hooks (not registered by default)

Two utility hooks ship under `hooks/` but are **off by default** (they're project-scoped and have heavy side effects, so upstream leaves them opt-in):

- **`sdd-cache`** — cross-session doc-fetch cache for `source-driven-development` (revalidates via `ETag`/`Last-Modified`, serves only on `304`). Register `PreToolUse`/`PostToolUse` on `WebFetch` → see [`hooks/SDD-CACHE.md`](hooks/SDD-CACHE.md).
- **`simplify-ignore`** — block-level protection for `code-simplify` (`/* simplify-ignore-start */`). Register on `Read`/`Edit|Write`/`Stop` → see [`hooks/SIMPLIFY-IGNORE.md`](hooks/SIMPLIFY-IGNORE.md).

Both expect `jq`; reference the scripts at `${CLAUDE_PLUGIN_ROOT}/hooks/...` since they ship inside this plugin. Add the snippets from their docs to your project's `.claude/settings.local.json` to enable.

## Companion pieces

- `/neo <task>` — invokes the `neo` loop skill directly
- Slash commands `/spec` `/plan` `/build` `/test` `/review` `/ship` `/code-simplify` `/webperf` — entry points into the agent-skills lifecycle bundle
- `using-agent-skills` meta-skill — the discovery router for the 24 lifecycle skills
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
2. **Slash command** — `/neo <task description>` runs the full loop
3. **Direct ask** — "ช่วย review MR นี้...", "gen api doc ให้หน่อย", "idea-refine วิธีออกแบบ...", "spec-driven this feature"

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
│   ├── neo/                 # thin loop wrapper over using-agent-skills (loop engineering)
│   ├── ingest/             # standalone memory primitive (/ingest <url> → docs/knowledge/)
│   ├── api-spec/            # AUTHOR docs/api/*.yaml api-spec (producer — head of the api-doc chain)
│   ├── openapi-doc/         # Go ↔ docs/api/*.yaml api-spec drift checker (report-only; sync-back)
│   ├── open-collection/     # docs/api/*.yaml api-spec → runnable self-documenting Bruno collection
│   ├── confluence-api-doc/  # docs/api/*.yaml api-spec → Confluence pages
│   ├── gitlab/              # glab execution arm (connector — used at neo's human gate)
│   ├── atlassian/           # acli reference + Jira/Confluence CLI ops (connector)
│   ├── init-project/        # scaffold a new Go hexagonal/DDD service from a frozen template
│   ├── migrate-project/     # refactor an existing Go service onto the hexagonal blueprint
│   └── <agent-skills bundle>/  # 24 spec→ship engineering skills (see agent-skills section above)
├── agents/                  # 4 specialist agents: code-reviewer, security-auditor, test-engineer, web-performance-auditor
├── .claude/commands/        # 8 slash commands: spec/plan/build/test/review/ship/code-simplify/webperf
├── references/              # shared checklists cited by the lifecycle skills
├── scripts/                 # validate-skills.js (maintainer validator)
├── docs/                    # skill-anatomy.md
├── legacy/
│   ├── neo-team/            # dormant v2.6 backup (not auto-discovered)
│   └── neo-v3/              # pre-3.0.0 phase-gated neo (retired; reference/fallback only)
├── LICENSE
└── README.md
```

## Author

Witoo Harianto · <witoo@plimble.com>

## License

MIT
