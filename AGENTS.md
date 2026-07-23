# AGENTS.md

Canonical repository guidance for AI coding harnesses working on this repo. Root `CLAUDE.md` imports it with `@AGENTS.md`.

## Repository Overview

neo is a thin engineering router plus a set of org-specific domain skills. It drives feature work end to end (ingest → align → api → spec → build → verify → review → doc → MR) with machine-verifiable gates, and borrows its generic method layer from the external `mattpocock/skills` plugin instead of bundling one.

## Architecture — three layers

- **Router** — `skills/using-neo/SKILL.md`. The single entry point, injected at session start. Detects intent, drives the flow, enforces gates. All neo behavior changes land here first.
- **Method layer** — vendored from [mattpocock/skills](https://github.com/mattpocock/skills) into `skills/` via the repo-local `sync-mattpocock` skill: `grilling`, `domain-modeling`, `tdd`, `code-review`, `diagnosing-bugs`, `research`, `prototype`, `codebase-design`, `resolving-merge-conflicts`. Allowlist + 3-way compare; never overwrites neo-owned skills. `using-neo` carries inline minimums as a degraded fallback if a method skill is missing on disk.
- **Domain layer** — neo-owned skills in `skills/`: `api-spec`, `e2e-playwright`, `openapi-doc`, `open-collection`, `confluence-api-doc`, `markitdown`, `init-project`, `migrate-project`, `atlassian`, `gitlab`.

Machine gates live in the domain layer (`apispeccheck.py`, `e2echeck.py`, per-skill verifiers) and in `using-neo`'s gate table. There are no personas and no phase-contract files. Method-layer updates run through `sync-mattpocock`; domain skills and the router are edited in place.

## Project Structure

```text
skills/            using-neo router + method layer (synced) + 10 domain skills
hooks/             Claude Code session-start hook (injects using-neo)
extensions/        pi session-start extension (injects using-neo + steering INDEX)
.claude-plugin/    Claude Code plugin + marketplace manifests
.plugin/           Generic plugin manifest mirror (hooks.json variant)
.pi/               pi discovery symlinks (skills → ../skills, extensions → ../extensions)
.agents/skills/    Repo-local skills for working on neo itself (ship, sync-mattpocock)
scripts/           Validators
docs/              Setup guides
```

## Harness Channels

Two supported channels, one canonical content source:

- **Claude Code**: plugin install; `hooks/session-start.sh` injects the full `using-neo` SKILL.md plus the target repo's `.kiro/steering/INDEX.md` when present.
- **pi**: `package.json` `pi` block + `.pi/` symlinks; `extensions/using-neo-session-start.js` performs the same injection.

Other harnesses are unsupported by design. If one is needed later, add a thin injection adapter — never fork skill content per harness.

## Execution Model

Every request routes through `using-neo`. It selects a flow (FEATURE, BUG, REFACTOR, or a direct domain-skill route), runs it continuously, and stops only at its four gates: spec+plan approval (human), AC coverage via `e2echeck` (machine), API contract via `apispeccheck` + drift (machine), MR/ship (human). Git branching belongs to the user; the only git side effects live behind the MR gate.

`using-neo` always runs its **high-hallucination profile** (no model detection): single-surface slices, package tests after every task, hard evidence paths for external API fields, and a mandatory fresh-eyes pass on REVIEW — plus grounding rules (evidence-before-assert, contracts-from-docs-only) for every model.

## Skill Authoring Conventions

- Every skill lives in `skills/<kebab-case-name>/SKILL.md` with `name` and `description` YAML frontmatter; description ≤ 1024 characters, third-person "what" first, then "when to use".
- Skill-owned assets (templates, verifiers, checkers) live inside that skill's directory. There is no shared `references/` tree.
- Never reference a skill that does not exist in `skills/`. `scripts/validate-skills.js` enforces this (and rejects names of removed upstream skills).
- Method-layer skills are synced, not hand-authored. Prefer expanding `sync-mattpocock`'s allowlist over copying content by hand. Do not edit a synced skill unless you intend the next sync to keep your edit (3-way compare) or conflict.

## Validation Commands

- Skills: `node scripts/validate-skills.js`
- pi package: `node scripts/validate-pi-package.js`
- Claude hook: `bash hooks/session-start-test.sh`
- Claude plugin structure: `claude plugin validate .`

## Versioning and Releases

When the user asks to bump the version, commit, or cut a release:

1. Bump the canonical `version` in `.claude-plugin/plugin.json` (SemVer: patch for fixes/docs, minor for backward-compatible features or skills, major for breaking changes). Sync the same version to `.plugin/plugin.json`. `.claude-plugin/marketplace.json` intentionally has no version field.
2. After the commit lands, create an annotated tag: `git tag -a v<version> -m "neo <version> — <headline>"`, then push the branch and tag.
3. After the tag reaches `origin`, publish a GitHub release with `gh release create v<version> --title "v<version>" --notes-file <tmp.md> --latest`. Headline plus Added / Changed / Removed / Notes sections in the body; the title is the version only.

Do not commit by default. Create a local commit only when the user explicitly requests it or invokes an approved workflow that includes committing (such as `ship`); follow that workflow's confirmation gates exactly.

## Boundaries

- Always run relevant validators before declaring skill work done.
- Never add vague advice as a skill; skills define actionable processes.
- Never duplicate content between skills or from the method layer; reference instead.
- Never duplicate this guidance in `CLAUDE.md` or another adapter file; update this file.
