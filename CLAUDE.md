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

Skills currently bundled: `neo`, `ingest`, `api-spec`, `openapi-doc`, `open-collection`, `confluence-api-doc`, `gitlab`, `atlassian`, `init-project`, `migrate-project` (the neo toolkit), **plus 24 upstream agent-skills lifecycle skills** (added 0.33.0, ported from `addyosmani/agent-skills` 0.6.2 — the old `brainstorm`→`idea-refine` and `improve`→`code-simplification`; routed via the `using-agent-skills` meta-skill, with 4 specialist `agents/` + 8 `.claude/commands/` slash commands; shared checklists under `references/`). The README's table is the authoritative list of triggers. **History note (3.0.0): `neo` was REBUILT from a phase-gated orchestrator (v3, now in `legacy/neo-v3/`) into a thin loop wrapper over `using-agent-skills`** — see below and `skills/neo/CLAUDE.md`. The `commit` skill was dropped (overlaps `git-workflow-and-versioning`). The `ingest` skill was added as the standalone memory primitive. (The **API-doc family is single-source**: the **custom-YAML api-spec at `docs/api/` is the single source of truth** — `_meta.yaml` (service-level: title/version/base_url/overview/field_info/common_errors/domains) + one `<domain>/<endpoint>.yaml` per endpoint (method/path/auth/covers_ac, field tables with M/O + Remark, multi-flow `business_logic`, per-endpoint `errors`). **the `api-spec` skill authors it** — the producer at the head of the chain (added 3.2.0; neo delegates api-spec authoring to it during its loop, restoring the spec-authoring the retired Architect used to do — `api-and-interface-design` stays the generic interface-design guidance, not the custom-YAML producer); the three api-doc skills below are **read-only consumers**. `openapi-doc` **no longer generates** — it scans the Go source and **diffs it against the api-spec, emitting a drift report** (routes / fields / M-O / types; the sync-back detector — `assets/speccheck.py` reuses the Go-scan engine, writes nothing). The other two *derive* their output from the spec — `open-collection` (a runnable, **self-documenting** Bruno OpenCollection: hand-maps each endpoint + embeds a generated `docs:` rendered by its own `assets/yaml2md.py`) and `confluence-api-doc` (Confluence pages; assembles each page directly from the endpoint YAML's doc-table shape). Each of the three carries its own **three-layer verify** (L1 script · L2 fresh-eyes · L3 completeness sweep). History: consolidated into one `api-doc` gen+publish skill in 0.8.0, re-split md-hub in 0.15.0, then `openapi-doc` added + downstream made dual-source in 0.18.0, then the Markdown `api-doc` skill **removed** and the chain made **spec-only** in 0.19.0; a **dereferenced view** (`bruno/openapi.deref.yaml`, `assets/deref.py`) added alongside the canonical spec in 0.24.0; **then 0.28.0 reworked the whole chain — `api-contract`→`api-spec`: a custom-YAML SoT at `docs/api/` authored by neo (no OpenAPI, no Go-first), retiring `bruno/openapi.yaml` + `openapi.deref.yaml` + `assets/deref.py` and flipping `openapi-doc` from generator to a drift checker**; the `bruno` hand-authoring skill was removed in 0.9.0; `atlassian` — the `acli` Jira/Confluence reference + direct-ops skill — was added in 0.10.0 as a lean "thin shell over `acli --help`" rework of the user-global skill.) **`init-project`** (added 0.30.0) is the odd one out — it does NOT touch `docs/api`/neo/MR work; it scaffolds a **new Go hexagonal/DDD service** from a **frozen template** bundled at `skills/init-project/assets/template/` — an empty-but-runnable, business-stripped snapshot of `account-service` (clean layers + tooling + infra wiring + `.kiro/` steering + `CLAUDE.md`, ZERO domains) under a **sentinel identity** (`example.com/neo/service` / `neo-service` / `NEOSVC`) so the bundled template stays compilable + CI-verifiable. `assets/scaffold.py` copies the template → substitutes the three sentinels (single-pass regex) → `go mod tidy` → `git init` → `go build`; `assets/initcheck.py` is the L1 verify (build/vet, identity, no-leftover-sentinel, manifest, zero-business, /health-wired, best-effort-boot); `references/init-verifier.md` is the L2 fresh-eyes contract; `references/init-project-guide.md` documents how to **refresh the snapshot** when `account-service`'s conventions change. The generated service boots **best-effort** (HTTP first, Postgres/Redis dialed within a 2s timeout, warn-not-panic) so `go run ./cmd/api` serves `/health` with no Docker. The `.kiro/{skills,agents}` neo-port inside the template ships **frozen/verbatim** (it goes stale by design — the user accepted that trade-off). **`migrate-project`** (added 0.31.0) is init-project's **brownfield** counterpart — instead of scaffolding an empty service it refactors an **existing** Go service to the same blueprint, and it **reuses init-project's frozen template + `.kiro/steering/`** as the target-structure contract rather than duplicating it (`INIT_TEMPLATE = <MIGRATE_DIR>/../init-project/assets/template` — a runtime cross-skill dependency; refresh the blueprint by refreshing init-project's snapshot, not this skill). It is a **standalone phase-based orchestrator** (`tools: [Agent, Read, AskUserQuestion]`, delegates all real work via point-to-read) that plans the migration as ordered, independently-verifiable **slices** (one bounded context at a time, S1 installs the contract — `.golangci.yaml` with the target's module substituted for the `example.com/neo/service` sentinel + `.kiro/steering/` + `CLAUDE.md`), executes each on the `migrate/hexagonal-blueprint` branch with `git mv` (history- + behavior-preserving), and verifies each slice (`go build`/`vet`/`test` + golangci depguard/forbidigo). Plan-first (CP1 approval before any code moves) and resumable via `<target>/docs/migration/plan.md` (markdown, sole-writer = Mapper); finishes with a three-layer verify (L1 `assets/structurecheck.py` — a stdlib-only structural tripwire, mutation-tested; L2 `references/migrate-verifier.md` fresh-eyes; L3 completeness). Roles: Analyzer (→ `target-map.md`) · Mapper (→ `plan.md`) · Migrator · Verifier · Reviewer.

## How the pieces wire together

- **`SessionStart` hook** (`hooks/hooks.json` → `run-hook.cmd session-start`) runs on `startup | clear | compact` and injects an `<EXTREMELY_IMPORTANT>` block listing every skill and its triggers. This is what makes Claude reach for the skills proactively without the user naming them.
- **`run-hook.cmd`** is a deliberate polyglot file — cmd.exe reads the `@echo off` batch portion (which finds Git-Bash and re-execs the script), while bash treats the leading `:` as a no-op and falls through to the Unix branch. Hook scripts are intentionally **extensionless** (`session-start`, not `session-start.sh`) because Claude Code's Windows auto-detection prepends `bash` to anything ending in `.sh`, which breaks the wrapper.
- **`/neo`** invokes the `neo` skill directly — skill invocation, no command shim (the skill's `description` is the trigger contract).
- **`neo`** is a THIN loop wrapper over `using-agent-skills` (rebuilt 3.0.0; the old phase-gated v3 lives in `legacy/neo-v3/`). It turns a task into a recursive goal and iterates against a project-specific exit condition until "done" is proven. neo owns only four things: (1) the recursive loop, (2) project memory (`docs/tasks/<slug>/STATE.md` + `docs/knowledge/`), (3) the exit condition authored by the Business Analyst (which AUGMENTS `using-agent-skills` behavior #6 "Verify, Don't Assume", never replaces it), and (4) a human gate at commit/PR. neo DELEGATES the entire SDLC — skill discovery, lifecycle order, the 6 Core Operating Behaviors, verification methodology — to `using-agent-skills`; it never picks skills itself and never re-derives the SDLC (doing so would create a second meta-skill that drifts from upstream — exactly what "not really using agent-skills" feels like). `SKILL.md` runs the lifecycle **inline** — it holds `Edit`/`Write`/`Bash` (plus `Read`/`Skill`/`AskUserQuestion`), declared in its `compatibility.tools`; `Agent` is optional (long-loop isolation + a fresh judgment exit-verifier only). Two roles only: Business Analyst (exit-condition framer) + Librarian (memory primitive + ingest-first gate). The `ingest` skill (standalone, `/ingest <url>`) writes `docs/knowledge/`. Concept grounded in Addy Osmani's *loop engineering* (same author as agent-skills — sibling concept).

## Working in this repo

### Editing skills

- `SKILL.md` frontmatter `description` is **the trigger contract** — Claude uses it (not the body) to decide whether to invoke a skill. Edits to the description change activation behavior; edits to the body change what happens *after* activation. Keep both in sync.
- When adding a new skill, also update: the SessionStart hook (`hooks/session-start`) so its overview block lists the new skill, and the README table.
- `neo` references (`skills/neo/references/`) are **read inline by neo** (point-to-read): `loop-over-meta-skill.md` (how each iteration runs `using-agent-skills` inline), `exit-condition.md` (BA's done template), `state-schema.md` (STATE.md shape), `human-gate.md` (commit/PR escalation). Roles: `roles/business-analyst.md` (exit-condition framer) + `roles/librarian.md` (memory primitive). Changing a role's contract here changes how neo plays that role.
- **`neo` has its own scoped `skills/neo/CLAUDE.md`** — the load-bearing invariants for editing it (the thin-wrapper one-rule, the 7 invariants, inline-execution vs SDLC-delegation, the add-a-role sync list, verify-before-commit). It's a maintainer doc (not loaded at runtime, not shipped to consumers). Read it before non-trivial neo edits; keep neo detail there, not duplicated here.

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
