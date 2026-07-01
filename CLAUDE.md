# neo

This is the neo project — a collection of production-grade engineering skills for AI coding agents.

## Project Structure

```
skills/       → Core skills (SKILL.md per directory)
agents/       → Reusable agent personas (code-reviewer, test-engineer, security-auditor, web-performance-auditor)
hooks/        → Session lifecycle hooks
.claude/commands/ → Slash commands (/ingest, /spec, /plan, /build, /commit, /test, /review, /code-simplify, /ship; plus /webperf specialist audit)
references/   → Supplementary checklists (testing, performance, security, accessibility, observability)
docs/         → Setup guides for different tools
```

## Skills by Phase

**Ingest:** markitdown
**Define:** interview-me, idea-refine, spec-driven-development, api-spec
**Plan:** planning-and-task-breakdown
**Build:** incremental-implementation, test-driven-development, context-engineering, source-driven-development, doubt-driven-development, frontend-ui-engineering, api-and-interface-design
**Verify:** browser-testing-with-devtools, debugging-and-error-recovery, e2e-playwright
**Review:** code-review-and-quality, code-simplification, security-and-hardening, performance-optimization
**Ship:** git-workflow-and-versioning, ci-cd-and-automation, deprecation-and-migration, documentation-and-adrs, observability-and-instrumentation, shipping-and-launch, open-collection, confluence-api-doc, openapi-doc

> `api-spec` spans two phases — **Define** drafts the `docs/api/` contract spec-first (via `/spec`), **Ship** reconciles it from the built code via Update-from-code (via `/ship`). The api-doc chain's **consumers** cluster at **Ship**: `open-collection` (runnable Bruno collection) and `confluence-api-doc` (Confluence publish) fold into `/ship`; `openapi-doc` (read-only Go↔spec drift report) stays discoverable on demand.

## Conventions

- Every skill lives in `skills/<name>/SKILL.md`
- YAML frontmatter with `name` and `description` fields
- Description starts with what the skill does (third person), followed by trigger conditions ("Use when...")
- Every skill has: Overview, When to Use, Process, Common Rationalizations, Red Flags, Verification
- References are in `references/`, not inside skill directories
- Supporting files only created when content exceeds 100 lines

## Upstream vs neo-owned (keep upstream syncs clean)

This repo is a rebranded fork of `addyosmani/agent-skills`; the `sync-upstream` skill pulls upstream updates. To keep future upgrades painless, **never hand-edit a file the sync treats as upstream-owned** — a hand-edit that collides with an upstream change becomes a merge CONFLICT on the next sync.

- **Upstream-owned — do NOT edit.** Two groups: (a) the skills listed under `synced_skills` in `.claude/skills/sync-upstream/sync-state.json` (the vendored agent-skills lifecycle skills); and (b) **everything in `hooks/`, `agents/`, and `references/`** — those three dirs are 100% upstream (neo has added no files of its own to them). The **only** exception is `using-neo` — neo's customized fork of `using-agent-skills`, deliberately carved out of the sync. Hand-editing any of these collides with the next upstream sync = merge CONFLICT. (If you ever add a *new* neo-specific hook/agent/reference, the sync auto-classifies it neo-local since it is absent from upstream.)
- **neo-local skills — edit freely.** Anything NOT in `synced_skills`: `api-spec` and the api-doc chain (`openapi-doc`, `open-collection`, `confluence-api-doc`), `init-project`, `migrate-project`, `atlassian`, `gitlab`, `e2e-playwright`, `markitdown`. The sync never touches these.
- **To change upstream behavior, use a neo-owned file** — a slash command (`.claude/commands/`), `docs/`, `README.md`, `CLAUDE.md`, or a neo-local skill — never the upstream skill file. (This is why the api-spec wiring for `/spec` and `/ship` lives in the command files, not in `spec-driven-development` / `shipping-and-launch`.)

## Contributing

Before adding a new skill or significantly reworking an existing one, run the pre-flight checks in [CONTRIBUTING.md](CONTRIBUTING.md#before-proposing-a-new-skill): search the catalog, check open PRs, confirm the idea fits [docs/skill-anatomy.md](docs/skill-anatomy.md), and justify the gap. Prefer extending an existing skill over adding a near-duplicate. CONTRIBUTING.md is the single source of truth for this workflow; do not restate its checklist here or elsewhere, link to it.

## Commands

- `npm test` — Not applicable (this is a documentation project)
- Validate: Check that all SKILL.md files have valid YAML frontmatter with name and description

## Versioning and releases

When the user asks to **bump the version, commit, or cut a release**, run this standing flow (the version bump is a hard rule — never cut a release with it unchanged):

1. **Bump `version`** in `.claude-plugin/plugin.json` — the plugin manifest is the single source of truth for the version (`marketplace.json` carries no version field). Semver by change type: patch = fix/docs, minor = new skill/feature, major = breaking. It's the only signal installed clients have that the plugin changed, so a stale version means users keep running old code.
2. **Tag the release** — one annotated tag per version bump, created *after* the commit lands: `git tag -a v<version> -m "neo <version> — <headline>"` (v-prefix). Push it alongside the branch when the user pushes: `git push origin <branch> && git push origin v<version>`.
3. **Publish a GitHub release** — this is the changelog home (there is no `RELEASE.md`). Once the tag is on `origin`, create a release against it with structured notes you write from the diff: a `### <headline>` line, then **Added** / **Changed** / **Removed** / **Notes** sections (match the shape of prior releases). `gh release create v<version> --title "v<version> — <headline>" --notes-file <tmp.md> --latest` — the newest release gets `--latest`; backfilling an older one uses `--latest=false`. Check prior format first with `gh release list` / `gh release view v<x.y.z>`.

The user runs `git commit` themselves — don't auto-commit. Do step 1 in the same turn as the request; provide (or run, once they've committed) the step-2 tag command and the step-3 `gh release create`.

## Pull Requests

PRs target the upstream repository's default branch. In a typical fork setup the upstream remote is `upstream` and your fork is `origin`, but the exact remote names are not what matters here.

- Before opening a PR, search the upstream repository's open PRs and issues for work that touches the same files or rules. If any overlaps, coordinate (build on it, align your rules with it, or rebase after it merges) instead of opening a conflicting PR.
- Prefer small, focused PRs over large refactors of widely shared files (for example, files under `scripts/`), which are more likely to collide with in-flight work.

## Boundaries

- Always: Run the CONTRIBUTING.md pre-flight checks before creating a new skill directory
- Always: Follow the skill-anatomy.md format for new skills
- Always: Check the upstream repo's open PRs and issues for overlap before opening a new PR
- Never: Add skills that are vague advice instead of actionable processes
- Never: Duplicate content between skills — reference other skills instead
- Never: Hand-edit an upstream-synced skill (`synced_skills` in `.claude/skills/sync-upstream/sync-state.json`) or the other in-scope dirs (`hooks/`, `agents/`, `references/`) — it breaks clean upstream upgrades. Sole exception: `using-neo`. See "Upstream vs neo-owned".
