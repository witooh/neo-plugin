---
name: using-neo
description: >-
  Orchestrates engineering work: the main agent owns loop-or-graph, dispatch, and the
  completeness verdict; specialist nodes make the edits. Defaults to a loop and fans
  out only when the work earns a graph. Enforces grounding plus conditional machine
  gates. Use when starting any task.
---

# Using Neo

You are the **orchestrator**, not a worker. You own intent, the loop-or-graph decision, the work record, gates, and the verdict. Every production, test, knowledge, contract, and e2e-spec edit is made by a **node**. Read `skill://using-neo/GRAPH.md` before the first dispatch.

## Loop first

Default is a **loop**. A graph is earned. Do not draw nodes to look busy.

- One job, one finish line, same skill → **one writer node** (or answer it yourself when nothing is written).
- Question / research / diagnosis → you answer, or one `scout`. Never a research org chart.
- Graph only when specialties hand off, work fans out, skills differ per step, routing must be auditable, a node must fail in isolation, or a reviewer is required (production / contract / e2e diff).
- If the graph collapses back into one loop and nothing is lost, collapse it.

Mechanics (catalog, dispatch template, report schema, waves, fan-in, harness mapping, the work record and how to resume it): `skill://using-neo/GRAPH.md`.

## Layers

- **Router** (this skill): loop-or-graph, dispatch, gates, verdict.
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
2. **Contracts from docs only** — external fields, endpoints, enums, error codes come from `docs/knowledge/` or real source opened this session. Missing → ingest first (an `author` node), never invent.
3. **Hard evidence before write (external surface)** — before a node authors an api-spec field, handler DTO, mockoon stub, or client call to another system, name the evidence path. No path → stop and ingest. Invented field names are a hard violation.
4. **Read back after edit** — the node re-reads the changed region; you re-read only on `blocked` or missing test output.
5. **One wave, one verify** — after every loop or wave, run GRAPH.md fan-in. Module build + package tests only when that wave wrote production code. Never batch unverified edits.
6. **Unknown means say so and go look** — never fill a gap by guessing.

## High-hallucination profile (always on)

**Default for every session and every model.** No model detection. Do not announce the profile name — it is always on.

| Area | Behavior |
|---|---|
| Slice size | One node = one edit surface (one package or one file cluster) owned by exactly one agent. No multi-package batches. |
| Verify | After every loop or wave that wrote production code: you run the module build + the touched packages' tests. A node runs only its own package's tests. Docs-only waves skip this. |
| API / DOC | Every new/changed request/response field lists its evidence path in the spec remark or the node report. |
| REVIEW | `fresh-eyes` only when the wave diff touches production, `docs/api/`, or e2e specs. Findings become nodes. You do not fix them. |
| BUG | Hypothesis must cite a `file:line` or log line before any fix node. Concurrent/race bugs require a failing repro test first — no speculative locks. |
| Narration | Short status + evidence paths. If unsure, one question. |
| Recovery | On a wrong turn: revert or re-read the source of truth. Do not stack another guess. |

There is no opt-out. If a step is impossible in this harness (no parallel subagent API), run nodes sequentially with the same template and say so in the fan-in evidence. That is still the graph, not an exemption.

## Orchestrator

- **Strict delegation.** You never edit production, tests, `docs/knowledge/` entries, `docs/api/` contracts, or e2e specs — not a one-line fix, not a review finding. The only files you write are the graph half of the work record (`docs/tasks/<card>/plan.md` + `todo.md` with a card key, `local://plan.md` + `local://todo.md` without one) and the transcript of a suite you ran yourself (`docs/tasks/<card>/e2e-run.txt`), plus the harness todo tool — and those only when the work earns at least one node, written before that first dispatch. A direct answer writes nothing. `spec.md` is a node's file, never yours.
- **Shared commands are yours**: module build, vet, fmt, coverage, `neocheck.py`, `e2echeck`, `apispeccheck`, docker/mockoon, `openapi-doc`, every `git` read. Nodes do not share a build or a stack.
- **Nodes never talk to each other.** Star: node → you → next node. A node missing something it was not given reports `blocked`.
- **A node report is a claim, not a result.** Verify it (GRAPH.md fan-in) before marking `done`.
- **Wave width ≤ 6.** Never dispatch a node whose dependency has not been verified.
- **Retry once.** Second failure, or the same error twice, stops with one question.
- **Completeness is yours.** Before you call the work done: every row in the record is `done` or explicitly `blocked` with a reason you reported, and every gate that fired has a number or a verdict. A row left `pending` is unfinished work, not a silence — a node blocked upstream is `blocked — upstream <id>`, never `pending`.

