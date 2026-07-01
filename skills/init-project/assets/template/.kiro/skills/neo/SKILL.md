---
name: neo
description: >-
  Entry point for the **neo** multi-agent software development workflow.
  Task-aware **phase-based** router — no fixed pipeline. Parses any task in natural
  language and hands off to the `neo-orchestrator` subagent, which looks up the
  Phase Map to dispatch only the specialists (Business Analyst, Architect, QA,
  Developer, Code Reviewer, Security, System Analyzer, Librarian) for the phases the task
  actually touches (Ingest / Spec / Design / TestSpec / Build / Verify / Diagnose).
  The Librarian ingests external sources (JIRA / Confluence / image / verbal) once
  into docs/knowledge/ for every role to reuse.
  Supports single-role calls ("create AC for revoke" / "สร้าง AC ของ revoke") and multi-role tasks
  ("add endpoint POST /accounts" / "เพิ่ม endpoint POST /accounts" → Spec → Design → TestSpec → Build → Verify).
  Also the single entry point for GitLab MR work — **creating an MR** (create MR / สร้าง MR)
  and **reviewing an MR** (review MR / ตรวจ MR; with a JIRA card → AC/TC compliance,
  without → code + security + regression), handled by the in-skill MR brain that
  runs the `glab` command set (see the `gitlab` skill). It works on the user's
  current branch and never commits, pushes, or edits source files. Trigger phrases:
  "neo", "/neo", "use the team", "ใช้ทีม", "สั่งทีม", "start a new requirement",
  "implement {ticket}", "design the API for {usecase}", "write test cases for
  {usecase}", "review code", "fix bug", "refactor", "ingest {source}", "remember this" /
  "จำเรื่องนี้ไว้" (into the knowledge base), "continue {ticket}",
  "/neo continue {ticket}", "ทำ {ticket} ต่อ", "resume {ticket}", "สร้าง MR", "create MR",
  "review MR", "ตรวจ MR", or any GitLab MR URL paired with "review", "fix", or
  "address feedback".
metadata:
  version: "4.0-kiro"
  bundles: "9 custom subagents (neo-orchestrator + 8 specialists), 12 references (incl. 9 templates under references/templates/) + 6 shared rule files (shared/), and the shared interactive-HTML design system (assets/, incl. lint.py + docverify.py + apispeccheck.py + agents_to_cli.py)"
---

# Neo Skill

`/neo <your request>` is the **single entry point** to the neo multi-agent workflow. The skill hands off to the `neo-orchestrator` subagent, which owns every Phase Map lookup, plan/checkpoint UX, and inline doc verification.

> **🛑 HARD-GATE — Mandatory before any action**
>
> When this skill activates, the main agent MUST complete the **Mandatory Action** and enforce the **Refusal Guards** continuously.
>
> ### Mandatory Action (in order)
>
> 1. **Detect MR intent FIRST.** If the task is **MR Create** or **MR Review** (see § MR Workflows for create-vs-review and card-vs-no-card detection), run the in-skill **MR brain** in the main loop — do NOT hand it to neo-orchestrator (the orchestrator subagent cannot run `glab`). A bare MR URL with no verb is ambiguous → ask the user (a quick read vs a full review); never default to a heavy review. For every **non-MR** task, continue to step 2.
> 2. **Check `neo-orchestrator` is installed** (at `~/.kiro/agents/neo-orchestrator.md` or `<workspace>/.kiro/agents/neo-orchestrator.md`). If not, return the onboarding message (see § Onboarding requirement) and stop.
> 3. **Invoke `neo-orchestrator`** with the user's request VERBATIM — no summarization, no prefix, no added context. **Kiro IDE:** `Use the neo-orchestrator subagent to <user's task verbatim>` (or `/neo-orchestrator <user's task verbatim>`). **kiro-cli:** call the `use_subagent` tool with `agent_name: "neo-orchestrator"` and the task verbatim in `query` — on kiro-cli the IDE sentence is inert plain text and dispatches nothing.
> 4. **Wait for the orchestrator to return.** It owns plan, checkpoints, dispatch, and final summary. Relay the output to the user.
>
> ### Refusal Guards (continuous — never violate, even if it seems helpful)
>
> **Scope:** Guards 4–8 govern the **non-MR delegation path** (the hand-off to neo-orchestrator). On the **MR path** (§ MR Workflows) the skill intentionally DOES classify the MR mode, read `docs/design/INDEX.md` (8b only), spawn `code-reviewer ∥ security ∥ qa`, and run `glab` — sanctioned for MR create/review ONLY, nowhere else.
>
> 4. **Do NOT pre-process the user's task.** No summarizing, no rewording, no adding "context for clarity", no inserting design-doc summaries, no inserting file paths "to implement", no inserting code snippets, no step-by-step instructions for the orchestrator. The orchestrator reads the Phase Map and figures everything out itself. Pre-processing corrupts routing and tempts the orchestrator to _execute_ instructions instead of _dispatching_ to a specialist — this is the #1 cause of orchestrator implementing work it should have delegated.
> 5. **Do NOT pre-fetch project context.** Do not read `.kiro/steering/*.md`, `docs/design/INDEX.md`, AC documents, system design docs, or any project file before dispatching. The orchestrator reads what it needs in its own Mandatory FIRST Reads.
> 6. **Do NOT classify the task.** Do not pre-assign roles, do not match Phase Map rows, do not decide which specialists to involve. The Phase Map lookup is the orchestrator's GATE 3 — let it run.
> 7. **Do NOT spawn specialist subagents directly** (BA, Architect, QA, Developer, Code Reviewer, Security, System Analyzer, Librarian) from the skill. The orchestrator is the only routing path. The user MAY invoke specialists directly via `/business-analyst`, `/qa`, etc. (see § Direct specialist invocation) — but the skill itself never does.
> 8. **Do NOT touch git state or modify files** *(non-MR path).* Outside § MR Workflows this skill is pure routing — branches, commits, and pushes stay user-owned via `/commit`. On the MR path the ONLY sanctioned git/glab surface is read-only MR review (fetch + post a findings comment) and MR create (open an MR from the current branch); the skill never edits source files and never commits/pushes/branches.

