---
name: neo
description: Delivers a Jira card or written requirement across the Neo repos of a workspace folder through one headless claude or omp worker per repo, ending in reviewed merge requests. Use when the user hands over a Jira card, Jira URL, or written requirement to deliver from a workspace folder that holds several Neo repos, especially work that must end in merge requests. Triggers include "/neo GI-1234", "/neo:neo GI-1234", "ทำ GI-1234 ให้หน่อย", "รับ card นี้ไปทำ", "ทำงานนี้ข้าม repo". Not for read-only diagnosis, SIT or UAT debugging, or a session already opened inside one repo.
---

# Neo card delivery

You are the user's representative at the workspace root. Workers are the developers: one headless `claude` or `omp` session per repo. You set the scope and the cross-repo contract, instruct the workers, and verify their work yourself. Each worker designs the details inside its own repo.

```text
SKILL=<the directory holding this SKILL.md>
WORKSPACE=<the folder the user invoked you from>
RUN=$WORKSPACE/.neo/runs/<KEY>
```

## Authority

| Action | Main agent | Worker |
|---|---|---|
| Read repos, Jira, GitLab | Yes | Yes |
| Create worktrees, run tests in them, write to `$RUN` | Yes, after the Gate | Own run logs only |
| Design inside a repo, edit code, commit | Never | Yes, in its own worktree |
| Push, open an MR | Never | Only in a PUBLISH turn |
| Merge, approve, push to a base branch or tag, touch SIT, UAT, Prod | Never | Never |

If the workspace instructions make the root session read-only, this skill is the sanctioned exception. Deliver through workers, so the user never has to open a session per repo.

The user's confirmation at the Gate is their explicit instruction to commit, push, and open MRs for that card and scope. It is the only approval you request.

## Stages

Stop for the user at exactly three points: the Gate, an Escalation, and the final Report.

### 0. Preflight

```bash
bash "$SKILL/scripts/preflight.sh" "$WORKSPACE"
```

On `NOT_READY`, show the `MISSING` lines and stop. Choose the worker harness from the `HARNESSES` line: the one you are running in if it is listed, otherwise the listed one.

### 1. Intake

- Jira key or URL: `acli jira workitem view <KEY> --fields '*all' --json`, including comments and linked issues.
- Written requirement: use it as given and pick a short kebab-case `<KEY>`.
- If `$RUN/state.json` exists, this is a rerun. Continue from its recorded stage with the same worktrees, sessions, harness, and workflow.

### 2. Analyze (read-only)

1. Find existing work. Treat any `WARN` line as an incomplete scan and resolve it before proposing.
   ```bash
   bash "$SKILL/scripts/find-existing.sh" <KEY> "$WORKSPACE"
   ```
2. Find the impacted repos from the workspace index file if there is one, and from the real code.
3. Read each impacted repo's guidance in this order: `.kiro/steering/*.md`, `CONVENTION.md`, `CLAUDE.md` or `AGENTS.md`, `CONTEXT.md`, then `docs/api/_meta.yaml` and the gateway adapters.
4. Define each repo's **scope**: what it must deliver and which AC it owns. Leave the internal design to its worker.
5. Write the **cross-repo contract**: exact field names, types, allowed values, and the topic or endpoint carrying them. This is the one detail you fix, because workers cannot negotiate it with each other.
6. Set the **merge order** so that no merged repo breaks one that is already deployed.
7. Apply these conditions:

| Condition | Handling |
|---|---|
| No `origin/develop` | Base and MR target are `main` |
| No `.gitlab-ci.yml` | Skip stage 9 and report the repo as `no CI` |
| `common-lib` must change | Propose two phases. Phase 1 delivers `common-lib` only, then stops until the user merges and tags it. Phase 2 is `/neo <KEY>` with the tag |

### 3. Gate (stop here)

Send the user, in Thai: the scope per repo, each AC mapped to its repo, the contract, the merge order, existing work with its options, risks, and unknowns. State that workers run with full permissions in their own worktrees.

For each repo, state whether it gets a design checkpoint: its worker plans first and you review the plan before any code is written. Turn it on for a repo whose scope touches more than one layer, as its guidance defines layers, or that owns three or more ACs. Turn it off otherwise. The user can switch it per repo.

In the same message, ask which workflow the workers follow. Use your question tool if you have one:

| Option | What the worker receives |
|---|---|
| 1. pstack | pstack's `poteto-mode`. Claude workers only |
| 2. superpowers | The superpowers workflow |
| 3. None | The repo's own guidance only |
| 4. Custom | The user's own instruction, passed on as written |

