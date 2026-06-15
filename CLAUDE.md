# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A **Claude Code plugin** (`neo-dev-toolkit`) — not an application. There is no compile/test/lint pipeline. The "code" is Markdown skill definitions and a SessionStart hook script. Distribution is via Claude Code's plugin marketplace mechanism.

## Repo layout (the parts that matter)

```
.claude-plugin/
  plugin.json         # plugin manifest — bump `version` when publishing
  marketplace.json    # local-dev marketplace pointing at "./"
hooks/
  hooks.json          # registers SessionStart hook
  run-hook.cmd        # cross-platform polyglot wrapper (cmd.exe + bash)
  session-start       # bash script that emits skill-overview context as JSON
skills/<name>/
  SKILL.md            # frontmatter + body; the `description` field is what
                      # Claude matches against to decide when to trigger
  references/*.md     # role specs / templates pulled in by the skill body
```

Skills currently bundled: `neo`, `brainstorm`, `improve`, `openapi-doc`, `open-collection`, `confluence-api-doc`, `gitlab`, `commit`, `atlassian`. The README's table is the authoritative list of triggers. (The **API-doc family is single-source**: **Go is the single source of truth** → `openapi-doc` reads the Go source and emits an OpenAPI 3.2 split spec in `bruno/openapi/` (root `openapi.yaml` + `paths/` + `components/schemas/`; business logic in `x-business-logic`, per-sentinel errors in `x-error-catalog`), verifying its output against Go. The two downstream skills *derive* from that spec — `open-collection` (a runnable Bruno OpenCollection; imports the spec via `bru import openapi`) and `confluence-api-doc` (Confluence pages; reconstructs pages from the spec incl. the `x-*` extensions). Each of the three carries its own **three-layer verify** (L1 script · L2 fresh-eyes · L3 completeness sweep). History: consolidated into one `api-doc` gen+publish skill in 0.8.0, re-split md-hub in 0.15.0, then `openapi-doc` added + downstream made dual-source in 0.18.0, then the Markdown `api-doc` skill **removed** and the chain made **spec-only** in 0.19.0; the `bruno` hand-authoring skill was removed in 0.9.0; `atlassian` — the `acli` Jira/Confluence reference + direct-ops skill, and the acli source `neo`'s BA already points to (`skills/neo/references/shared/jira-ref.md §7`) — was added in 0.10.0 as a lean "thin shell over `acli --help`" rework of the user-global skill.)

## How the pieces wire together

