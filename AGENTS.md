# AGENTS.md

Canonical repository guidance for AI coding harnesses working on this repo. Root `CLAUDE.md` imports it with `@AGENTS.md`.

## Repository Overview

neo is a skill pack of 17 org domain skills for AI coding agents (HTTP/API/e2e, Jira/GitLab, Go scaffold, SIT). It is not a router and does not ship a bundled workflow. The host agent loads matching skills; developers can also pick a skill themselves. neo does not orchestrate ingest → spec → implement.

The 17 skills live in `skills/`:

- **User-invoked:** `advice-mode`
- **Model-invoked:** `markitdown`, `atlassian`, `gitlab`, `api-spec`, `openapi-doc`, `open-collection`, `confluence-api-doc`, `e2e-playwright`, `http-audit-log`, `falsifying`, `bug-hunter`, `attack-test`, `init-project`, `migrate-project`, `neo-core-sit`, `neo-aux-sit`

`falsifying`, `bug-hunter`, and `attack-test` all start from an all-green (or happy-path) state and differ by target: `falsifying` audits the measuring apparatus (can this gate go red at all?), `bug-hunter` hunts the product in code for what the acceptance criteria never asked — its first ground compares the code against the ingested originals in `docs/knowledge/` — and `attack-test` fires abuse paths over live HTTP against a running stack. All three stop at a confirmed symptom; none fixes in place.

There are no personas and no phase-contract files. Domain skills are edited in place.

## Project Structure

```text
skills/            the 17 org domain skills
scripts/           Validators
docs/              Setup guides
.claude-plugin/    Claude Code plugin + marketplace manifests
.cursor-plugin/    Cursor plugin + marketplace manifests (GitHub Add)
.grok-plugin/      Grok Build marketplace index + plugin manifest
.omp-plugin/       omp marketplace index
.plugin/           Generic plugin manifest mirror
.pi/               pi discovery symlink (`skills` → `../skills`)
.agents/skills/    Repo-local maintainer skill (`ship`); omp discovers via `.omp/config.yml` → `skills.customDirectories`
.omp/              Project omp settings (`config.yml`: customDirectories for `.agents/skills`)
```

`ship` is maintainer-only and is not one of the shipped 17.

## Harness Channels

Six supported channels. Each **only discovers skills**. There is no SessionStart injection.

- **Claude Code**: plugin install; skills from `skills/`.
- **Grok Build**: `.grok-plugin/` + `skills/`. See `docs/grok-setup.md`.
- **pi**: `package.json` `pi.skills: ["./skills"]`; `.pi/skills` symlink for a project-local checkout. See `docs/pi-setup.md`.
- **omp**: `package.json` `"omp": {}` (harness discovery); skills from `skills/`. See `docs/omp-setup.md`.
- **Cursor**: `.cursor-plugin/marketplace.json` + `.cursor-plugin/plugin.json`; skills from `skills/`. Add the repo from GitHub in Customize. Cloud Agent snapshot install is `scripts/install-cursor-cloud.sh` (`install`, not `start`).
- **Kiro**: `./kiro.sh` copies **skills only**.

Do not fork skill content per harness.

## Execution Model

There is none. The host agent loads matching skills. neo does not own the work, the edits, or a completeness verdict. Git branching belongs to the user.

## Skill Authoring Conventions

- Every skill lives in `skills/<kebab-case-name>/SKILL.md` with `name` and `description` YAML frontmatter; description ≤ 1024 characters, third-person "what" first, then "when to use".
- `advice-mode` sets `disable-model-invocation: true` so only the user can invoke it. Validators must allow that frontmatter field.
- Skill-owned assets (templates, verifiers, checkers) live inside that skill's directory. There is no shared `references/` tree.
- Never reference a skill that does not exist in `skills/`. `scripts/validate-skills.js` enforces this (and rejects names of removed skills).

## Validation Commands

- Skills: `node scripts/validate-skills.js`
- pi package: `node scripts/validate-pi-package.js`
- omp package: `node scripts/validate-omp-package.js`
- Grok package: `node scripts/validate-grok-package.js`
- Cursor package: `node scripts/validate-cursor-package.js`
- Claude plugin structure: `claude plugin validate .`
- Grok plugin structure: `grok plugin validate .`

## Versioning and Releases

When the user asks to bump the version, commit, or cut a release:

1. Bump the canonical `version` in `.claude-plugin/plugin.json` (SemVer: patch for fixes/docs, minor for backward-compatible features or skills, major for breaking changes). Sync the same version to `.plugin/plugin.json`, `.grok-plugin/plugin.json`, `.cursor-plugin/plugin.json`, root `plugin.json`, and `package.json` in the same bump. Marketplace indexes (`.claude-plugin/marketplace.json`, `.cursor-plugin/marketplace.json`, `.grok-plugin/marketplace.json`, `.omp-plugin/marketplace.json`) intentionally have no version field.
2. After the commit lands, create an annotated tag: `git tag -a v<version> -m "neo <version> — <headline>"`, then push the branch and tag.
3. After the tag reaches `origin`, publish a GitHub release with `gh release create v<version> --title "v<version>" --notes-file <tmp.md> --latest`. Headline plus Added / Changed / Removed / Notes sections in the body; the title is the version only.

Do not commit by default. Create a local commit only when the user explicitly requests it or invokes an approved workflow that includes committing (such as `ship`); follow that workflow's confirmation gates exactly. `.agents/skills/ship` is the maintainer-only release skill; it is not shipped in `skills/`.

## Boundaries

- Always run relevant validators before declaring skill work done.
- Never add vague advice as a skill; skills define actionable processes.
- Never duplicate content between skills; reference instead.
- Never duplicate this guidance in `CLAUDE.md` or another adapter file; update this file.
