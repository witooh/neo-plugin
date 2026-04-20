---
name: gitlab
description: >
  Interact with GitLab via the glab CLI. Supports seven MR workflows — Create (สร้าง MR),
  Update (อัพเดท description), Read (summarize), Review (full code/security/QA review),
  Fix (review + implement), CI Fix (fix pipeline failures), and Feedback (address review comments).
  Trigger whenever the user provides a GitLab MR URL or says anything like
  "สร้าง MR", "create MR", "open MR", "เปิด MR",
  "อัพเดท MR", "update MR", "update description", "แก้ description", "อัพเดท description",
  "อ่าน MR", "ดู MR", "check MR", "review MR", "ช่วย review MR นี้",
  "ตรวจ MR", "แก้ตาม MR", "fix MR", "fix CI", "fix pipeline", "แก้ pipeline",
  "แก้ตาม comment", "แก้ตาม feedback", "address feedback", or just pastes a GitLab MR URL.
  Also supports listing MRs, viewing MR status, checking CI/CD pipelines, approving MRs,
  and other glab operations. Trigger on "check pipeline", "list open MRs", "pipeline failed",
  or any GitLab-related task.
compatibility:
  environment: claude-code
  tools:
    - Bash
    - Read
    - Agent
metadata:
  version: "1.0"
---

# GitLab Skill (Claude Code)

Use the `glab` CLI to interact with GitLab. Supports seven MR workflows (Create → Update → Read → Review → Fix → CI Fix → Feedback) plus general glab operations.

## URL Parsing

When given a GitLab MR URL like `https://gitlab.com/group/subgroup/project/-/merge_requests/42`:

- **repo_ref**: strip `https://` and everything from `/-/` onward → `gitlab.com/group/subgroup/project`
- **mr_id**: extract the number after `merge_requests/` → `42`

These two values power most glab commands: `glab mr <cmd> <mr_id> --repo <repo_ref>`

## Intent Detection

Determine the user's intent before selecting a workflow. There are seven distinct workflows — **Create** creates a new MR from the current branch, **Update** updates an existing MR's description, **Read** is the lightest (just summarize), **Review** runs full specialist agents, **Fix** reviews then implements, **CI Fix** targets pipeline failures, and **Feedback** addresses reviewer comments. Default to Read when the user provides a MR URL with no strong signal indicating they want more.

| Signal in User Request | Workflow |
|------------------------|----------|
| "สร้าง MR", "create MR", "open MR", "เปิด MR", "สร้าง merge request" | **MR Create** — create a new MR from the current branch with comprehensive description |
| "อัพเดท MR", "update MR", "update description", "แก้ description", "อัพเดท description" | **MR Update** — update MR description to reflect latest changes |
| "อ่าน", "ดู", "check", "สรุป", "summary", bare URL with no action verb | **MR Read** — fetch MR info + diff, then summarize. No specialist agents. |
| "review", "ตรวจ", "ช่วย review", "review ให้หน่อย" | **MR Review** — full code/security/QA review via 3 parallel specialist agents, post findings as comment |
| "แก้", "fix", "แก้ตาม", "แก้ issue", "implement", "ทำตาม" | **MR Fix** — review first, then ask user to invoke /neo-team-claude to implement fixes |
| "fix CI", "fix pipeline", "แก้ pipeline", "pipeline fail", "CI fail", "build fail" | **MR CI Fix** — fetch failed job logs, analyze, ask user to invoke /neo-team-claude to fix |
| "address feedback", "แก้ตาม comment", "แก้ตาม feedback", "resolve threads", "ตอบ review" | **MR Feedback** — parse unresolved review threads, implement fixes, resolve |

**Decision rule:**
1. If the user's message asks to create/open a new MR (no existing MR URL) → **MR Create**
2. If the user's message asks to update MR description or mentions "อัพเดท MR" → **MR Update**
3. If the user's message mentions CI/pipeline failure → **MR CI Fix**
4. If the user's message mentions feedback/comments to address → **MR Feedback**
5. If the user's message contains a fix/แก้ keyword (not CI/feedback-specific) → **MR Fix**
6. If the user's message explicitly says "review" or "ตรวจ" → **MR Review**
7. Everything else (bare URL, "อ่าน", "ดู", "check", "สรุป", or ambiguous) → **MR Read** (lightest option, no side effects)