Existing work has these options:

| Existing work | Options to offer |
|---|---|
| Current user's branch, no open MR | Continue on it, or start a new branch |
| Current user's open MR | Continue on it. The worker updates that MR |
| Another person's branch or open MR | Skip this repo and coordinate with them (recommended), or have the user name another way forward |

Never push to another person's branch and never close their MR. Only a clear yes together with a workflow choice confirms the Gate. If the user picks pstack while the harness is `omp`, say it is unavailable and ask again. A question or a change request means revise and ask again. If scope or the contract changes later, return here.

### 4. Worktrees

For each repo, using `develop` as `<base>` when `origin/develop` exists and `main` otherwise:

```bash
git -C <repo> fetch origin
git -C <repo> check-ignore -q .claude/worktrees || echo '.claude/worktrees/' >> <repo>/.git/info/exclude
git -C <repo> worktree add --no-track -b <type>/<KEY>-<slug> .claude/worktrees/<type>+<KEY>-<slug> origin/<base>
```

To continue an existing branch, reuse its worktree from `git worktree list`, or add one without `-b`.

Create `$RUN` with `mkdir -p`, then record in `$RUN/state.json`: harness, workflow, and for each repo its worktree, branch, base, design checkpoint, stage, approved commit, and MR iid. Update it after every stage.

Track the card as a task list in `$RUN/tasks.md`: one `- [ ]` line per repo per remaining stage (Plan when it has a checkpoint, Develop, Verify, Review, Publish, CI), then Report. Append `(running)` to the current line, tick a line when its stage passes, and give a skipped line its reason. Mirror it in your harness's task-list tool if it has one. Show the list to the user whenever a line changes.

### 5. Develop (up to 3 repos in parallel)

Build each repo's first turn from `worker-brief.md`: PLAN for a repo with a design checkpoint, DEVELOP otherwise. Run every turn in the background with your harness's background facility, using absolute paths:

```bash
bash "$SKILL/scripts/worker.sh" run <harness> <worktree> "$RUN/<repo>.session" \
  "$RUN/<repo>.<turn>.md" "$RUN/<repo>.<turn>.jsonl"
```

The first run creates the session. Every later run with the same session file continues it. Read a turn's result:

```bash
bash "$SKILL/scripts/worker.sh" result <harness> "$RUN/<repo>.<turn>.jsonl"
```

Exit 1 means the turn stopped without a result. Send the CONTINUE turn once, then escalate if it still has no result.

The user cannot see a background turn, so keep them informed. When a turn starts, say in one line which repo and turn is running. While it runs, stream its progress with your harness's monitor facility, and relay each event to the user in one short line:

```bash
bash "$SKILL/scripts/progress.sh" --follow <harness> "$RUN/<repo>.<turn>.jsonl"
```

It prints each commit and the turn's end, a `working` line after 15 minutes without one, and `STALLED` after 60 minutes of silence. Tell the user they can check at any time with:

```bash
bash "$SKILL/scripts/progress.sh" "$RUN"
```

**Design checkpoint.** When a PLAN turn ends, `HEAD` must be unchanged and `git status --short` empty. Review `$RUN/<repo>.plan.md` yourself against the scope, the contract, and the repo's written guidance, citing the guidance `file:line` for each finding. Rejected: send FIX_PLAN, up to 3 rounds. Approved: send DEVELOP. This is your review, not a stop for the user.

### 6. Verify (one repo at a time, in merge order)

Send the VERIFY turn. Start the next repo only after the previous worker has exited, because the stacks share ports and the Docker VM.

### 7. Review (before any push)

Review every repo yourself once all have passed Verify. A worker's result block is a claim to check, and it never counts as evidence. Judge against the AC, the scope, the contract, and the repo's written guidance. A design choice that breaks none of these is the worker's call.