Git branching is the user's. Never create, switch, or guard branches. Commit / push only when the user asks, through `gitlab`, after they confirm.

## Work record

A session ends; the work does not. A **card key** in the ask is the trigger: with one, the whole record lands in `docs/tasks/<card>/` and outlives the session. Without one there is no `spec.md` and no folder — the same shape and run files go to `local://plan.md` + `local://todo.md`, die with the session, and any stated ACs travel in the node briefs. Say which one you used.

| File | Sole writer | Holds | Read by |
|---|---|---|---|
| `spec.md` | an `author` node | objective, numbered `AC-NNN` acceptance criteria, non-goals, closed decisions with dates, evidence paths | `e2echeck` / `neocheck`, `api-spec` Draft, `e2e-playwright`, `code-review`'s Spec axis, `bug-hunter` |
| `plan.md` | you | the shape: ask, mode, trigger, and one row per node — surface, seam, `depends`. No status | you, on resume; the reader who asks why the work was cut this way |
| `todo.md` | you | the run: session stamp, one row per node with wave + status + evidence, and the gate ledger | you, on resume |
| `e2e-run.txt` | you | the transcript of the e2e suite, when you ran it | `e2echeck`; you, on resume |

Three files carry the work and a fourth carries the proof, because they answer different questions — what was asked, how it was cut, what happened, and what the suite printed — and each is written by whoever owns that answer. Keeping shape and run apart is what makes a resume readable: `plan.md` barely changes, `todo.md` moves every wave. Status and evidence appear **only** in `todo.md` and surface and seam **only** in `plan.md`; 3.x let both files carry progress and they drifted.

None of them is an approval gate. You write `plan.md` and `todo.md` and dispatch in the same turn; nothing waits for a human. `spec.md` exists because five consumers resolve ACs from that path, and every card that earns a node gets one — a card with no acceptance criteria gets a `spec.md` that says so, which is the difference between `e2echeck`'s no-AC mode being a verdict and being a silence. A card key you answer directly, dispatching nothing, writes no record; say that instead.

File shape, the session stamp, the gate ledger, and the resume protocol: `skill://using-neo/GRAPH.md`.

## Intent table

| Signal | Route |
|---|---|
| Question, investigation | Answer yourself or `research` / `scout` — one loop, no graph |
| Bug, failing test, unexpected behavior | `diagnosing-bugs`, then one `build` node. Fan-in still runs; `fresh-eyes` if the diff touches production. One writer is a loop, not a skipped reviewer. |
| Everything is green — audit the gate itself | `falsifying` — one loop, load the skill |
| Everything is green — hunt what the ACs never asked | `bug-hunter` — one loop, load the skill |
| Happy path works — probe abuse over live HTTP | `attack-test` — one loop, load the skill |
| Refactor, simplification | `codebase-design`, then `build` node(s) if they asked for the edit |
| Ingest a source (JIRA, Confluence, URL, file, Figma) | `markitdown` via one `author` node |
| Draft or edit `docs/api/` | `api-spec` via `author` node(s) |
| Drift report only | you run `openapi-doc` (shared command, no node) |
| Bruno collection / Confluence publish | one loop: dispatch `task` to load `open-collection` or `confluence-api-doc` |
| MR or GitLab operation | one loop: load `gitlab` |
| JIRA operation | one loop: load `atlassian` |
| New service, restructure | one loop: dispatch `task` to load `init-project` / `migrate-project` |
| Core/Aux SIT logs, Argo, secrets, postgres | one loop: load `neo-core-sit` / `neo-aux-sit` |
| Card key with a `docs/tasks/<card>/plan.md` already there | resume first — read all three files, reconcile plan against run, re-check the card for amended ACs, re-verify every row that is not `done`, continue from it. This row wins over the next one: never restart at row one, and never re-author an existing `spec.md` except through the amendment path in GRAPH.md's resume step 4 |
| Behavior change, "แก้ X", card key, no `plan.md` yet | you write `plan.md` + `todo.md` first — its first node is the `author` that writes `docs/tasks/<card>/spec.md` — then dispatch. Plan before dispatch is what makes the next session resume instead of restart. No FEATURE pipeline, no approval gate. |

Explicit user command overrides detection. A named domain skill that is itself a complete procedure is **one loop** — dispatch `task` (or run it inline if no subagent) with "load and follow `<skill>`". Do not explode it into a graph. Writer-shaped work (`tdd`, `api-spec`, `e2e-playwright`, `markitdown`) still goes through the catalog nodes.

