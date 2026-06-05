---
name: gitlab
description: >
  Low-level GitLab execution via the glab CLI — the "execution arm" that the neo
  skill invokes (through the Skill tool) to run glab for MR creation and review-comment
  posting. Also usable directly for lightweight, side-effect-free MR operations: Read
  (summarize an MR), Update (อัพเดท MR description), list MRs, view MR/CI status, fetch
  CI job logs, and approve MRs. Trigger when the user pastes a bare GitLab MR URL or says
  "อ่าน MR", "ดู MR", "check MR", "สรุป MR", "อัพเดท MR", "update description",
  "แก้ description", "list MRs", "list open MRs", "check pipeline", "pipeline status",
  "approve MR", or asks for a raw glab operation. NOTE: creating an MR ("สร้าง MR"),
  reviewing an MR ("review MR", "ตรวจ MR"), fixing issues/CI, or addressing review
  feedback now route through the neo skill (which calls this skill for the glab I/O) —
  do NOT trigger this skill directly for those; let neo orchestrate.
compatibility:
  environment: claude-code
  tools:
    - Bash
    - Read
metadata:
  version: "1.1"
---

# GitLab Skill (Claude Code)

Use the `glab` CLI to interact with GitLab. This skill is the **glab execution arm**: the `neo` skill invokes it (via the `Skill` tool) to run glab for MR creation and review-comment posting, and you can also use it directly for lightweight, side-effect-free MR operations.

It provides **mechanics only** — **Create, Update, Read, Post Comment, CI Inspection**, plus general glab operations. MR **review / fix / CI-fix / feedback orchestration now lives in the `neo` skill**; this skill no longer spawns review agents or hands off to other skills.

## URL Parsing

When given a GitLab MR URL like `https://gitlab.com/group/subgroup/project/-/merge_requests/42`:

- **repo_ref**: strip `https://` and everything from `/-/` onward → `gitlab.com/group/subgroup/project`
- **mr_id**: extract the number after `merge_requests/` → `42`

These two values power most glab commands: `glab mr <cmd> <mr_id> --repo <repo_ref>`

## Intent Detection

This skill provides **glab mechanics only**. Determine which operation the user (or the calling `neo` skill) wants:

| Signal | Operation |
|--------|-----------|
| bare MR URL, "อ่าน", "ดู", "check", "สรุป", "summary" | **MR Read** — fetch MR info + diff (+ notes) and summarize |
| "สร้าง MR", "create MR", "open MR" — or invoked by neo to create | **MR Create** — create a new MR from the current branch |
| "อัพเดท MR", "update description", "แก้ description" | **MR Update** — rewrite the MR description |
| "check pipeline", "pipeline status", failed-job logs | **CI Inspection** — fetch pipeline status + job logs (no fixing) |
| "list MRs", "approve MR", or a raw glab command | **Common glab Operations** |
| post a composed review comment (invoked by neo) | **Post a Comment** |

**Routes to neo, NOT here:** reviewing an MR ("review MR", "ตรวจ MR"), fixing review findings or CI failures, and addressing review feedback are orchestrated by the `neo` skill. neo calls THIS skill only for the glab I/O (fetch, create, post comment). Do not spawn review/fix agents in this skill.

**Decision rule:** default a bare MR URL with no action verb to **MR Read** (lightest, no side effects). When neo invokes this skill, it states the operation explicitly — follow it.

---

## MR Create Workflow

Create a new MR from the current branch. No MR URL is needed — this workflow detects the current branch and creates a MR targeting the default branch.

```
1. Verify current branch and uncommitted changes
2. Push branch to remote if needed
3. Analyze changes & generate comprehensive description
4. Create MR with generated description
5. Report MR URL to user
```

### Step 1: Verify Branch

```bash
git branch --show-current
git status --short
```

If there are uncommitted changes, warn the user and ask whether to proceed or commit first. If the current branch is `main` or `master`, warn the user — they likely need to create a feature branch first.

### Step 2: Push Branch

