---
name: commit
description: >-
  Smart git commit workflow with branch protection, rebase, and conventional commits.
  Detects protected branches (main, develop, release/*, staging) and auto-creates
  a feature/* branch before committing. Rebases onto base branch to keep history clean.
  Analyzes changes, smart-stages files (excluding secrets), writes conventional commit
  messages, and offers to push.
  Use whenever the user says "commit", "/commit", "commit changes", "save my work",
  "push this", "commit and push", or wants to commit code changes. Also trigger
  when the user finishes a task and says "done", "เสร็จแล้ว", "commit ให้หน่อย",
  "ช่วย commit", or "save and push".
compatibility:
  environment: claude-code
  tools:
    - Bash
    - Read
    - Grep
    - AskUserQuestion
metadata:
  author: witooh
  version: "1.0"
---

# Commit

Smart git commit workflow that protects important branches, writes good commit messages, and streamlines the commit-push cycle.

## Workflow

Execute these steps in order. Gather information first, then act.

### Step 1: Gather State

Run these commands in parallel to understand the current repo state:

| Command | Purpose |
|---------|---------|
| `git branch --show-current` | Current branch name |
| `git status --short` | Changed files overview |
| `git diff --stat` | Unstaged change summary |
| `git diff --cached --stat` | Staged change summary |
| `git log --oneline -5` | Recent commit style reference |

If there are no changes (working tree clean, nothing staged), tell the user there is nothing to commit and stop.

### Step 2: Branch Protection Check

Check if the current branch matches any protected pattern:

| Protected Pattern | Match Rule |
|-------------------|------------|
| `main` | Exact match |
| `develop` | Exact match |
| `release/*` | Starts with `release/` |
| `staging` | Exact match |

**If on a protected branch**, you MUST create a new branch before committing:

1. Read the diff content (`git diff` and `git diff --cached`) to understand what changed
2. Determine a short descriptive slug from the changes (e.g., `add-user-auth`, `fix-login-redirect`)
3. Compose the branch name as `feature/<slug>`
4. Ask the user to confirm or edit the branch name using AskUserQuestion
5. Run `git checkout -b <branch-name>`

**If NOT on a protected branch**, proceed to Step 3.

### Step 3: Rebase onto Base Branch

Before committing, rebase the current feature branch onto the latest base branch to keep history linear and avoid merge conflicts later.

1. Determine the base branch — check which of these exists (in order): `develop`, `main`, `master`. Use the first one found.
2. Stash any uncommitted changes: `git stash`
3. Fetch latest from origin (if remote exists): `git fetch origin <base-branch> 2>/dev/null`
4. Rebase: `git rebase origin/<base-branch>` (or `git rebase <base-branch>` if no remote)
5. Pop the stash: `git stash pop`

**If rebase has conflicts:**
- Do NOT auto-resolve. Run `git rebase --abort` to undo.
- Tell the user there are conflicts and show which files conflict.
- Let the user decide how to proceed — do not force through.

**Skip rebase when:**
- There is no remote configured (`git remote -v` is empty)
- The branch was just created in Step 2 (it's already based on the latest)

### Step 4: Smart Stage

Analyze all changed files and stage them intelligently.

**Never stage these files** (even if modified):

| Pattern | Reason |
|---------|--------|
| `.env*` | Environment secrets |
| `*.pem`, `*.key` | Private keys |
| `credentials*`, `secret*` | Credential files |
| `*.log` | Log files |
| `node_modules/`, `.sisyphus/` | Generated directories |

**Staging logic:**
1. If files are already staged (`git diff --cached` is non-empty), respect the existing staging — only review for dangerous files
2. If nothing is staged, analyze the unstaged changes and stage relevant files using `git add <file1> <file2> ...` (explicit file names, never `git add -A` or `git add .`)
3. If any dangerous files are detected in the changes, warn the user and exclude them

### Step 5: Write Commit Message

Use **Conventional Commits** format based on the changes:

```
<type>(<scope>): <description>

[optional body]

Co-Authored-By: Claude <noreply@anthropic.com>
```

**Type selection guide:**

| Type | When to use |
|------|------------|
| `feat` | New feature or capability |
| `fix` | Bug fix |
| `refactor` | Code restructuring, no behavior change |
| `docs` | Documentation only |
| `test` | Adding or updating tests |
| `chore` | Build, config, tooling changes |
| `style` | Formatting, whitespace, semicolons |
| `perf` | Performance improvement |

**Rules:**
- Scope is optional — derive from the primary directory or module affected
- Description: imperative mood, lowercase, no period, under 72 chars
- Body: only if the change is non-trivial — explain the "why", not the "what"
- Reference the recent git log style (from Step 1) and try to stay consistent with the repo's conventions
- Always end with `Co-Authored-By: Claude <noreply@anthropic.com>`

Use a HEREDOC to pass the commit message to avoid shell escaping issues:

```bash
git commit -m "$(cat <<'EOF'
type(scope): description

Optional body explaining why.

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"
```

### Step 6: Verify and Offer Push

After the commit succeeds:

1. Run `git status` to verify the commit went through
2. If pre-commit hooks fail: fix the issue, re-stage, and create a NEW commit (never amend)
3. Ask the user if they want to push to origin:

Ask using AskUserQuestion with these options:
- **Push to origin** — `git push -u origin <branch-name>`
- **Skip push** — done, no push

If the user chooses to push, run `git push -u origin <current-branch>` and confirm success.

## Important Safety Rules

- Never commit files that look like they contain secrets
- Never amend commits — always create new ones
- Never force push
- Never skip pre-commit hooks (`--no-verify`)
- If `git push` fails due to remote rejection, show the error and let the user decide what to do — do not retry with `--force`