## Architecture

This skill is the bundled entry point. It ships with:

- **`agents/`** — 9 custom Kiro subagents installed by `setup.sh` into `~/.kiro/agents/<name>.md` (plus a generated `<name>.json` per agent for kiro-cli, via `assets/agents_to_cli.py`). The orchestrator + 8 specialists each get their own isolated context window when invoked.
- **`references/`** — 12 references loaded by agents on demand via the `read` tool from `~/.kiro/skills/neo/references/<name>.md`. Notable: `phase-map.md` (routing source of truth), `references/templates/` (5 document templates incl. `api-spec.md` + the task-file template `task-file-template.md` + the knowledge-file template `knowledge-file-template.md` + the MR review-comment template `mr-review-template.md` + the E2E guide), `html-output.md` (interactive-HTML design system guide for BA/Architect/QA), 1 CLI cheatsheet. Plus `references/shared/` — 6 single-source-of-truth rule files (`jira-ref.md`, `preamble.md`, `ac-status.md`, `task-tracking.md`, `knowledge-base.md`, `convention-grounding.md`) that every specialist reads first.
- **`assets/`** — the shared interactive-HTML design system (CSS/JS web components, `_shell.html`, `lint.py` (per-file structural linter), `docverify.py` (cross-document reference linter), `scaffold.sh`) plus `apispeccheck.py` (the `docs/api/` api-spec L1 validator) and `agents_to_cli.py` (the `.md`→`.json` agent converter for kiro-cli), installed to `~/.kiro/skills/neo/assets/`. BA/Architect/QA stamp the design system into a project's `docs/design/` to render design docs as interactive HTML. See `references/html-output.md`.

The eight utility skills (`brainstorm`, `gitlab`, `atlassian`, `openapi-doc`, `open-collection`, `confluence-api-doc`, `commit`, `improve`) live as separate top-level skills under `~/.kiro/skills/` — they are reusable outside the neo workflow.

## How invocation works

```
User → /neo <task>               (or any matching trigger phrase)
         │
         ▼
  Kiro main agent  (this skill activates)
         │
         ├─ MR intent? (create / review an MR)
         │     └─ YES → run the in-skill MR brain (§ MR Workflows):
         │              fetch via glab, spawn Code Reviewer ∥ Security ∥ QA,
         │              compose + post the review comment / create the MR
         │
         ▼ (non-MR)
  Delegate to `neo-orchestrator` subagent
         │
         ▼
  Orchestrator reads phase-map.md, picks the touched phases,
  shows a plan (if 2+ phases), then dispatches specialists in order
  (4 checkpoints: CP1 plan · CP2 BA5-intent · CP3 pre-Build · CP-final)
         │
         ▼
  Final summary returned to user — deliverable file paths on the
  current branch. To ship, the user runs /commit; an MR can be opened
  with /neo create MR (สร้าง MR) or directly via /gitlab.
```