```bash
git push -u origin <current_branch>
```

If the branch is already pushed and up to date, skip this step.

### Step 3: Analyze Changes & Generate Description

Before creating the MR, analyze all changes on the branch to write a comprehensive description. This is the key step — the description must fully capture what was done so reviewers understand the MR without reading every line of diff.

```bash
# Detect target branch
git remote show origin | grep 'HEAD branch'

# All commits since diverging from target
git log <target_branch>..HEAD --format="%h %s"

# File change summary
git diff <target_branch>...HEAD --stat

# Full diff for detailed analysis
git diff <target_branch>...HEAD
```

From the commits and diff, generate a structured MR description:

```
## Summary
<1-2 sentences: overall purpose of this MR — what problem it solves or what feature it adds>

## Changes
<grouped by area — e.g., Features, Refactoring, Bug Fixes, Config, Tests, Docs>
- <concise description of each change>

## Files Changed
<key files with what changed in each — not every file, focus on the important ones>
```

The description must accurately reflect what the commits and diff show. Read the actual code changes — do not just paraphrase commit messages. If commits are messy or unclear, the description should still be clear and well-organized based on what the diff reveals.

If a JIRA card ID is provided (e.g., by the neo skill or the user), add a `JIRA: <ID>` line near the top of the description.

### Step 4: Create MR

```bash
glab mr create --remove-source-branch --squash-before-merge \
  --title "<title>" --description "<generated_description>"
```

- Generate the title from the branch name or commit messages (concise, under 70 chars)
- Use the description generated in Step 3
- `--remove-source-branch` deletes source branch after merge (team default)
- `--squash-before-merge` squash commits when MR is accepted (team default)
- If the user provides a title, description, or other options (assignee, reviewer, target branch), use theirs instead of generating

### Step 5: Report

After creation, show the user the MR URL and key details:

```
✅ สร้าง MR สำเร็จ
- MR: !<mr_id> — <title>
- Branch: <source> → <target>
- URL: <mr_url>
- Delete source branch: ✅
- Squash commits: ✅
```

---

## MR Update Workflow

Update an existing MR's description to reflect the latest changes. Use when additional commits have been pushed after the MR was created, or when the user wants a better description.

```
1. Identify MR (from URL or current branch)
2. Fetch current MR info
3. Analyze all changes on the branch
4. Generate updated description
5. Update MR and report
```

### Step 1: Identify MR

If the user provides a MR URL, parse it. Otherwise, find the MR for the current branch:

```bash
glab mr list --source-branch $(git branch --show-current) --state opened
```

### Step 2: Fetch Current MR Info

```bash
glab mr view <mr_id> --repo <repo_ref> --output json
```

Extract the current description and target branch.

### Step 3: Analyze All Changes

Analyze the full set of changes on the branch — not just the new commits, but everything since diverging from the target branch:

```bash
# All commits on the branch
git log <target_branch>..HEAD --format="%h %s"

# File change summary
git diff <target_branch>...HEAD --stat

# Full diff
git diff <target_branch>...HEAD
```

Compare with the existing MR description to understand what's new or changed since the description was last written.

### Step 4: Generate Updated Description

Write a new description covering ALL changes (original + new), using the same structure as MR Create Step 3:

```
## Summary
<updated overall summary reflecting the full scope>

## Changes
<complete grouped list of all changes>

## Files Changed
<updated file list>
```

Do NOT just append new changes to the old description — rewrite the entire description to be coherent and comprehensive. The description should read as if it was written fresh for the current state of the branch.

### Step 5: Update MR and Report

```bash
glab mr update <mr_id> --repo <repo_ref> --description "<updated_description>"
```

Report:

```
✅ อัพเดท MR description สำเร็จ
- MR: !<mr_id> — <title>
- สิ่งที่เพิ่มเติม: <brief summary of new changes detected since last description>
- URL: <mr_url>
```

---

## MR Read Workflow

