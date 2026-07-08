---
name: ship
description: One-command release for the neo-plugin — bump the plugin version, pack all working-tree changes into a single commit, tag, push, and publish a GitHub release, in that order. Takes the bump type as an argument (major | minor | patch); infers it from the diff when omitted. Use when the user says "/ship", "/ship minor", "/ship patch", "ship it", "cut a release", "bump version + commit + push + release", "ออก release", "bump + push + release ทีเดียว".
---

# Ship — one-command neo-plugin release

Runs the full release chain for this repo end to end: **bump → commit → tag →
push → GitHub release**. It codifies the "Versioning and releases" flow in the
root `CLAUDE.md`; that section is the source of truth — this skill is the doer.

**Argument:** `/ship <major|minor|patch>` selects the version bump.
- `/ship minor` → pack everything, bump the minor version, ship.
- No argument → **infer** the bump from the change type (see step 2) and show it
  in the preview for the user to confirm.

**Safety model (fixed):** the skill drafts everything, does the **local** commit +
tag, then **STOPS for one confirmation before the irreversible push + release**.
Local commit/tag are cheap to amend or delete; push and a public GitHub release
are not.

## Non-negotiables

- **`.claude-plugin/plugin.json` is the ONLY version source.** `marketplace.json`
  carries no version field — never touch it for versioning.
- **Semver by change type:** `patch` = fix/docs, `minor` = new skill/feature,
  `major` = breaking.
- **One annotated tag per bump, created after the commit:** `v<version>` (v-prefix),
  message `neo <version> — <headline>`.
- **Release title is the version only** (`v<version>`); the `<headline>` goes in the
  notes body, never the title.
- **Commit to the current branch** (this repo ships from `main` — do not open a
  feature branch).
- Every commit message ends with the trailer:
  `Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`

## Workflow

### 1. Preconditions
```bash
git rev-parse --show-toplevel        # must be the neo-plugin repo root
git branch --show-current            # the branch we commit + push
gh auth status                       # gh must be authenticated
git status --porcelain               # must be NON-empty — else "nothing to ship", stop
```

### 2. Determine the new version
Read the current version and compute the next one from the bump type. When no
bump arg was given, infer it: any breaking change → `major`; a new skill or
feature → `minor`; otherwise (fix/docs/refactor) → `patch`.
```bash
cur=$(python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['version'])")
IFS=. read -r MA MI PA <<< "$cur"
case "$BUMP" in
  major) next="$((MA+1)).0.0";;
  minor) next="$MA.$((MI+1)).0";;
  patch) next="$MA.$MI.$((PA+1))";;
esac
echo "$cur -> $next"
```

### 3. Stage + draft (no commit yet)
1. Bump the `version` field in `.claude-plugin/plugin.json` (Edit the
   `"version": "<cur>"` line to `<next>`).
2. Pack everything: `git add -A` (all changes incl. untracked, plus the manifest).
3. Draft the **commit message** — Conventional Commits (`type(scope): subject`),
   a body saying what changed and why, derived from `git diff --cached`. End with
   the Co-Authored-By trailer. Write it to a temp file (your scratchpad).
4. Draft the **release notes** — `### neo <next> — <headline>`, then the sections
   that apply (`Added` / `Changed` / `Fixed` / `Removed` / `Notes`), matching the
   shape of recent releases. Check the last one first:
   ```bash
   gh release view "$(git tag --sort=-v:refname | head -1)"
   ```
   Write the notes to a temp file.

### 4. Preview → local commit + tag → STOP
Show the user, in one message:
- `cur -> next` version and the inferred/selected bump type,
- `git diff --cached --stat` (what is being packed),
- the drafted commit message,
- the drafted release notes.

Then do the **local** steps only:
```bash
git commit -F <commit-msg-file>
git tag -a "v$next" -m "neo $next — <headline>"
```
**Stop here.** Ask the user to confirm the push + release (a single yes). Do NOT
run step 5 until they reply. If they want changes: `git tag -d v$next`, amend the
commit or edit the notes, re-preview.

### 5. On confirm — push + publish
```bash
git push origin "$(git branch --show-current)" && git push origin "v$next"
gh release create "v$next" --title "v$next" --notes-file <notes-file> --latest
```

### 6. Report
Version, commit SHA, tag, and the release URL. Update any relevant auto-memory
release-status line from "NOT committed" to "SHIPPED v<next>".

## Red flags — stop and fix, don't ship through them
- Working tree is clean → nothing to ship; do not cut an empty release.
- `gh auth status` fails → resolve auth first; a half-done chain (pushed, no
  release) is worse than not starting.
- Tempted to edit `marketplace.json` for the version → don't; it has no version field.
- Release **title** contains the headline → wrong; title is `v<version>` only.
- Pushing before the user confirmed the preview → never; the confirm gate is the point.
