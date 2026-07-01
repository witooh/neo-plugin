---
name: sync-upstream
description: Sync the upstream addyosmani/agent-skills plugin into this neo fork and re-apply the neo rebrand. Use when updating agent-skills, pulling upstream skill/hook/agent/reference changes, or when the user says "sync upstream", "update agent-skills into neo", or "pull the latest agent-skills".
---

# Sync upstream agent-skills into neo

This repo is a rebranded **fork** of `addyosmani/agent-skills`. This skill pulls
upstream updates for the parts neo tracks, re-applies the deterministic
`agent-skills → neo` rebrand, and preserves everything neo owns.

- **In scope (synced from upstream):** `skills/` (except `using-agent-skills`),
  `hooks/`, `agents/`, `references/`.
- **Out of scope (neo-owned, never touched):** `docs/`, `commands/`,
  `.claude-plugin/` manifests, `README.md`, `AGENTS.md`, `.github/`, and the
  `using-neo` router (neo's customized fork of `using-agent-skills`).

Two files do the work:

- `assets/rebrand.py` — the deterministic transform and **single source of truth**
  for the `agent-skills → neo` rules. Edit this when upstream introduces a **new**
  brand pattern.
- `assets/sync.py` — orchestration: fetch, transform in-scope files, classify
  neo-local vs upstream-removed, dry-run/apply, and advance the baseline recorded
  in `sync-state.json`.

## Workflow

1. **Preflight.** Confirm the upstream clone at `sync-state.json:upstream_path`
   exists (or pass `--upstream <path>`).

2. **Dry run — always first.**
   ```bash
   python3 .claude/skills/sync-upstream/assets/sync.py
   ```
   Read the report:
   - **add / update** — files the apply step will write (upstream delta, rebranded).
   - **neo-owned edits kept** — upstream-owned files you hand-edited; the sync keeps
     *your* version (upstream did not change them) and does not overwrite them.
   - **neo-local skills preserved** — your own skills; confirm they are all listed.
   - **CONFLICT** — a file both you *and* upstream changed. The sync does NOT
     overwrite it; merge by hand, then re-run.
   - **REVIEW – removed upstream** — skills upstream deleted. Decide per skill
     whether to drop it from neo (manual `git rm`); the sync never auto-deletes.
   - **REVIEW – residual brand tokens** — a file still contains `agent-skills` /
     `addyosmani` after transform ⇒ upstream added a **novel** pattern. Do NOT
     apply: add a rule to `assets/rebrand.py`, then re-run the dry run until clean.

3. **Apply.**
   ```bash
   python3 .claude/skills/sync-upstream/assets/sync.py --apply
   ```
   Writes the changes and advances `last_synced_commit` / `synced_skills`.

4. **Verify (do not skip).**
   ```bash
   node scripts/validate-skills.js                         # upstream skills must stay ✓
   bash hooks/session-start-test.sh                        # hook loads (path/brand intact)
   grep -rnI 'addyosmani' skills hooks agents references   # expect no output
   bash hooks/session-start.sh | jq -r .message | head -1  # expect: neo loaded. ...
   ```
   The hook test, the grep, and the hook message must pass. For `validate-skills.js`,
   the **upstream-owned** skills must stay green — the sync must not introduce a new
   failure there. (neo-local skills such as `api-spec` may already fail the agent-skills
   anatomy checks; that is pre-existing and separate, not a sync regression.) If a
   **new** upstream skill trips the validator, handle it the way existing ones are.

5. **Finish.** Review `git diff`, bump the plugin `version` in
   `.claude-plugin/plugin.json` + `marketplace.json` (patch/minor by change size),
   then commit. (Committing is yours to run.)

## Guarantees / boundaries

- **Idempotent.** The dry run against the recorded baseline reports zero changes.
  If a run ever shows spurious changes, `rebrand.py` has drifted from the manual
  rebrand — fix the rules, not the output.
- **Never clobbers neo work.** Neo-local skills (absent from upstream *and* the
  baseline) are left untouched — no allow-list to keep. Upstream-owned files you
  hand-edit are detected by a 3-way compare and kept, never silently overwritten.
- **Reports, never guesses.** Removed-upstream skills and novel brand patterns are
  surfaced for a human decision, not resolved automatically.