The lightest workflow — no specialist agents, no comments posted. Just fetch MR data and present a concise summary to the user in the conversation. (neo also calls this to fetch MR data for a review.)

```
1. Fetch MR info (JSON), diff, and notes
2. Summarize in conversation
```

### Step 1: Fetch

```bash
glab mr view <mr_id> --repo <repo_ref> --output json
glab mr diff <mr_id> --repo <repo_ref>
glab mr note list <mr_id> --repo <repo_ref>
```

### Step 2: Summarize

Present a concise Thai summary covering:

- **MR metadata** — title, author, status, source → target branch, pipeline status
- **What changed** — brief description of the changes (group by area: features, refactoring, CI, docs, tests)
- **Files changed** — count and key files
- **Existing comments** — if there are review comments, briefly note them

Keep it terminal-friendly and scannable. Do NOT spawn specialist agents or post any comments on the MR.

---

## CI Inspection (fetch only)

Fetch pipeline status and failed-job logs for an MR or branch. This skill only **inspects** CI — fixing pipeline failures is orchestrated by the `neo` skill (Bug Fix flow), which calls this section to gather the logs.

### Step 1: Pipeline Status

```bash
glab mr view <mr_id> --repo <repo_ref> --output json
glab ci list --repo <repo_ref> --branch <source_branch>
glab ci status --repo <repo_ref>
```

### Step 2: Failed Job Logs

```bash
# List jobs in the pipeline:
glab ci view <pipeline_id> --repo <repo_ref>

# Fetch logs for each failed job:
glab ci trace <job_id> --repo <repo_ref>
```

Collect the last ~100 lines of each failed job's log — these hold the actual error messages. Summarize each failure (job name, stage, category — Build / Test / Lint / Config — and an error excerpt) and hand it back to neo for orchestration, or present it to the user. Do NOT spawn fix agents here.

---

## Post a Comment (invoked by neo)

When neo has composed a review comment (it owns the table-first review template), it calls this skill to post the comment. Post the provided text **verbatim** — do not re-summarize, re-review, or add findings of your own:

```bash
glab mr note <mr_id> --repo <repo_ref> -m "<composed_comment>"
```

If `glab` is not authenticated or the post fails, return the error and output the comment text so it can be posted manually.

---

## Common glab Operations

Use these directly via `Bash` when the user asks for something other than the workflows above:

| Task | Command |
|------|---------|
| Create MR | `glab mr create --repo <repo_ref> --remove-source-branch --squash-before-merge` |
| List open MRs | `glab mr list --repo <repo_ref>` |
| View MR details | `glab mr view <mr_id> --repo <repo_ref>` |
| Approve MR | `glab mr approve <mr_id> --repo <repo_ref>` |
| Check pipeline status | `glab ci status --repo <repo_ref>` |
| List pipelines | `glab ci list --repo <repo_ref>` |
| Retry a job | `glab ci retry <job_id> --repo <repo_ref>` |
| Update MR description | `glab mr update <mr_id> --repo <repo_ref> --description "<text>"` |
| Add a note/comment | `glab mr note <mr_id> --repo <repo_ref> -m "<text>"` |

### MR Creation Defaults

When creating a MR with `glab mr create`, always include these flags:
- `--remove-source-branch` — delete source branch after merge
- `--squash-before-merge` — squash commits when MR is accepted

These are team defaults and should be applied to every MR creation, whether the user explicitly mentions them or not. The user may add other flags (e.g., `--title`, `--description`, `--assignee`, `--reviewer`) as needed.

For `--repo`, you can omit it if you're already inside the project directory (glab detects the remote automatically).

## Error Handling

- **glab not authenticated**: tell the user to run `glab auth login`
- **glab command fails**: output the result as conversation text instead of posting, explain what failed
- **Empty diff**: note that the MR has no file changes (tell neo / the user) and stop
- **Large diff (>500 lines)**: warn the user, proceed but note the summary may miss details
- **Large single-line files** (minified JS, large JSON): the view tool now shows partial content — note this in the summary if such files are part of the diff