---

## Specialist Reference Files

This skill delegates review work to three specialist agents. Their detailed instructions live in the neo-team-claude skill's reference files. Before spawning review agents, read these files with `Read`:

| Specialist | Reference File |
|------------|---------------|
| Code Reviewer | `.agents/skills/neo-team-claude/references/code-reviewer.md` |
| Security | `.agents/skills/neo-team-claude/references/security.md` |
| QA | `.agents/skills/neo-team-claude/references/qa.md` |

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

The lightest workflow — no specialist agents, no comments posted. Just fetch MR data and present a concise summary to the user in the conversation.

```
1. Fetch MR info (JSON) and diff
2. Summarize in conversation
```

### Step 1: Fetch

```bash
glab mr view <mr_id> --repo <repo_ref> --output json
glab mr diff <mr_id> --repo <repo_ref>
```

### Step 2: Summarize

Present a concise Thai summary covering:

- **MR metadata** — title, author, status, source → target branch, pipeline status
- **What changed** — brief description of the changes (group by area: features, refactoring, CI, docs, tests)
- **Files changed** — count and key files
- **Existing comments** — if there are review comments, briefly note them

Keep it terminal-friendly and scannable. Do NOT spawn specialist agents or post any comments on the MR.

---

## MR Review Workflow

When the user asks to review a MR (or intent is detected as "review"), run this pipeline:

```
1. Fetch MR info, diff, and existing comments
2. Read & summarize existing comments (understand what's already discussed)
3. code-reviewer + security + qa → review in PARALLEL (with comment context)
4. Compose Thai comment from template
5. Post comment to the MR
```

### Step 1: Fetch

```bash
glab mr view <mr_id> --repo <repo_ref> --output json
glab mr diff <mr_id> --repo <repo_ref>
glab mr note list <mr_id> --repo <repo_ref>
```

Extract from the view output: MR title, source branch, target branch, author.

### Step 2: Read Existing Comments

Before diving into the review, read through all existing MR comments/notes fetched in Step 1. This gives crucial context — other reviewers may have already flagged issues, the author may have explained design decisions, or there may be ongoing discussions that affect how you should review. Summarize the key points:

- Issues already raised by other reviewers
- Author's explanations or decisions
- Unresolved discussions that need attention
- Resolved items (avoid duplicating feedback)

This prevents the review from repeating what's already been said and helps focus on gaps that haven't been addressed yet.

### Step 3: Parallel Review

Read the project's `CLAUDE.md` if available (for conventions). Then read the three specialist reference files listed above, and spawn all three agents at the same time — including a summary of existing comments so reviewers have full context:

```
Agent(
  subagent_type: "Code Reviewer",
  prompt: """
# Role: Code Reviewer
[paste full code-reviewer instructions from .agents/skills/neo-team-claude/references/code-reviewer.md]

---
## Project Conventions
[relevant sections from CLAUDE.md if available, else omit]

---
## Existing MR Comments
[summary of existing comments from Step 2 — issues raised, author explanations, unresolved discussions]
Do NOT repeat issues that other reviewers have already flagged unless you have additional insight to add.

---
## Task
Review the following MR diff for convention compliance.

MR: !<mr_id> — <mr_title>
Branch: <source> → <target>

## Diff
<full diff output>
"""
)

Agent(
  subagent_type: "Security Reviewer",
  prompt: """
# Role: Security Reviewer
[paste full security instructions from .agents/skills/neo-team-claude/references/security.md]

---
## Existing MR Comments
[summary of existing comments from Step 2]
Do NOT repeat security concerns that have already been raised unless you have additional findings.

---
## Task
Security review the following MR diff.

MR: !<mr_id> — <mr_title>
Branch: <source> → <target>

## Diff
<full diff output>
"""
)

Agent(
  subagent_type: "QA Reviewer",
  prompt: """
# Role: QA Reviewer
[paste full QA instructions from .agents/skills/neo-team-claude/references/qa.md]

---
## Project Conventions
[relevant sections from CLAUDE.md if available, else omit]

---
## Existing MR Comments
[summary of existing comments from Step 2]
Do NOT repeat QA concerns that have already been raised unless you have additional findings.

---
## Task
QA review the following MR diff. Focus on:
- Test coverage gaps (are new code paths tested?)
- Missing edge case tests
- Regression risks
- Acceptance criteria validation (if available)

MR: !<mr_id> — <mr_title>
Branch: <source> → <target>

## Diff
<full diff output>
"""
)
```