## What this skill must do

**MR create/review is the exception** — handle it in-skill via § MR Workflows (do not delegate it to the orchestrator). For every **other** task, immediately delegate the user's task to the `neo-orchestrator` subagent.

**Kiro IDE** — use the subagent invocation pattern (or the slash form `/neo-orchestrator <user's task verbatim>`):

```
Use the neo-orchestrator subagent to <user's task verbatim>
```

**kiro-cli** — the sentence above is inert plain text here; instead call the `use_subagent` tool:

```
use_subagent(agent_name="neo-orchestrator", query="<user's task verbatim>")
```

Pass the user's full request verbatim — do not summarize, do not pre-classify, do not pre-fetch project context. The orchestrator handles all of that itself (it reads `.kiro/steering/*.md`, looks up the Phase Map, routes the task, etc.).

### If the user gave no arguments

If `/neo` was invoked with no task description, ask exactly one question first:

> "What would you like neo to do?"

Then delegate to the orchestrator with the user's answer.

## MR Workflows

You (the neo skill, running in the **main loop**) are the single entry point for GitLab MR work — **creating** an MR and **reviewing** an MR. You run the `glab` command set yourself via Bash, using the **`gitlab` skill** (`~/.kiro/skills/gitlab/SKILL.md`) as the canonical reference for URL parsing, the glab command set, MR-creation defaults, and error handling. You orchestrate the thinking (mode decision, specialist dispatch, comment composition) and spawn `code-reviewer ∥ security ∥ qa` as Kiro subagents (the same specialists the orchestrator uses). You never edit source files; MR Review posts findings only. (The orchestrator subagent cannot do any of this — its GATE 1 bans `shell` and Kiro has no skill-invocation tool — which is why the MR brain lives here.)

### Intent + mode detection

