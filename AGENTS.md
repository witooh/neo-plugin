# AGENTS.md

This is the canonical repository guidance for every AI coding harness (Claude Code, Codex, Copilot, Cursor, OpenCode, Antigravity, and others). Harness-specific entry files must import or reference this file instead of duplicating its content; root `CLAUDE.md` imports it with `@AGENTS.md`.

## Repository Overview

neo is a collection of production-grade engineering skills and specialist agent personas covering the software-development lifecycle from ingest through ship.

## Project Structure

```text
skills/        Core skills (`SKILL.md` per directory)
skills/neo/    Lifecycle driver (`neo` / `neo auto`)
skills/neo-*/  Cross-tool phase entry skills
agents/        Reusable specialist personas
hooks/         Claude session lifecycle hooks
references/    Canonical shared checklists
docs/          Tool-specific setup guides
```

## Skill-Driven Execution

### Core Rules

- If a task matches a skill, invoke it before taking task actions.
- Skills live at `skills/<skill-name>/SKILL.md`; read and follow the selected skill completely.
- Use the harness's native skill mechanism; in OpenCode, invoke the selected skill with the `skill` tool.
- Never implement directly when a skill applies, and never partially apply a skill workflow.
- Load only the relevant skill and referenced resources; do not inject the whole catalog into context.

### Intent to Skill Mapping

- External docs or context → `markitdown`
- Feature or new functionality → `spec-driven-development`, then `incremental-implementation` + `test-driven-development`
- HTTP acceptance tests → `e2e-playwright`
- Planning or breakdown → `planning-and-task-breakdown`
- Bug, failure, or unexpected behavior → `debugging-and-error-recovery`
- Code review → `code-review-and-quality`
- Refactoring or simplification → `code-simplification`
- API or interface design → `api-and-interface-design`
- Go implementation vs `docs/api` drift → `openapi-doc`
- Bruno collection from `docs/api` → `open-collection`
- Publish `docs/api` to Confluence → `confluence-api-doc`
- UI work → `frontend-ui-engineering`

### Method Skills by Phase

- **Driver:** `neo`
- **Ingest:** `markitdown`
- **Define:** `interview-me`, `idea-refine`, `spec-driven-development`, `api-spec`
- **Plan:** `planning-and-task-breakdown`
- **Build:** `incremental-implementation`, `test-driven-development`, `context-engineering`, `source-driven-development`, `doubt-driven-development`, `frontend-ui-engineering`, `api-and-interface-design`
- **Verify:** `browser-testing-with-devtools`, `debugging-and-error-recovery`, `e2e-playwright`
- **Review:** `code-review-and-quality`, `code-simplification`, `security-and-hardening`, `performance-optimization`
- **Ship:** `git-workflow-and-versioning`, `ci-cd-and-automation`, `deprecation-and-migration`, `documentation-and-adrs`, `observability-and-instrumentation`, `shipping-and-launch`, `open-collection`, `confluence-api-doc`, `openapi-doc`

### Lifecycle Entry Skills

- DRIVER → `neo` detects and sequences all phases; `neo auto` continues after one approval and stops only at commit, ship, blockers, or high-risk steps.
- INGEST → `neo-ingest` runs `markitdown`.
- DEFINE → `neo-spec` runs `spec-driven-development` and drafts `api-spec` for HTTP features.
- PLAN → `neo-plan` runs `planning-and-task-breakdown`.
- BUILD → `neo-build` runs `incremental-implementation` + `test-driven-development`.
- VERIFY → `neo-test` runs `test-driven-development`, adding `debugging-and-error-recovery` for failures and `e2e-playwright` for HTTP acceptance criteria.
- REVIEW → `neo-review` runs `code-review-and-quality`; `neo-code-simplify` reduces complexity.
- SHIP → `neo-ship` runs `shipping-and-launch`, reconciles API drift, and refreshes `open-collection` / `confluence-api-doc` deliverables.
- SUPPORT → `neo-webperf` audits web performance; `neo-commit` prepares atomic commits.

`api-spec` spans Define and Ship: Define authors the contract; Ship reconciles it from built code. `openapi-doc` remains a read-only drift report.

### Execution Model

For every request:

1. Determine whether any skill applies, even for small tasks.
2. Invoke the appropriate skill and follow its workflow exactly.
3. Complete required spec, plan, test, and review gates before implementation or delivery.
4. Treat thoughts such as “this is too small for a skill,” “I can quickly implement this,” or “I will gather context first” as rationalizations; skill discovery comes first.

## Orchestration

neo has three composable layers:

- **Skills** (`skills/<name>/SKILL.md`) define *how* work is done.
- **Personas** (`agents/<role>.md`) define *who* performs specialist work.
- **Entry skills** (`skills/neo-<phase>/SKILL.md`) define *when* workflows run and orchestrate method skills.

The user or an entry skill is the orchestrator. Personas may invoke skills but must not invoke other personas. The only endorsed multi-persona composition is parallel fan-out with a merge step, used by `neo-ship` for `code-reviewer`, `security-auditor`, and `test-engineer`.

See [docs/agents.md](docs/agents.md) and [references/orchestration-patterns.md](references/orchestration-patterns.md). Claude Code discovers personas in `agents/` as subagents and Agent Teams teammates; plugin agents silently ignore `hooks`, `mcpServers`, and `permissionMode` frontmatter fields.

## Skill Authoring Conventions

- Every skill lives in `skills/<kebab-case-name>/SKILL.md` with `name` and `description` YAML frontmatter.
- Descriptions begin with what the skill does in third person, then state when to use it.
- Standard skills include Overview, When to Use, Process, Common Rationalizations, Red Flags, and Verification.
- Most skills are Markdown-only. Create supporting files only when content exceeds roughly 100 lines; never create per-skill zip packages.
- Top-level `references/` is the source of truth for shared checklists. `scripts/bundle-references.sh` copies them into skills that must be self-contained; never hand-edit generated copies.

Before adding or significantly reworking a skill, follow [CONTRIBUTING.md](CONTRIBUTING.md#before-proposing-a-new-skill): search the catalog and open PRs, confirm the gap against [docs/skill-anatomy.md](docs/skill-anatomy.md), and prefer extending an existing skill.

## Upstream vs neo-Owned Files

The repo is a rebranded fork of `addyosmani/agent-skills`; `sync-upstream` imports upstream changes.

- **Do not edit upstream-owned files:** skills listed in `synced_skills` in `.claude/skills/sync-upstream/sync-state.json`, plus upstream files in `hooks/`, `agents/`, and `references/`. The sole carved-out skill exception is `using-neo`.
- **Edit neo-local files freely:** entry skills under `skills/neo-*`, this `AGENTS.md`, `docs/`, `README.md`, and skills absent from `synced_skills`, including `api-spec`, the API-doc chain, `init-project`, `migrate-project`, `atlassian`, `gitlab`, `e2e-playwright`, and `markitdown`.
- Put neo behavior changes in a neo-owned entry skill or other neo-owned file, never in its upstream method skill.
- New neo-specific files added under an otherwise upstream-owned directory remain neo-local when absent upstream.

## Validation Commands

- Skills: `node scripts/validate-skills.js`
- Agent guidance SOT: `node scripts/validate-agent-guidance.js`
- Copilot plugin: `node scripts/validate-copilot-plugin.js`
- Claude hook: `bash hooks/session-start-test.sh`
- Codex hook: `bash .codex-plugin/hooks/session-start-test.sh`
- Claude plugin structure: `claude plugin validate .`

## Versioning and Releases

When the user asks to bump the version, commit, or cut a release:

1. Bump the canonical `version` in `.claude-plugin/plugin.json` using SemVer: patch for fixes/docs, minor for backward-compatible features or skills, major for breaking changes. Sync that version to `.plugin/plugin.json` and both version fields in `.github/plugin/marketplace.json`; `.claude-plugin/marketplace.json` intentionally has no version field. Follow the Codex packaging flow for its build-suffixed manifest version.
2. After the commit lands, create an annotated tag: `git tag -a v<version> -m "neo <version> — <headline>"`, then push the branch and tag.
3. After the tag reaches `origin`, publish a GitHub release with `gh release create v<version> --title "v<version>" --notes-file <tmp.md> --latest`. Put the headline and Added / Changed / Removed / Notes sections in the body; the title is the version only.

Check prior releases before writing notes. Use `--latest=false` when backfilling an older release. The user runs `git commit`; never auto-commit.

## Pull Requests

- Before opening a PR, search the upstream repository's open PRs and issues for overlapping files or rules and coordinate instead of creating a conflict.
- Target the upstream repository's default branch; remote names may differ (`upstream` and `origin` are conventional, not required).
- Prefer small, focused PRs over broad refactors of shared files.

## Boundaries

- Always run the CONTRIBUTING pre-flight before creating a skill directory.
- Always follow `docs/skill-anatomy.md` and run relevant validators.
- Never add vague advice as a skill; skills must define actionable processes.
- Never duplicate content between skills; reference another skill instead, except for generated bundled references.
- Never hand-edit upstream-synced content or generated per-skill reference copies.
- Never duplicate canonical repository guidance in `CLAUDE.md` or another harness adapter; update this file instead.
