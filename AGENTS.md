# AGENTS.md

Canonical repository guidance for AI coding harnesses working on this repo. Root `CLAUDE.md` imports it with `@AGENTS.md`.

## Repository Overview

neo is a thin engineering router plus a set of org-specific domain skills. The injected router is an orchestrator: it decides loop vs graph, dispatches specialist nodes, and stops only where a machine gate or a human confirm can prove the work. The generic method layer is vendored from the external `mattpocock/skills` plugin.

## Architecture — three layers

- **Router** — `skills/using-neo/SKILL.md`. The single entry point, injected at session start. Owns loop-or-graph, dispatch, gates, and the verdict. Dispatch mechanics live in `skills/using-neo/GRAPH.md`. All neo behavior changes land here first.
- **Method layer** — vendored from [mattpocock/skills](https://github.com/mattpocock/skills) into `skills/` via the repo-local `sync-mattpocock` skill: `grilling`, `domain-modeling`, `tdd`, `diagnosing-bugs`, `research`, `prototype`, `codebase-design`, `resolving-merge-conflicts`. Allowlist + 3-way compare; never overwrites neo-owned skills. `using-neo` carries inline minimums as a degraded fallback if a method skill is missing on disk.
- **Domain layer** — neo-owned skills in `skills/`: `code-review`, `falsifying`, `bug-hunter`, `attack-test`, `api-spec`, `e2e-playwright`, `openapi-doc`, `open-collection`, `confluence-api-doc`, `markitdown`, `init-project`, `migrate-project`, `atlassian`, `gitlab`. `code-review` began as a synced method skill and was taken over because upstream discovers standards from files this org's services do not have; see `sync-mattpocock`.

`falsifying`, `bug-hunter`, and `attack-test` all start from an all-green (or happy-path) state and differ by target: `falsifying` audits the measuring apparatus (can this gate go red at all?), `bug-hunter` hunts the product in code for what the acceptance criteria never asked — its first ground compares the code against the ingested originals in `docs/knowledge/`, since a spec file is an interpretation and a misread card produces code that passes every gate — and `attack-test` fires abuse paths over live HTTP against a running stack (skip-step, forge-proof, IDOR, idempotency). All three stop at a confirmed symptom and hand off to the orchestrator; none fixes in place.

Machine gates live in the domain layer (`apispeccheck.py`, `e2echeck.py`, per-skill verifiers) and in `using-neo`'s gate table. There are no personas and no phase-contract files. Method-layer updates run through `sync-mattpocock`; domain skills and the router are edited in place.

## Project Structure

```text
skills/            using-neo router + method layer (synced) + 14 domain skills
agents/            graph nodes (`neo-builder`, `neo-author`, `neo-e2e`, `fresh-eyes`) — not user-level copies
hooks/             Claude Code session-start hook (injects using-neo)
extensions/        session-start extensions: `.js` (pi, CJS) and `.mjs` (omp, ESM) — both inject using-neo only
.claude-plugin/    Claude Code plugin + marketplace manifests
.grok-plugin/      Grok Build marketplace index + plugin manifest
.plugin/           Generic plugin manifest mirror (hooks.json variant)
.pi/               pi discovery symlinks (skills → ../skills, extensions → ../extensions)
.agents/skills/    Repo-local maintainer skills (ship, sync-mattpocock); omp discovers via `.omp/config.yml` → `skills.customDirectories`
.omp/              Project omp settings (`config.yml`: customDirectories for `.agents/skills`)
scripts/           Validators
docs/              Setup guides
```

## Harness Channels

Four supported channels plus two installer channels, one canonical content source (`using-neo` + `GRAPH.md`). Graph dispatch is first-class on each — see `skills/using-neo/GRAPH.md` harness mapping.

- **Claude Code**: plugin install; `hooks/session-start.sh` injects `using-neo`; `agents/*.md` are plugin subagents (`Agent` + `subagent_type`).
- **Grok Build**: `.grok-plugin/` + `skills/` + `agents/`. Same SessionStart hook; Grok 1.0.3 may drop stdout — `/using-neo` then. See `docs/grok-setup.md`.
- **pi**: `package.json` `pi` block; session extension injects `using-neo`. Task/Agent when present; else sequential with the GRAPH template.
- **omp**: `package.json` `omp` block; ESM session extension; plugin-root `agents/` as task agents. See `docs/omp-setup.md`.
- **Cursor / Kiro**: `./cursor.sh` / `./kiro.sh` copy skills, `agents/*.md`, and SessionStart hooks (`hooks/cursor/`, `hooks/kiro/`).

Do not fork skill content per harness. A new channel gets a thin injection adapter only.

## Execution Model

Every request routes through `using-neo`. The router is an orchestrator: it decides whether the work is a **loop** (default) or a **graph** (only when specialties hand off, work fans out, or a reviewer is required), dispatches node agents to make the edits, and owns every gate and the completeness verdict. It never edits production, tests, knowledge entries, contracts, or e2e specs — those go through `neo-builder` / `neo-author` / `neo-e2e`. Dispatch mechanics live in `skills/using-neo/GRAPH.md`.

Machine gates are **conditional** on the touched surface: unit coverage via the repo coverage command ≥ 80% when production code changed; AC coverage via `e2echeck` when HTTP-observable ACs or e2e specs are in play; API contract via `apispeccheck` + drift = 0 when `docs/api/` or the HTTP wire changed. An MR is a human confirm through `gitlab` only when the user asks. There is no FEATURE / BUG / RECONCILE pipeline and no spec+plan approval gate. Git branching belongs to the user.

`using-neo` always runs its **high-hallucination profile** (no model detection): single-surface nodes, package tests after every wave that wrote production code, hard evidence paths for external API fields, and a `fresh-eyes` pass only when the wave diff touches production, `docs/api/`, or e2e specs — plus grounding rules (evidence-before-assert, contracts-from-docs-only) for every model.

`CONTEXT.md` at a target service root holds **business vocabulary only**. A `neo-author` node appends a term when the work surfaces one with evidence. The orchestrator does not bootstrap or edit it. `.kiro/steering/` remains the code-convention layer.

## Skill Authoring Conventions

- Every skill lives in `skills/<kebab-case-name>/SKILL.md` with `name` and `description` YAML frontmatter; description ≤ 1024 characters, third-person "what" first, then "when to use".
- Skill-owned assets (templates, verifiers, checkers) live inside that skill's directory. There is no shared `references/` tree.
- Never reference a skill that does not exist in `skills/`. `scripts/validate-skills.js` enforces this (and rejects names of removed upstream skills).
- Method-layer skills are synced, not hand-authored. Prefer expanding `sync-mattpocock`'s allowlist over copying content by hand. Do not edit a synced skill unless you intend the next sync to keep your edit (3-way compare) or conflict.

## Validation Commands

- Skills: `node scripts/validate-skills.js`
- pi package: `node scripts/validate-pi-package.js`
- omp package: `node scripts/validate-omp-package.js`
- Grok package: `node scripts/validate-grok-package.js`
- Claude hook: `bash hooks/session-start-test.sh`
- Claude plugin structure: `claude plugin validate .`
- Grok plugin structure: `grok plugin validate .`

## Versioning and Releases

When the user asks to bump the version, commit, or cut a release:

1. Bump the canonical `version` in `.claude-plugin/plugin.json` (SemVer: patch for fixes/docs, minor for backward-compatible features or skills, major for breaking changes). Sync the same version to `.plugin/plugin.json`, `.grok-plugin/plugin.json`, root `plugin.json`, and `package.json` in the same bump. Marketplace indexes (`.claude-plugin/marketplace.json`, `.grok-plugin/marketplace.json`) intentionally have no version field.
2. After the commit lands, create an annotated tag: `git tag -a v<version> -m "neo <version> — <headline>"`, then push the branch and tag.
3. After the tag reaches `origin`, publish a GitHub release with `gh release create v<version> --title "v<version>" --notes-file <tmp.md> --latest`. Headline plus Added / Changed / Removed / Notes sections in the body; the title is the version only.

Do not commit by default. Create a local commit only when the user explicitly requests it or invokes an approved workflow that includes committing (such as `ship`); follow that workflow's confirmation gates exactly.

## Boundaries

- Always run relevant validators before declaring skill work done.
- Never add vague advice as a skill; skills define actionable processes.
- Never duplicate content between skills or from the method layer; reference instead.
- Never duplicate this guidance in `CLAUDE.md` or another adapter file; update this file.