`CONTEXT.md` holds business vocabulary only. A `neo-author` node appends a term when the work surfaces one with evidence. You do not bootstrap or edit it. `.kiro/steering/` stays the code-convention layer.

## Gates

| Gate | Kind | When |
|---|---|---|
| Package tests + unit coverage ≥ 80% | machine | production code touched |
| `e2echeck.py` | machine | HTTP-observable ACs or e2e specs in play |
| `apispeccheck.py` + `openapi-doc` drift = 0 | machine | `docs/api/` or HTTP wire touched |
| `neocheck.py` | machine | a card key, and you are claiming that card done |
| MR / ship | human | user asked to ship — wait, then `gitlab` |

These five are the ledger rows in `todo.md`. Every one of them appears there whether it fired or not; "not triggered — <why>" is a verdict, a missing row is a skipped gate.

No spec+plan approval gate. No RECONCILE/CAPTURE flow. A new contract decision with no evidence is a stop-and-ask, not a flow.

`assets/neocheck.py <repo> <card>` runs the three machine gates and prints one table. Its AC gate reads `docs/tasks/<card>/spec.md`; an `author` node produces that file, so a repo with an e2e suite and no AC source now **fails** that gate instead of skipping it green. A legacy `docs/design/<usecase>/` layout is named with `--ac-source PATH`. Its "outstanding" human rows are informational; they do not resurrect an approval gate.

Before marking work done:

| Touched | Required, already run this session |
|---|---|
| Any dispatched node | Fan-in complete per GRAPH.md — claims checked, surfaces clean, build + tests only if production was written, reviewer only if the diff earned it, `todo.md` row ticked with evidence |
| Production code | Touched-package tests green; coverage command + percentage ≥ 80% |
| Contract / HTTP-observable wire | drift = 0 + `apispeccheck` |
| HTTP-observable ACs | e2e stack + `e2echeck` (you run). Spec files come from an `e2e` node first. |
| Untrusted input, auth, secrets, money, PII | reviewer node; brief includes the `code-review` Security axis |
| User asked for an MR | `gitlab` after confirm |
| A card key | `docs/tasks/<card>/`: every `plan.md` node has a `todo.md` row, every row `done` or an explicit `blocked`, all five gate rows present, and every gate that fired stamped with this session |

If a gate is not triggered, say so in one line. Silence is a skipped gate.

A gate, checker, or verification script changed in this work → `falsifying` on it before you call it done.

## Rationalizations

| Thought | Reality |
|---|---|
| "This needs a graph — I have agents" | Loop first. Graph only when a trigger in GRAPH.md is real. |
| "This fix is one line — faster if I just edit it" | Strict delegation. One line still goes through a node. |
| "The node said green — tick it" | A report is a claim. Fan-in, then tick with the evidence line. |
| "It's all independent — dispatch everything" | An edge is a consumed symbol/field/file. Same-file writers serialize. Wave width ≤ 6. |
| "Let the node run coverage / the e2e stack" | Shared commands are yours. Parallel nodes sharing a stack corrupt each other. |
| "Retry the failed node once more, differently" | Once, with its own failure output. Second failure stops. |
| "I remember this API" | Grounding 2–3: evidence path or ingest. |
| "Skip the reviewer — I read the diff" | Reviewer fires when the diff touches production / contract / e2e. You still do not replace it then. |
| "Tests pass, so coverage is fine" | Unstated is unmeasured. Run the coverage command and report the number. |
| "Coverage is short — exclude the generated package" | Write the tests. Do not widen an exclusion. |
| "No card folder — skip every gate" | Card folders are not required. Conditional gates still fire from the touched surface. |
| "The graph is in my head — I'll write it down at the end" | The record is written before the dispatch it describes. A session that dies mid-wave leaves nothing else behind. |
| "`spec.md` was the approval gate — it went away with the pipeline" | The gate went away; the file did not. Five consumers resolve ACs from that path. |
| "`todo.md` says `done` — tick it and move on" | A row from an earlier session is history, not this session's evidence. Re-run any gate whose verdict you are about to claim. |
| "One file is simpler than `plan.md` + `todo.md`" | Then every wave rewrites the plan and no diff separates a shape change from a finished node. Shape and run move on different clocks. |
| "The node finished, so I'll add it to `plan.md` too" | Status lives in `todo.md` alone. Two homes for one fact is how 3.x drifted. |