### Step 4: Compose Thai comment

Read [references/mr-review-template.md](references/mr-review-template.md) and fill in findings from all three agents (code-reviewer, security, qa).

### Step 5: Post

```bash
glab mr note <mr_id> --repo <repo_ref> -m "<thai_comment>"
```

If `glab` is not authenticated or fails, output the review in the conversation instead and tell the user.

---

## MR Fix Workflow

When intent is detected as "fix" (user wants to fix issues from a MR), run review first then hand off to /neo-team-claude for implementation.

```
1. Fetch MR info, diff, and existing comments          (same as MR Review Step 1)
2. Read & summarize existing comments                   (same as MR Review Step 2)
3. code-reviewer + security + qa → review in PARALLEL   (same as MR Review Step 3)
4. Compile findings into structured handoff context
5. Ask user to invoke /neo-team-claude with compiled findings
6. Post summary comment on MR (after fix is done)
```

### Steps 1-3: Same as MR Review

Run the exact same fetch → read comments → parallel review pipeline. The only difference is what happens after.

**Important for MR Fix:** When composing the agent prompts in Step 3, add this instruction to each agent:

> Categorize every finding with a severity level: **Blocker**, **Critical**, **Warning**, or **Info**. Format each finding as: `[Severity] file:line — description`. This structured output is required for the handoff to the fix pipeline.

### Step 4: Compile Findings for Handoff

After all three review agents return, compile their findings into a structured context:

```
## MR Fix Context

**MR:** !<mr_id> — <mr_title>
**Branch:** <source_branch> → <target_branch>
**Repository:** <repo_ref>

### Review Findings

#### Code Review Findings
<code_reviewer_output — full findings with severity levels>

#### Security Findings
<security_output — full findings with severity levels>

#### QA Findings
<qa_output — full findings with severity levels>

### Severity Summary
| Level | Count |
|-------|-------|
| Blocker | X |
| Critical | X |
| Warning | X |
| Info | X |

### MR Diff
<full diff for reference>
```

Only proceed to Step 5 if there are **Blocker or Critical** findings. If all findings are Warning/Info only:
1. Post the review comment on the MR (using the MR Review template from Step 4-5 of the Review workflow)
2. Inform the user in the conversation: "ไม่พบ Blocker/Critical — findings ทั้งหมดเป็น Warning/Info เท่านั้น ไม่จำเป็นต้องแก้ไขเร่งด่วน"
3. **End the workflow here.** Do NOT proceed to fix. The user can manually request fixes if desired.

### Step 5: Ask User to Invoke /neo-team-claude

Since Claude Code does not have programmatic skill invocation, ask the user to load the neo-team-claude skill:

```
กรุณาเรียก /neo-team-claude แล้ว paste context ด้านล่างนี้:

แก้ไขโค้ดตาม review findings จาก MR

<compiled findings from Step 4>

## Instructions
- Fix all Blocker and Critical findings
- Address Warning findings where practical
- Info findings are optional improvements
- The MR diff is provided for context — the code is already in the working directory
- After fixing, run existing tests to verify nothing is broken
```

/neo-team-claude will classify this as a **Bug Fix** workflow internally and run:
1. system-analyzer → understand the codebase + findings
2. developer + qa + code-reviewer → implement fixes + test + verify (3-WAY PARALLEL)
3. Remediation if needed

