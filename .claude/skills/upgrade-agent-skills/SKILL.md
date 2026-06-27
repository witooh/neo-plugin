---
name: "upgrade-agent-skills"
description: "Upgrade the ported agent-skills lifecycle bundle to a newer upstream release. Use when a new addyosmani/agent-skills tag is out and you need to port the delta into this plugin."
version: 1
created: "2026-06-27"
updated: "2026-06-27"
---
## When to Use
["A new agent-skills release/tag is published upstream and you want to pull it into neo-dev-toolkit.", "You see upstream drift in skills/agents/commands/references that came from agent-skills.", "After confirming the current ported version (tracked in hooks/session-start header + README agent-skills section) is behind upstream.", "Do NOT use for neo-native skill changes — neo skills (neo, gitlab, commit, atlassian, openapi-doc, open-collection, confluence-api-doc, init-project, migrate-project) are ours, not upstream."]

## Procedure
1. **Phase 0 — scan upstream.** List available releases via the GitHub API (no git needed): `curl -fsSL -H 'User-Agent: pi' https://api.github.com/repos/addyosmani/agent-skills/releases | grep '"tag_name"'`. Compare to the ported version recorded in `hooks/session-start` header comment ('Ported from upstream agent-skills <VER>') and the README agent-skills section. Read the release notes at https://github.com/addyosmani/agent-skills/releases. NOTE: upstream tags have NO v-prefix (e.g. `0.6.3`, not `v0.6.3`).
2. **Phase 1 — download + extract the new tag to staging.** `work=/tmp/as-upgrade; rm -rf "$work"; mkdir -p "$work"; cd "$work"`, then download GitHub's auto-generated source archive: `curl -fsSL -o src.zip "https://github.com/addyosmani/agent-skills/archive/refs/tags/<newtag>.zip"` and `unzip -q src.zip`. The zip extracts to a nested folder `agent-skills-<newtag>/` — treat THAT folder as the staging root (`STAGING="$work/agent-skills-<newtag>"`). (tar.gz works too: `.../archive/refs/tags/<newtag>.tar.gz` + `tar xzf`.) Releases have NO attached assets — always use these auto-generated source archives.
3. **Phase 2 — diff delta.** Diff staging vs the current upstream-origin files in the target repo: `diff -r "$STAGING/skills" <repo>/skills` (but EXCLUDE the 9 neo-native skills), plus agents/, commands/ (note: upstream also ships `.claude/commands/` — we use that path), references/, scripts/validate-skills.js, docs/skill-anatomy.md, hooks/sdd-cache-*, hooks/simplify-ignore.sh. Categorize: added / changed / removed / renamed.
4. **Phase 3 — identify re-apply points.** Three files carry OUR hand-edits that upstream will clobber: (a) `skills/idea-refine/SKILL.md` — the hardcoded `/mnt/skills/user/idea-refine/scripts/idea-refine.sh` must become `"${CLAUDE_PLUGIN_ROOT}/skills/idea-refine/scripts/idea-refine.sh"`; (b) `scripts/validate-skills.js` — the `SECTION_EXEMPT_SKILLS` map has 9 neo-native entries we added; (c) `hooks/session-start` — custom neo entries 1-9 + the #10 router entry for the bundle, all hand-written.
5. **Phase 4 — copy the delta.** Copy added + changed files from staging. Delete removed files. For renames, git-mv in the target. NEVER blanket-`cp -R "$STAGING/skills/." <repo>/skills/` — it would clobber neo-native skills and the idea-refine path fix. Copy per-skill, skipping neo-native dirs.
6. **Phase 5 — re-apply our modifications.** Re-apply the idea-refine path fix. Re-run `node scripts/validate-skills.js`: any NEW upstream skill that fails anatomy (missing ## Overview / ## Red Flags / etc.) needs an entry added to SECTION_EXEMPT_SKILLS with a documented reason (standard-anatomy skills pass on their own).
7. **Phase 6 — re-merge the integration layer.** If the upstream skill SET changed (added/removed/renamed): update `hooks/session-start` entry #10's lifecycle-map line to match, update README's agent-skills table, update CLAUDE.md's 'Skills currently bundled' line, and the header comment version marker.
8. **Phase 7 — bump + manifests.** Bump `.claude-plugin/plugin.json` AND `.claude-plugin/marketplace.json` `version` in lockstep (keep the description in sync too). Semver: minor = new upstream skills/agents/commands; patch = upstream fixes with no new skill. Update the 'Ported from upstream agent-skills <VER>' marker to the new tag.
9. **Phase 8 — validate.** Run: `node scripts/validate-skills.js` (expect 0 errors; the 2 `local`/`params` warnings in open-collection are pre-existing false positives). `bash hooks/session-start | python3 -m json.tool` (must be valid JSON). `grep -rn /mnt/ skills agents .claude references` (expect none). Confirm `.claude-plugin/plugin.json` `agents`/`commands` arrays still resolve to existing files.
10. **Phase 9 — release.** Follow the repo's standard release flow (CLAUDE.md 'Before every commit'): tag `v<newpluginversion>`, push, `gh release create` with Added/Changed/Removed/Notes sections noting the upstream version bumped.
## Pitfalls
- Upstream tags have NO v-prefix: `0.6.3`, never `v0.6.3`. The download URL must match: `.../archive/refs/tags/0.6.3.zip` (no `v`). The plugin's OWN tags DO use v-prefix (v0.33.0). Don't confuse the two.
- The auto-generated source zip extracts to a NESTED folder `agent-skills-<tag>/` (not flat). Always cd into it / set `STAGING` to it before diffing — diffing against the outer dir compares the wrong level.
- Releases carry NO attached binary assets — the only downloads are GitHub's auto-generated source archives (`.zip` and `.tar.gz`). Don't look for a release-specific asset file.
- Do NOT `cp -R` the whole skills dir from staging — it overwrites the 9 neo-native skills and the idea-refine path fix. Copy per upstream-skill.
- The 9 neo-native skills (neo, gitlab, commit, atlassian, openapi-doc, open-collection, confluence-api-doc, init-project, migrate-project) are OURS and must survive every upgrade. They live alongside upstream skills but have nothing to do with upstream.
- If upstream renames or removes a skill that `hooks/session-start` references, the hook will advertise a dead skill — always re-check entry #10's lifecycle map after a delta that touches the skill set.
- Staging work dir (`/tmp/as-upgrade`) disappears on reboot — always re-download in Phase 1, don't assume an old extract is fresh (it may be a different tag than you think).
- New upstream skills with non-standard anatomy will fail `validate-skills.js`. Either upstream fixed them (passes), or you add an exemption entry with a real reason — never blanket-disable the validator.
- `brainstorm`/`improve` were REMOVED and replaced by upstream's `idea-refine`/`code-simplification`. If upstream ever resurrects similar names, do not blindly re-add the old neo versions.
- The opt-in hooks (sdd-cache, simplify-ignore) are NOT registered in hooks.json by design (project-scoped, heavy side-effects). Keep them unregistered even when syncing newer versions.
## Verification
1. `node scripts/validate-skills.js` exits 0 with 0 errors (the 2 open-collection warnings are known false positives).
2. `bash hooks/session-start` emits valid JSON parseable by `python3 -m json.tool`.
3. `grep -rn -E '/mnt/|/skills/user' skills agents .claude references` returns nothing.
4. `python3 -c "import json; p=json.load(open('.claude-plugin/plugin.json')); m=json.load(open('.claude-plugin/marketplace.json'))['plugins'][0]; print(p['version']==m['version'])"` prints True (manifests in sync).
5. Every path in `.claude-plugin/plugin.json` `agents`/`commands` arrays resolves to an existing file.
6. The 'Ported from upstream agent-skills <VER>' marker in hooks/session-start and the README agent-skills section both show the new tag.
7. `find skills -maxdepth 2 -name SKILL.md | wc -l` equals 9 (neo-native) + (upstream skill count) — no neo skill lost, no upstream skill missing.
8. All 4 agent files + 8 command files + 5 reference checklists still present.
