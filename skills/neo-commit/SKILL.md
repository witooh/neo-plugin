---
name: neo-commit
description: >
  Entry point for committing work in the neo workflow — the doer that turns a
  working tree into clean, atomic commits. Delegates to
  `git-workflow-and-versioning` for the principles (atomic commits, conventional
  messages, separated concerns, pre-commit hygiene), then applies them to the
  current diff and judges when a rebase is safe (a decision tree; never rewrite
  shared history). Does not cut releases, tags, or version bumps — that is
  `neo-ship`. Use when making ad-hoc commits, staging precise atomic commits, or
  cleaning up unpushed history, or when you invoke /neo-commit. The principles
  come from `git-workflow-and-versioning`.
---

# Neo Commit — atomic-commit doer entry point

## Overview

This is the neo entry point for committing work. It delegates to
`git-workflow-and-versioning` for the commit principles, then acts as the *doer*
that applies them to the current working tree and decides whether a rebase is
warranted. It complements `neo-build` (which commits each increment inside the
Build loop) — reach for `neo-commit` for ad-hoc commits and pre-push history
cleanup. It does **not** cut releases or tags; that is `neo-ship`.

## When to Use

- When making ad-hoc commits or staging precise atomic commits from a mixed
  working tree.
- When cleaning up noisy, unpushed history before a push.
- When you invoke `/neo-commit`.
- Route elsewhere: for the commit *principles* → `git-workflow-and-versioning`;
  for releases, tags, or version bumps → `neo-ship`.

## The Workflow

1. **Survey the state.** `git status --porcelain`; inspect staged and unstaged
   changes (`git diff`, `git diff --staged`); note the branch; check unpushed
   commits with `git log @{u}..` (no upstream = local/unpushed).
2. **Group into atomic commits.** One commit per logical change; keep concerns
   separate (refactor apart from feature, formatting apart from behavior). Stage
   precisely (`git add <path>` or `git add -p`) — **never** a blind `git add -A`.
3. **Run pre-commit hygiene.** Scan the staged diff for secrets, then run the
   project's tests, linter, and type-check. Don't commit on a red state unless
   the user says otherwise.
4. **Write the message.** Conventional format
   (`feat/fix/refactor/test/docs/chore: …`) explaining the *why*, not just the
   *what*.
5. **Commit, then verify.** Re-check `git status` to confirm nothing unintended
   was staged, and `git log --oneline` to confirm the history reads cleanly.

**When to rebase (the decision).** Cleaning history is safe only on commits you
have **not** shared. If the target commits are already pushed to a shared branch,
on main, or possibly built on by others → do **not** rebase (prefer new commits
or a merge; rewriting needs explicit sign-off, then `--force-with-lease`, never a
plain `--force`). If local and unpushed → squashing noisy WIP, or `git pull
--rebase` for a linear history, is fine with confirmation. If you can't tell
whether history is shared, treat it as shared: do not rebase — ask the user.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "`git add -A` is faster." | It absorbs unrelated changes into one commit — stage precisely so each commit is one logical change. |
| "I'll squash this pushed branch to clean it up." | Rewriting shared history breaks everyone built on it — rebase only local, unshared commits. |
| "Tests can run after I commit." | Pre-commit hygiene (secrets scan, tests, lint) exists to keep a red state out of history. |

## Red Flags

- `git add -A` / `git commit -am` staging everything blindly.
- Rebasing or force-pushing commits that are already shared, without sign-off.
- Commit messages that describe the *what* with no *why*.
- Committing on a red test/lint state without explicit user approval.

## Verification

- Each commit is atomic (one logical change) with a conventional message.
- Nothing unintended was staged (`git status` clean afterward).
- Pre-commit checks passed (or the user explicitly accepted a red state).
- Any rebase was performed only on local, unshared history.