### Step 6: Post Summary Comment

After /neo-team-claude completes (user will come back to this conversation), post a summary comment on the MR:

```bash
glab mr note <mr_id> --repo <repo_ref> -m "<summary_comment>"
```

The comment should follow this format:

```
## 🤖 MR Fix Summary

**MR:** !<mr_id> — <mr_title>

### สิ่งที่แก้ไข
<list of fixes applied, mapped to original findings>

### สถานะ
- Blocker: X/Y แก้แล้ว
- Critical: X/Y แก้แล้ว
- Warning: X/Y แก้แล้ว

**ผลลัพธ์:** ✅ แก้ไขเสร็จ / ⚠️ แก้ไขบางส่วน (ดูรายละเอียดด้านบน)

---
*Fix โดย GitLab Skill + Neo Team · Claude Code*
```

---

## MR CI Fix Workflow

When the user wants to fix CI/pipeline failures for a MR, run this pipeline:

```
1. Fetch MR info and pipeline status
2. Identify failed jobs and fetch logs
3. Analyze failures and categorize
4. Ask user to invoke /neo-team-claude to implement fixes
5. Push fix and optionally retry pipeline
```

### Step 1: Fetch MR + Pipeline Status

```bash
glab mr view <mr_id> --repo <repo_ref> --output json
glab ci list --repo <repo_ref> --branch <source_branch>
```

Extract MR metadata and identify the latest pipeline. If the MR URL wasn't provided but the user mentions a branch or "fix pipeline", use `glab ci status` to find the current pipeline.

### Step 2: Get Failed Job Logs

```bash
# List jobs in the failed pipeline:
glab ci view <pipeline_id> --repo <repo_ref>

# Fetch logs for each failed job:
glab ci trace <job_id> --repo <repo_ref>
```

Collect the last ~100 lines of each failed job's log output. These contain the actual error messages.

### Step 3: Analyze Failures

Categorize each failure:

| Category | Examples | Typical Fix |
|----------|----------|-------------|
| Build failure | Compilation errors, missing imports, type errors | Fix source code |
| Test failure | Unit/integration/E2E test failures | Fix code or update tests |
| Lint failure | Style violations, formatting issues | Run formatter, fix violations |
| Config failure | Docker build, missing env vars, bad CI config | Fix config files |

Present a summary to the user before proceeding:

```
## CI Failure Analysis

**Pipeline:** #<pipeline_id> — <status>
**Branch:** <source_branch>

### Failed Jobs
1. [Build] job-name — CompilationError: missing import "pkg/util"
2. [Test] test-unit — FAIL TestUserCreate: expected 200, got 500

Proceed to fix?
```

### Step 4: Ask User to Invoke /neo-team-claude

Since Claude Code does not have programmatic skill invocation, ask the user to load the neo-team-claude skill:

```
กรุณาเรียก /neo-team-claude แล้ว paste context ด้านล่างนี้:

แก้ไข CI/pipeline failures จาก MR

## CI Failure Context
**MR:** !<mr_id> — <mr_title>
**Branch:** <source_branch>
**Pipeline:** #<pipeline_id>

### Failed Jobs
<for each failed job:>
- **Job:** <job_name> (stage: <stage>)
- **Category:** <Build|Test|Lint|Config>
- **Error:** <relevant error excerpt from logs>

## Instructions
- Fix all failing jobs
- Run the failing commands locally to verify fixes before pushing
- Do NOT change CI configuration unless the config itself is the problem
- If a test failure reveals a genuine bug, fix the code (not the test)
```

/neo-team-claude will classify this as a **Bug Fix** workflow and route through system-analyzer → developer → verification agents.

### Step 5: Push and Retry

After /neo-team-claude completes (user returns to this conversation):

```bash
git push origin <source_branch>
glab ci retry <pipeline_id> --repo <repo_ref>
```

Post a summary comment on the MR:

```bash
glab mr note <mr_id> --repo <repo_ref> -m "<summary>"
```

