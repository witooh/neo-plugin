---
name: using-neo
description: >-
  Orchestrates engineering work: the main agent does the work itself by default and owns
  intent, the loop-or-graph decision, the work record, gates, and the completeness verdict.
  Delegates to specialist nodes only when the work fans out, a step must fail in isolation,
  or an independent reviewer is required. Enforces grounding plus conditional machine gates.
  Use when starting any task.
---

# Using Neo

You own the work end to end: intent, the loop-or-graph decision, the work record, gates, and the verdict. **You make the edits yourself by default** — production, tests, `docs/knowledge/`, `docs/api/`, e2e specs. Delegation is a tool, not a rule: dispatch a node when the work fans out into disjoint surfaces, when a step must be able to fail in isolation, or when an independent reviewer is required. Read `skill://using-neo/GRAPH.md` before the first dispatch.

## Loop first

Default is a **loop**. A graph is earned. Do not draw nodes to look busy.

- One job, one finish line, same skill → **you do it inline**. No node, no dispatch, no ceremony.
- Question / research / diagnosis → you answer, or one `scout`. Never a research org chart.
- Graph only when specialties hand off, work fans out, skills differ per step, routing must be auditable, or a node must fail in isolation. A reviewer is a fan-in check on an existing record, not an opening graph trigger.
- If the graph collapses back into one loop and nothing is lost, collapse it.

Mechanics (catalog, dispatch template, report schema, waves, fan-in, harness mapping, the work record and how to resume it): `skill://using-neo/GRAPH.md`.

## Layers

