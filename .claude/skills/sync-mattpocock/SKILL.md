---
name: sync-mattpocock
description: Sync the allowlisted method-layer skills from mattpocock/skills into this neo-plugin repo. Use when updating the method layer, pulling tdd/code-review/grilling and related skills, or when the user says "sync mattpocock", "update method skills", or "pull mattpocock skills".
---

# Sync mattpocock method skills into neo

neo vendors its **method layer** from [mattpocock/skills](https://github.com/mattpocock/skills)
instead of depending on an external plugin at runtime. This skill pulls the
allowlisted skills into `skills/<name>/` (flat neo layout) and never touches
neo-owned domain skills or the `using-neo` router.

## In scope

Allowlist is `sync-state.json:synced_skills` (source path → dest name):

| Dest (`skills/`) | Upstream source |
|---|---|
| `tdd` | `skills/engineering/tdd` |
| `code-review` | `skills/engineering/code-review` |
| `diagnosing-bugs` | `skills/engineering/diagnosing-bugs` |
| `domain-modeling` | `skills/engineering/domain-modeling` |
| `research` | `skills/engineering/research` |
| `prototype` | `skills/engineering/prototype` |
| `codebase-design` | `skills/engineering/codebase-design` |
| `resolving-merge-conflicts` | `skills/engineering/resolving-merge-conflicts` |
| `grilling` | `skills/productivity/grilling` |

## Out of scope (never touched)

- All neo-owned skills: `using-neo`, `api-spec`, `e2e-playwright`, `openapi-doc`,
  `open-collection`, `confluence-api-doc`, `markitdown`, `init-project`,
  `migrate-project`, `atlassian`, `gitlab`
- Entry skills from mattpocock that neo absorbed into the router
  (`grill-with-docs`, `implement`, `wayfinder`, `to-spec`, `to-tickets`, `triage`, …)
- `hooks/`, `agents/`, manifests, docs, README

To add a method skill later: append it to `synced_skills` in `sync-state.json`,
then re-run. To drop one: remove it from the allowlist and `git rm skills/<name>`
by hand — the sync never auto-deletes.

## Files

- `assets/sync.py` — fetch/clone, 3-way compare, dry-run/apply, advance baseline
- `sync-state.json` — allowlist, upstream URL/path, last synced commit

## Workflow

1. **Dry run — always first.**

   ```bash
   python3 .agents/skills/sync-mattpocock/assets/sync.py
   ```

   Optional: `--upstream <path>` if you already have a local clone;
   `--ref origin/main` (default from state); `--no-fetch` to skip `git fetch`.

   Read the report:
   - **ADD / UPDATE** — files the apply step will write
   - **LOCAL-KEPT** — you edited a vendored file and upstream did not change it; kept
   - **CONFLICT** — both you and upstream changed the same file; merge by hand, re-run
   - **UPSTREAM-REMOVED** — file gone upstream; decide manually (sync never deletes)
   - **MISSING-UPSTREAM-SKILL** — allowlist path not found; fix `sync-state.json`

2. **Apply.**

   ```bash
   python3 .agents/skills/sync-mattpocock/assets/sync.py --apply
   ```

   Writes add/update files and advances `last_synced_commit` / `last_synced_date`.
   First run clones into `.agents/skills/sync-mattpocock/.upstream-cache/`
   (gitignored-friendly; re-used on later runs).

3. **Verify (do not skip).**

   ```bash
   node scripts/validate-skills.js
   node scripts/validate-pi-package.js
   bash hooks/session-start-test.sh
   ```

   All green. Spot-check `git diff skills/` — only allowlisted method skills should change.

4. **Finish.** Review the diff, bump plugin version if you are shipping the update,
   then commit (yours to run). Prefer `/ship` when cutting a release.

## Guarantees

- **Allowlist-only.** Skills not listed in `synced_skills` are invisible to the sync.
- **Neo-owned hard-blocked.** Even a mistaken allowlist entry for `using-neo` / domain
  skills is rejected up front.
- **Never clobbers hand-edits.** 3-way compare keeps your change when upstream is quiet;
  CONFLICT when both sides moved.
- **Never auto-deletes.** Removed-upstream files are reported only.
- **Idempotent.** Dry run against the recorded baseline reports zero pending writes.

## When to run

- Upstream mattpocock/skills cut a release you want
- A method skill is missing under `skills/` after a fresh clone
- You expanded `synced_skills` and need the new skill on disk