Summary format:

```
## 🤖 CI Fix Summary

**MR:** !<mr_id> — <mr_title>
**Pipeline:** #<pipeline_id>

### สิ่งที่แก้ไข
- ✅ [Build] job-name — fixed missing import
- ✅ [Test] test-unit — fixed handler returning wrong status code

### Pipeline
🔄 Retry triggered — pipeline #<new_pipeline_id>

---
*CI Fix โดย GitLab Skill + Neo Team · Claude Code*
```

---

## MR Feedback Workflow

When the user wants to address review feedback/comments on a MR, parse unresolved threads and implement fixes.

```
1. Fetch MR info, diff, and all comments/discussions
2. Filter and group unresolved feedback
3. Ask user to invoke /neo-team-claude with structured feedback
4. Push fix, post summary, and resolve threads
```

### Step 1: Fetch

```bash
glab mr view <mr_id> --repo <repo_ref> --output json
glab mr diff <mr_id> --repo <repo_ref>
glab mr note list <mr_id> --repo <repo_ref>
```

### Step 2: Parse Unresolved Feedback

From the notes/comments, identify:
- **Actionable feedback** — explicit change requests ("fix this", "add error handling", "rename to X")
- **Suggestions** — optional improvements ("consider using...", "might be better to...")
- **Questions** — need user input before acting ("why did you choose X?", "should this handle Y?")

Group by file and classify:

```
### Unresolved Feedback

#### file: src/handler.go
1. @reviewer1: "Missing error handling on line 42" — Actionable
2. @reviewer2: "Consider using context.WithTimeout" — Suggestion

#### file: src/service.go
1. @reviewer1: "N+1 query in GetUsers" — Actionable

#### Questions (need user input)
1. @reviewer1: "Should this endpoint support pagination?"
```

**If there are questions**, present them to the user before proceeding. The user's answers become part of the context for /neo-team-claude.

### Step 3: Ask User to Invoke /neo-team-claude

```
กรุณาเรียก /neo-team-claude แล้ว paste context ด้านล่างนี้:

แก้ไขโค้ดตาม review feedback จาก MR

## Feedback Context
**MR:** !<mr_id> — <mr_title>
**Branch:** <source_branch> → <target_branch>

### Actionable Feedback
<list of actionable items with file, line, reviewer, and description>

### Suggestions
<list of suggestions — implement where practical>

### User Answers to Questions
<answers from Step 2, if any>

### MR Diff
<current diff for context>

## Instructions
- Address ALL actionable feedback items
- Implement suggestions where practical; explain in summary if skipped
- Run existing tests after changes
- Do not modify code unrelated to the feedback
```

### Step 4: Push, Post Summary, and Resolve

After fixes are applied (user returns to this conversation):

```bash
git push origin <source_branch>
glab mr note <mr_id> --repo <repo_ref> -m "<summary>"
```

Summary format:

```
## 🤖 Feedback Addressed

**MR:** !<mr_id> — <mr_title>

### สิ่งที่แก้ไข
- ✅ src/handler.go:42 — เพิ่ม error handling ตาม @reviewer1
- ✅ src/service.go:15 — แก้ N+1 query ตาม @reviewer1
- ✅ src/handler.go:58 — ใช้ context.WithTimeout ตาม @reviewer2
- ⏭️ src/config.go:10 — skipped: ไม่เกี่ยวกับ scope ของ MR นี้

### ผลลัพธ์
- Actionable: X/Y แก้แล้ว
- Suggestions: X/Y implemented

---
*Feedback addressed โดย GitLab Skill + Neo Team · Claude Code*
```

---

## Common glab Operations

Use these directly via `Bash` when the user asks for something other than a full review:

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
- **glab command fails**: output the review as conversation text instead of posting, explain what failed
- **Empty diff**: note that the MR has no file changes and skip the review agents
- **Large diff (>500 lines)**: warn the user, proceed but note the review may miss details
- **Large single-line files** (minified JS, large JSON): the view tool now shows partial content — note this in the review if such files are part of the diff