1. **Create vs review.** "สร้าง MR / create MR / open MR" (no existing MR URL, intent to open one) → **MR Create**. "review MR / ตรวจ MR / ช่วย review" + an MR URL → **MR Review**. A bare MR URL with no verb is ambiguous between a quick read and a review — ask the user which they want (do NOT default to a heavy review; a plain read is the `gitlab` skill's MR Read, which the user can trigger directly).
2. **Review mode — card or no card.** If the task names a JIRA card ID (format `ABC-123`) → **mode 8b (with card)**. If no card is named → **mode 8a (no card)**. If unsure whether a card applies (e.g., "review per the card" / "review ตามการ์ด" but no ID) → ask the user; never guess a card ID (Never Guess + `~/.kiro/skills/neo/references/shared/jira-ref.md`).

### MR Create flow (single delegation, no plan UI)

1. Run the `gitlab` skill's **MR Create** command set via Bash (`~/.kiro/skills/gitlab/SKILL.md` § MR Create): verify the current branch + uncommitted changes, push if needed, analyze the branch diff, generate a comprehensive description, run `glab mr create --remove-source-branch --squash-before-merge`.
2. If the user named a JIRA card, add a `JIRA: <ID>` line to the description.
3. Report the MR URL. (Create is a delegation, not a specialist dispatch — no plan table.)

### MR Review flow (modes 8a / 8b — read-only; posts findings; never edits code)

1. **(8b only) Resolve the usecase docs.** Read `docs/design/INDEX.md`, match the card/MR to a usecase, and confirm the usecase's `acceptance-criteria.html` carries a `JIRA Ref:` equal to the card. Collect the paths: `acceptance-criteria.html`, `test-cases.html`, `traceability.html`. If the card maps to **no** usecase, **multiple** usecases, or the match is unclear → **ask the user** (Never Guess). Local docs are the only source — do NOT fetch the live JIRA card.
2. **Fetch the MR.** Run the `gitlab` MR-Read command set via Bash (`glab mr view <id> --repo <ref> --output json`, `glab mr diff`, `glab mr note list`) to get the MR JSON (title, source→target branch, author), the diff, and the existing notes. Summarize the existing comments so reviewers don't repeat them.
3. **Plan confirmation (3 roles).** Present the plan (Code Reviewer ∥ Security ∥ QA, with the mode noted) and ask Confirm / Edit / Cancel as a plain-text numbered list (Kiro has no `AskUserQuestion` tool).
4. **Dispatch the read-only review group in parallel** (one batch): **Code Reviewer ∥ Security ∥ QA**.
   - **Kiro IDE:** three `Use the <name> subagent to …` sentences in ONE message.
   - **kiro-cli:** three `use_subagent` calls in one turn (`agent_name: "code-reviewer" | "security" | "qa"`). Parallel cap is 4 → 3 is safe.
   - Give every agent the diff + the existing-comments summary (instruct: do not repeat issues already raised).
   - **QA** additionally gets the **MR-review-mode** flag (`8a regression` / `8b compliance`) and, for 8b, the three doc paths + the card ID. QA runs read-only — see `~/.kiro/agents/qa.md` § MR Review Mode. For 8b, instruct QA to return the **AC/TC compliance table**.
5. **One combined checkpoint** after all three return. No checkpoint between them.
6. **Compose the comment.** Read `~/.kiro/skills/neo/references/templates/mr-review-template.md` and fill it from the three agents' findings (table-first). For 8b, include the AC/TC Compliance section from QA's table — the mismatch column must be specific and actionable so an AI can act on it.
7. **Post the comment.** Run `glab mr note <id> --repo <ref> -m "<composed text>"` (the `gitlab` skill's Post-a-Comment command). If glab is unauthenticated/fails, surface the comment text to the user to post manually.
8. **Finalize.** Output a short recap (the review group's verdicts + whether the comment was posted) + a Final Summary.

**MR Review does NOT auto-fix.** It posts findings only. If the user wants the findings fixed, they re-invoke `/neo` with a fix request, which routes through the Modify-Code / Bug-Fix phase rows (phase-map.md) and the Dev Loop — handled by the orchestrator.

## What this skill must NOT do

- **(Non-MR tasks)** Do not route the task yourself — the orchestrator owns Phase Map lookup. (MR create/review is the documented exception — see § MR Workflows.)
- **(Non-MR tasks)** Do not read `.kiro/steering/*.md`, `INDEX.md`, or any project doc — the orchestrator handles that. (8b MR review reads `INDEX.md` + the usecase docs — see § MR Workflows.)
- **(Non-MR tasks)** Do not spawn specialist subagents directly (BA, Architect, QA, etc.) — the orchestrator is the only entry point for them. (MR review spawns Code Reviewer ∥ Security ∥ QA itself — see § MR Workflows.)
- Do not commit, push, or create branches (still `/commit`'s job), and do not edit source files. **MR create + review-comment posting ARE in-scope** via § MR Workflows.
- Outside § MR Workflows, this skill is pure routing — modify no file.

## Onboarding requirement

The `neo-orchestrator` subagent must be installed under `~/.kiro/agents/neo-orchestrator.md` (global) or `<workspace>/.kiro/agents/neo-orchestrator.md` (workspace). If the orchestrator subagent is not available, return this message to the user:

> "The `neo-orchestrator` subagent is not installed. From the neo-power repo, run `./setup.sh --global` to install 9 subagents and 7 skills, then retry `/neo`."

Do not try to inline the orchestrator's behavior — it depends on the full agent prompt including the Phase Map lookup and the inline doc-verification model.

## When to use vs. skip

| Situation                                                     | Use `/neo`?                                                                |
| ------------------------------------------------------------- | -------------------------------------------------------------------------- |
| New feature ("add a new endpoint", "start a new requirement") | ✅                                                                         |
| Bug fix that spans multiple files or has unclear root cause   | ✅                                                                         |
| Cross-module refactor                                         | ✅                                                                         |
| MR review (`review MR <url>`) — Code Reviewer ∥ Security ∥ QA; +AC/TC compliance with a JIRA card | ✅ — handled in-skill (§ MR Workflows) |
| Create an MR (`create MR` / `สร้าง MR`)                                     | ✅ — handled in-skill (§ MR Workflows)                                     |
| Single-role focused doc edit ("create AC" / "สร้าง AC", "gen test cases")   | ✅ — orchestrator runs the single phase and propagates only if user opts in |
| Single-file typo fix                                          | ❌ — answer directly                                                       |
| Quick question about the codebase                             | ❌                                                                         |
| Pure research with no code change                             | ❌                                                                         |
| Editing this skill or any neo-power file                      | ❌                                                                         |

## Direct specialist invocation (advanced)

For focused single-doc edits, the user may invoke a specialist subagent directly without going through the orchestrator:

```
/business-analyst update AC-007 to add audit logging
/qa add a test case for the new error path
/architect document the new caching layer
```

This bypasses the orchestrator's Phase Map lookup and checkpoint UX. Specialists still self-enforce their gates (read `shared/preamble.md`, read steering, read the relevant template). For multi-phase propagation, route through `/neo` instead.