- **`SessionStart` hook** (`hooks/hooks.json` → `run-hook.cmd session-start`) runs on `startup | clear | compact` and injects an `<EXTREMELY_IMPORTANT>` block listing every skill and its triggers. This is what makes Claude reach for the skills proactively without the user naming them.
- **`run-hook.cmd`** is a deliberate polyglot file — cmd.exe reads the `@echo off` batch portion (which finds Git-Bash and re-execs the script), while bash treats the leading `:` as a no-op and falls through to the Unix branch. Hook scripts are intentionally **extensionless** (`session-start`, not `session-start.sh`) because Claude Code's Windows auto-detection prepends `bash` to anything ending in `.sh`, which breaks the wrapper.
- **`/neo`** invokes the `neo` skill directly — skill invocation, no command shim (the skill's `description` is the trigger contract).
- **`neo`** is the heaviest skill — a strict **phase-based orchestrator**. `SKILL.md` (~100 lines) declares `tools: [Agent, Read, Skill]` and forbids `Edit`/`Write`/`Bash`. All real work goes through specialist sub-agents (`subagent_type: "general-purpose"`) dispatched via `Agent` using **point-to-read**: the orchestrator passes `NEO_DIR` + artifact paths, and each specialist reads its own role spec from `skills/neo/references/roles/<role>.md` — the orchestrator never pastes role specs into the prompt. The previous v2.6 (`neo-team`) is kept **dormant** in `legacy/neo-team/` (outside `skills/`, so not auto-discovered) as a reference/fallback. For **JIRA-card work**, `neo` persists a resumable per-card task-file (`docs/tasks/<card-id>/plan.md`, markdown) — a `Build` progress axis (`pending`/`in-progress`/`done`) kept orthogonal to the AC `Status` (readiness, which stays `Ready`/`Blocked` only), plus a `## Build Plan` developer work-breakdown (buildable work organized by code-change/surface in build order, absorbing the former sub-task + shared-prereq lanes; 0.12.0) — gated mandatory before Build and read back to resume across sessions; BA is its sole writer (added 0.11.0; `skills/neo/references/shared/task-tracking.md` + `templates/task-file-template.md`). Beyond card work, **`neo` also ingests external knowledge** (JIRA / Confluence / image / html / text / verbal) once into `docs/knowledge/` via a new **Librarian** role (its sole writer) — curated by topic with portable provenance, read context-only by downstream roles (AC stays binding), with an ingest-first guard ensuring a source is ingested before a phase needs it (added 0.13.0; `skills/neo/references/shared/knowledge-base.md` + `roles/librarian.md`). Digest fidelity is gated (0.14.0): the Librarian self-checks that every source clause maps to the digest (KB4) and a second Librarian independently re-checks it at ingest (KB5) — the "Ingest Loop", mirroring the Dev Loop.

## Working in this repo

### Editing skills

- `SKILL.md` frontmatter `description` is **the trigger contract** — Claude uses it (not the body) to decide whether to invoke a skill. Edits to the description change activation behavior; edits to the body change what happens *after* activation. Keep both in sync.
- When adding a new skill, also update: the SessionStart hook (`hooks/session-start`) so its overview block lists the new skill, and the README table.
- `neo` references (`skills/neo/references/`) are **read by the specialist sub-agent** (point-to-read), not pasted by the orchestrator: `roles/<role>.md` (distilled role capsules), `shared/preamble.md` (universal agent header — never-guess / cleanup / status / HTML-verify), `templates/` (artifact content specs), `html-output.md` (HTML form), `phase-map.md` (task→phase routing). Changing a role's contract here changes specialist behavior.
- **`neo` has its own scoped `skills/neo/CLAUDE.md`** — the load-bearing invariants for editing it (gate inventory + count, point-to-read / `NEO_DIR` handoff, HTML asset coupling, the language-neutral rule, add-a-role sync list, verify-before-commit). It's a maintainer doc (not loaded at runtime, not shipped to consumers). Read it before non-trivial neo edits; keep neo detail there, not duplicated here.

### Before every commit (release workflow)

When the user asks to **bump the version, commit, or cut a release**, run this standing flow (the version bump is a hard rule — never commit with it unchanged):

1. **Bump `version`** in `.claude-plugin/plugin.json` AND `.claude-plugin/marketplace.json` (keep both in sync). Semver by change type: patch = fix/docs, minor = new feature/skill, major = breaking. It's the only signal installed clients have that the plugin changed; local marketplaces don't auto-update (see "Publishing" below), so a stale version means users keep running old code.
2. **Tag the release** — one annotated tag per version bump, created *after* the commit lands: `git tag -a v<version> -m "neo-dev-toolkit <version> — <headline>"` (v-prefix). Push it alongside the branch when the user pushes (`git push origin <branch> && git push origin v<version>`).
3. **Publish a GitHub release** — this is the changelog home (there is no `RELEASE.md`). Once the tag is on `origin`, create a release against it with structured notes you write from the diff: a `### <headline>` line, then **Added** / **Changed** / **Removed** / **Notes** sections (same shape as the existing releases). `gh release create v<version> --title "v<version> — <headline>" --notes-file <tmp.md> --latest` — the newest release gets `--latest`; backfilling an older one uses `--latest=false`. Match the format of prior releases (`gh release list` / `gh release view v<x.y.z>` to check).

The user runs `git commit` themselves — don't auto-commit. Do step 1 in the same turn as the request; provide (or run, once they've committed) the step-2 tag command and the step-3 `gh release create`.

### Publishing changes (local marketplace)

Local-path marketplaces have auto-update **off**. After committing a change you must refresh the marketplace listing and reinstall — `git pull` inside the marketplace dir is not enough:

```
/plugin marketplace update neo
/plugin uninstall neo-dev-toolkit@neo
/plugin install   neo-dev-toolkit@neo
```

(Version bump is a hard rule before commit — see "Before every commit" above.)

### Hook script conventions

- Keep hook scripts extensionless (see polyglot note above).
- `session-start` writes its output as a single JSON object on stdout matching Claude Code's hook-output schema (`hookSpecificOutput.hookEventName` + `additionalContext`). The `escape_for_json` bash function in the script handles backslash/quote/newline escaping — reuse it rather than introducing `jq` as a runtime dependency (hooks must work on a fresh machine).

## What this repo intentionally does NOT have

- No build system, no test runner, no linter. Don't introduce one unless asked.
- No application source code. Treat `.md` files as the deliverable.
- No CI. Validation is "does the plugin install and do its skills fire" — done manually in a Claude Code session.