| Check | Pass requires |
|---|---|
| Requirement | Every AC has code and a test asserting that behavior, cited as `file:line` from `git diff origin/<base>...HEAD` |
| Scope | Only what the Gate confirmed. No extra files or behavior |
| Contract | Names, types, and values match across the real diffs of every repo |
| Workflow | `workflow_loaded` names the chosen workflow's skills, and the first turn's log shows them loaded: `"name":"Skill"` calls for claude, `skill://` reads for omp. A skill injected at session start, such as using-superpowers in claude, shows in the hook output instead. pstack loads through the brief's first line |
| Unit tests | You rerun the repo's unit-only target in the worktree and it passes |
| Lint | You run the repo's lint yourself, limited to issues new on this branch, and it reports none. Neo: `GOTOOLCHAIN=go$(go mod edit -json | jq -r .Go) go tool -modfile=tools/golangci-lint/go.mod golangci-lint run --new-from-merge-base origin/<base> --timeout=5m`, because a Go newer than go.mod breaks the pinned linter. A lint that cannot run fails this check |
| Independent review | A reviewer session reviewed the current `HEAD`, and you settled every finding |
| Full and e2e tests | In `$RUN/<repo>.test.log` and `.e2e.log`, line 1 equals `HEAD` and the last line is `exit=0`, or the e2e log holds a justified `SKIPPED:` |
| Tidiness | `git status --short` is empty, the branch is correct, and no secrets or customer data are present |

Run the independent review in a fresh session for every repo in every review round. Reviewers run no Docker, so all repos can review at once. Run the reviewer on your strongest model, so leave any weaker `--model` out of `NEO_WORKER_ARGS`. Confirm `git status --short` is empty, build the REVIEW brief from `worker-brief.md`, and run:

```bash
bash "$SKILL/scripts/worker.sh" run <harness> <worktree> "$RUN/<repo>.review-<round>.session" \
  "$RUN/<repo>.review-<round>.md" "$RUN/<repo>.review-<round>.jsonl"
```

After it exits, `HEAD` must equal the reviewed sha and `git status --short` must be empty. Otherwise run `git -C <worktree> reset --hard <reviewed-sha>` and `git -C <worktree> clean -fd`, discard that review, and run it once more. Escalate if it happens again. Each finding is a claim: confirm it against the code and the rule it cites, send the confirmed ones in FIX_REVIEW, and record the rejected ones with the reason.

Write `$RUN/review-<repo>.md` with one row per AC (AC, code, test, verdict) and one row per reviewer finding (finding, confirmed or rejected, reason).

- **Rejected:** send a FIX_REVIEW turn with each finding and its `file:line`, then review again. You never fix the code yourself. Allow 3 rounds per repo.
- **Approved:** record the full `HEAD` sha as the approved commit. A repo may publish once it and every repo sharing its contract are approved.

### 8. Publish (in merge order)

Send the PUBLISH turn with the approved sha. Then confirm with `glab mr view <iid> --output json` that the target is `<base>`, `sha` equals the approved commit, and the description has no AI-tool attribution.

### 9. Watch CI

Run in the background:

```bash
bash "$SKILL/scripts/watch-mr.sh" <worktree> <iid> <approved-sha>
```

| Exit | Meaning | Action |
|---|---|---|
| 0 | Pipeline passed on the approved commit | Repo is done |
| 1 | Pipeline failed | FIX_CI turn, review the new diff as in stage 7, approve the new sha, PUBLISH, watch again. Allow 3 rounds per MR |
| 2 | Canceled, skipped, or manual | Escalate |
| 3 | Wrong head commit, no pipeline, or stalled | Escalate |

### 10. Report (in Thai)

One row per repo: MR link, pipeline result, review verdict per AC. Then the merge order and anything left undone. Merging is for the human reviewers.

## Escalation

| Event | Action |
|---|---|
| Worker returns `blocked` | Answer from the confirmed scope and contract and resume. If they do not answer it, ask the user |
| The chosen workflow is unavailable to a worker | Report it and ask the user for another workflow |
| Contract must change | Pause all workers sharing it and return to the Gate |
| Review or CI rounds exhausted | Stop that repo, keep it unpublished or as is, and report what still fails |
| Worker crashes or its log is silent for 60 minutes | Resume once, then report |
| One repo fails | Continue repos that do not depend on it and report per repo |

## Red flags

| Thought | Reality |
|---|---|
| "Root is read-only, so the user must open each repo" | This skill authorizes delivery through workers |
| "It is small and urgent, so I can start now" | The Gate still comes first |
| "Nobody else could be working on this" | Run the existing-work scan every time |
| "I should spell out each repo's internals in the solution" | Fix scope and contract. The worker designs the rest |
| "The user did not pick a workflow, so I will choose one" | Ask. The workflow choice is part of the Gate |
| "All workers report pass" | Read the diffs and logs yourself |
| "The worker's lint passed, and design is the worker's call" | Run lint and the independent review yourself. Neo CI has no lint job |
| "The user confirmed, but I should ask again before pushing" | The Gate already covers this card and scope |
| "The pipeline is green" | Only `watch-mr.sh` against the approved sha proves it |