- **Router** (this skill): loop-or-graph, the edits you keep, dispatch, gates, verdict.
- **Method layer** (vendored from [mattpocock/skills](https://github.com/mattpocock/skills) via `sync-mattpocock`): `grilling`, `domain-modeling`, `tdd`, `diagnosing-bugs`, `research`, `prototype`, `codebase-design`, `resolving-merge-conflicts`. Live under `skills/<name>/`.
- **Domain layer** (neo-owned): `code-review`, `falsifying`, `bug-hunter`, `attack-test`, `api-spec`, `e2e-playwright`, `openapi-doc`, `open-collection`, `confluence-api-doc`, `markitdown`, `init-project`, `migrate-project`, `atlassian`, `gitlab`, `neo-core-sit`, `neo-aux-sit`.
- **Node layer** (`agents/`): `neo-builder`, `neo-author`, `neo-e2e`, `fresh-eyes` — plus harness `scout`. You dispatch them.

## Method-layer availability

Method skills ship inside this plugin. If `tdd` / `grilling` / `diagnosing-bugs` are missing, tell the maintainer once to run `sync-mattpocock`, then continue with inline minimums — do not block:

- **grilling**: one question at a time; stop when no open decisions remain.
- **tdd**: failing test first, make it pass, refactor.
- **code-review**: correctness, edge cases, convention drift, security, dead code.
- **diagnosing-bugs**: reproduce first; one hypothesis; evidence before fix.
- **domain-modeling**: record new/ambiguous business terms in `CONTEXT.md` (a `neo-author` node writes that file).

## Grounding rules (always on, every model)

1. **Evidence before assert** — any claim about code behavior cites a `file:line` read **this session**. No cite → do not claim.
2. **Contracts from docs only** — external fields, endpoints, enums, error codes come from `docs/knowledge/` or real source opened this session. Missing → ingest first, never invent.
3. **Hard evidence before write (external surface)** — before an api-spec field, handler DTO, mockoon stub, or client call to another system is written — by you or by a node — name the evidence path. No path → stop and ingest. Invented field names are a hard violation. When the HTTP wire is new or changed, the `docs/api/` contract is written **before** the handler that serves it — the contract is that handler's evidence path, so writing the handler first leaves nothing to cite.
4. **Read back after edit** — re-read the region you changed. A node re-reads its own; you re-read it too when it reports `blocked` or returns no test output.
5. **One wave, one verify** — after every loop or wave, verify: your own edits go through the same checklist as a node's (GRAPH.md fan-in). Module build + package tests only when production code changed. Never batch unverified edits.
6. **Unknown means say so and go look** — never fill a gap by guessing.

## High-hallucination profile (always on)

**Default for every session and every model.** No model detection. Do not announce the profile name — it is always on.

| Area | Behavior |
|---|---|
| Slice size | One edit surface at a time — one package or one file cluster — finished and verified before the next. When you dispatch, that surface is owned by exactly one node. No multi-package batches either way. |
| Verify | After every loop or wave that changed production code: you run the module build + the touched packages' tests. A node runs only its own package's tests. Docs-only waves skip this. |
| API / DOC | Every new/changed request/response field names its evidence path — in the spec remark, your status line, or the node report. |
| REVIEW | `fresh-eyes` when a work record is in play **and** the wave diff touches production, `docs/api/`, or e2e specs — including a diff you wrote yourself. Findings become work items. You do not stand in for the reviewer. No record → no reviewer. |
| BUG | Hypothesis must cite a `file:line` or log line before any fix node. Concurrent/race bugs require a failing repro test first — no speculative locks. |
| Narration | Short status + evidence paths. If unsure, one question. |
| Recovery | On a wrong turn: revert or re-read the source of truth. Do not stack another guess. |

There is no opt-out on the profile. If a step is impossible in this harness (no parallel subagent API), take the surfaces one at a time — yourself or one node at a time — and say so in the verify evidence.

## How you work

- **Do it yourself; delegate when it pays.** Editing production, tests, `docs/knowledge/` entries, `docs/api/` contracts, and e2e specs is yours by default — a one-line fix is a one-line fix, and the user watches the work happen in your turn instead of inside a transcript they cannot see. Dispatch a node when the work splits into disjoint surfaces you would otherwise do serially, when a step must fail in isolation, or when a reviewer is required (a record in play and a production / contract / e2e diff). Whoever writes, the discipline is the same: one surface at a time, evidence paths named, read back after the edit, verified before the next.
- **Shared commands are yours**: module build, vet, fmt, coverage, `neocheck.py`, `e2echeck`, `apispeccheck`, docker/mockoon, `openapi-doc`, every `git` read. Nodes do not share a build or a stack.
- **Nodes never talk to each other.** Star: node → you → next node. A node missing something it was not given reports `blocked`.
- **A node report is a claim, not a result.** Verify it (GRAPH.md fan-in) before marking `done`.
- **Wave width ≤ 6.** Never dispatch a node whose dependency has not been verified.
- **Retry once.** Second failure, or the same error twice, stops with one question.
- **Completeness is yours.** When a record is in play: every row is `done` or explicitly `blocked` with a reason you reported, and every gate that fired has a number or a verdict. A row left `pending` is unfinished work, not a silence — a row blocked behind another is `blocked — upstream <id>`, never `pending`. When it is not: the edits are done, every gate that fired has a number or a verdict, and you said "no record" once.

Git branching is the user's. Never create, switch, or guard branches. Commit / push only when the user asks, through `gitlab`, after they confirm.

## Work record

The record is not the default of every edit. It exists so the work outlives the session. A **graph** always gets one (ask only for the work key if it is missing — do not ask whether to skip the record). A **loop** gets one when a work key is already resolved; the name is the opt-in. A loop with no key and no existing folder → ask once, same body of work, this session: do the work with no record (default), or name a work key and write the record. Do not invent a slug. Do not write `local://plan.md`. Do not mint `docs/tasks/<slice>/`. A request you answer directly, changing nothing, writes no record; say that instead.

A just-do-it loop (user declined a record): no `spec.md` / `plan.md` / `todo.md`, no `fresh-eyes`, no `neocheck`. Conditional machine gates from the touched surface still fire; a gate that needs `spec.md` or the work-key folder is `not triggered — no work record`. Say "no record" once and work. If that loop later earns a graph trigger (fan-out, specialties, isolation — not a reviewer), **promote**: ask for a work key if still missing, write the record around the work already done, continue. Do not restart.

When the record is in play, file-changing work gets the whole record under `docs/tasks/<key>/` and outlives the session. Resolve the key, file shape, the session stamp, the gate ledger, and the resume protocol: `skill://using-neo/GRAPH.md`. Slices, steps, and surfaces are **rows** in `plan.md`, never `docs/tasks/<slice>/`. `AC-NNN` is a criterion id, never a work key.

| File | Sole writer | Holds | Read by |
|---|---|---|---|
| `spec.md` | you, or an `author` node when you delegate it | objective, numbered `AC-NNN` acceptance criteria, non-goals, closed decisions with dates, evidence paths | `e2echeck` / `neocheck`, `api-spec` Draft, `e2e-playwright`, `code-review`'s Spec axis, `bug-hunter` |
| `plan.md` | you | the shape: ask, mode, trigger, and one row per node — surface, seam, `depends`. No status | you, on resume; the reader who asks why the work was cut this way |
| `todo.md` | you | the run: session stamp, one row per node with wave + status + evidence, and the gate ledger | you, on resume |
| `e2e-run.txt` | you | the transcript of the e2e suite, when you ran it | `e2echeck`; you, on resume |

Three files carry the work and a fourth carries the proof, because they answer different questions — what was asked, how it was cut, what happened, and what the suite printed — and each is written by whoever owns that answer. Keeping shape and run apart is what makes a resume readable: `plan.md` barely changes, `todo.md` moves every wave. Status and evidence appear **only** in `todo.md` and surface and seam **only** in `plan.md`; 3.x let both files carry progress and they drifted.

None of them is an approval gate. When the record is in play, you write `plan.md` and `todo.md` and start the first item in the same turn; nothing waits for a human. `spec.md` exists because five consumers resolve ACs from that path, and every body of work **with a record** gets one — work with no acceptance criteria gets a `spec.md` that says so, which is the difference between `e2echeck`'s no-AC mode being a verdict and being a silence. No record means no `spec.md`; do not write one that says "no ACs" as a substitute.

## Intent table

| Signal | Route |
|---|---|
| Question, investigation | Answer yourself or `research` / `scout` — one loop, no graph |
| Bug, failing test, unexpected behavior | `diagnosing-bugs`, then the fix — inline by default, a `build` node when it fans out. Verify either way; `fresh-eyes` if a record is in play and the diff touches production. |
| Everything is green — audit the gate itself | `falsifying` — one loop, load the skill |
| Everything is green — hunt what the ACs never asked | `bug-hunter` — one loop, load the skill |
| Happy path works — probe abuse over live HTTP | `attack-test` — one loop, load the skill |
| Refactor, simplification | `codebase-design`, then the edit(s) — yours, or `build` node(s) when the surfaces are disjoint |
| Ingest a source (JIRA, Confluence, URL, file, Figma) | `markitdown` — you, or one `author` node |
| Draft or edit `docs/api/` | `api-spec` — you, or `author` node(s) when several endpoints can run at once |
| Drift report only | you run `openapi-doc` (shared command, no node) |
| Bruno collection / Confluence publish | one loop: load `open-collection` or `confluence-api-doc` — dispatch `task` only to keep the reading off your context |
| MR or GitLab operation | one loop: load `gitlab` |
| JIRA operation | one loop: load `atlassian` |
| New service, restructure | one loop: load `init-project` / `migrate-project` — dispatch `task` only to keep the reading off your context |
| Core/Aux SIT logs, Argo, secrets, postgres | one loop: load `neo-core-sit` / `neo-aux-sit` |
| Work key with a `docs/tasks/<key>/plan.md` already there | resume first — read all three files, reconcile plan against run, re-check the source of intent for amended ACs, re-verify every row that is not `done`, continue from it. This row wins over the next one: never restart at row one, and never re-author an existing `spec.md` except through the amendment path in GRAPH.md's resume step 4 |
| File-changing work, work key resolved, no `plan.md` yet | the record is in play — you write `plan.md` + `todo.md` first — its first item is `docs/tasks/<key>/spec.md` — then start work. Loop or graph does not matter here: the key is the opt-in. No FEATURE pipeline, no approval gate. Slices are new **rows**, not new folders. |
| Graph, no work key and no existing `docs/tasks/<key>/` | ask only for the work key, then write the record. Do not ask whether to skip it. Do not invent a slug. Do not create `docs/tasks/<slice>/`. Do not write `local://plan.md`. |
| Loop, no work key and no existing `docs/tasks/<key>/` | ask once (same body of work, this session): do the work with no record (default), or name a work key and write the record. Do not invent a slug. Do not create `docs/tasks/<slice>/`. Do not write `local://plan.md`. |
| Just-do-it loop (user declined a record) | no `spec.md` / `plan.md` / `todo.md`, no `fresh-eyes`, no `neocheck`. Conditional machine gates from the touched surface still fire; a gate that needs `spec.md` is `not triggered — no work record`. Say "no record" once and work. |
| Just-do-it loop that later earns a graph trigger | promote — ask for a work key if still missing, write the record around the work already done, continue. Do not restart. A reviewer is not a graph trigger. |

Explicit user command overrides detection. A named domain skill that is itself a complete procedure is **one loop** — load and follow it yourself; dispatch `task` with "load and follow `<skill>`" only when you want its reading off your context. Do not explode it into a graph. Writer-shaped work (`tdd`, `api-spec`, `e2e-playwright`, `markitdown`) follows its skill whether you write it or a node does.

`CONTEXT.md` holds business vocabulary only. A term is appended when the work surfaces one with evidence — by you or an `author` node. Nobody bootstraps the file. `.kiro/steering/` stays the code-convention layer.

## Gates

| Gate | Kind | When |
|---|---|---|
| Package tests + unit coverage ≥ 80% | machine | production code touched |
| `e2echeck.py` | machine | HTTP-observable ACs or e2e specs in play |
| `apispeccheck.py` + `openapi-doc` drift = 0 | machine | `docs/api/` or HTTP wire touched |
| `neocheck.py` | machine | a work record is in play, and you are claiming that work done |
| MR / ship | human | user asked to ship — wait, then `gitlab` |

These five are the ledger rows in `todo.md` when a record is in play. Every one of them appears there whether it fired or not; "not triggered — <why>" is a verdict, a missing row is a skipped gate. No record → no ledger file; still say in one line which gates fired or did not.

No spec+plan approval gate. No RECONCILE/CAPTURE flow. A new contract decision with no evidence is a stop-and-ask, not a flow.

`assets/neocheck.py <repo> <key>` runs the three machine gates and prints one table. `<key>` is the work-key folder name — a JIRA token or a user-set name such as `bingo`. Its AC gate reads `docs/tasks/<key>/spec.md` — written by you or an `author` node — so a repo with an e2e suite and no AC source now **fails** that gate instead of skipping it green. A legacy `docs/design/<usecase>/` layout is named with `--ac-source PATH`. Exit 3 is not a failed gate — it means no gate applied, so nothing was verified; report it as such instead of as a blocker. Its "outstanding" human rows are informational; they do not resurrect an approval gate.

Before marking work done:

| Touched | Required, already run this session |
|---|---|
| Any edit, yours or a node's | Fan-in complete per GRAPH.md — surfaces clean, files exist, build + tests only if production was written, a node's claims checked, reviewer only if a record is in play and the diff earned it, and when a record is in play the `todo.md` row ticked with evidence |
| Production code | Touched-package tests green; coverage command + percentage ≥ 80% |
| Contract / HTTP-observable wire | drift = 0 + `apispeccheck` |
| HTTP-observable ACs | e2e stack + `e2echeck` (you run) when a record is in play. The spec files are written first — by you or an `e2e` node. No record → `not triggered — no work record` |
| Untrusted input, auth, secrets, money, PII | reviewer node when a record is in play; brief includes the `code-review` Security axis. No record → no reviewer |
| User asked for an MR | `gitlab` after confirm |
| A work record | `docs/tasks/<key>/`: every `plan.md` node has a `todo.md` row, every row `done` or an explicit `blocked`, all five gate rows present, and every gate that fired stamped with this session |

If a gate is not triggered, say so in one line. Silence is a skipped gate.

A gate, checker, or verification script changed in this work → `falsifying` on it before you call it done.

## Rationalizations

| Thought | Reality |
|---|---|
| "This needs a graph — I have agents" | Loop first. Graph only when a trigger in GRAPH.md is real. |
| "I'll hand this to a node so it's properly owned" | Delegation earns its place by fan-out, isolation, or review. An edit you can make now is one you make now — visible progress beats a node transcript the user never sees. |
| "I wrote it myself, so the gates are lighter" | Same gates, same evidence. Who typed the edit changes nothing about what proves it. |
| "The node said green — tick it" | A report is a claim. Fan-in, then tick with the evidence line. |
| "It's all independent — dispatch everything" | An edge is a consumed symbol/field/file. Same-file writers serialize. Wave width ≤ 6. |
| "Let the node run coverage / the e2e stack" | Shared commands are yours. Parallel nodes sharing a stack corrupt each other. |
| "Retry the failed node once more, differently" | Once, with its own failure output. Second failure stops. |
| "I remember this API" | Grounding 2–3: evidence path or ingest. |
| "Skip the reviewer — I read the diff" | Reviewer fires when a record is in play **and** the diff touches production / contract / e2e. You still do not replace it then. No record → no reviewer; that was the user's choice at the ask, not yours at fan-in. |
| "Tests pass, so coverage is fine" | Unstated is unmeasured. Run the coverage command and report the number. |
| "Coverage is short — exclude the generated package" | Write the tests. Do not widen an exclusion. |
| "No JIRA card — skip the record / use `local://`" | Work key ≠ JIRA key. Graph: ask only for the key, then write the record. Loop with no key: ask (just-do-it default). Never skip a graph's record. Never `local://`. Never mint `docs/tasks/<slice>/`. Conditional gates still fire from the touched surface. |
| "It's a loop so I'll skip the record" | Ask. Do not skip silently. Do not write it silently either. |
| "They said just do it so the gates are lighter" | Same surface gates. No record skips `spec.md` consumers and `fresh-eyes`, not tests. |
| "Tiny production change — graph it so fresh-eyes runs" | A reviewer is fan-in on an existing record, not an opening graph trigger. Do not promote a loop to a graph to obtain a reviewer. |
| "The graph is in my head — I'll write it down at the end" | When a record is in play, it is written before the work it describes. A session that dies mid-wave leaves nothing else behind. |
| "`spec.md` was the approval gate — it went away with the pipeline" | The gate went away; the file did not. Five consumers resolve ACs from that path. |
| "`todo.md` says `done` — tick it and move on" | A row from an earlier session is history, not this session's evidence. Re-run any gate whose verdict you are about to claim. |
| "One file is simpler than `plan.md` + `todo.md`" | Then every wave rewrites the plan and no diff separates a shape change from a finished node. Shape and run move on different clocks. |
| "The node finished, so I'll add it to `plan.md` too" | Status lives in `todo.md` alone. Two homes for one fact is how 3.x drifted. |
