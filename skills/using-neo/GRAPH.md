# Graph mechanics

Read before the first dispatch — this file is the mechanics of delegating. Work you do yourself needs only the record and the fan-in checks below. A node gets what its prompt pastes — never this file.

## When not to use a graph

Default is a **loop**. A graph is earned. Forcing a job into nodes, edges, and waves because the router can is the failure mode this file exists to prevent.

Stay a loop when:

- one job, one finish line
- steps are sequential and use the same skill / toolset
- the ask is a question, research, or diagnosis
- one writer can hold the whole edit
- collapsing the nodes back into one loop loses nothing

A single edit job is **yours**: discover / do / check, inline. That is not a graph, and it does not need a node.

Questions and open research stay with you, or one `scout` loop. Never a researcher → writer → reviewer org chart.

Reach for a graph only when at least one trigger is real:

| Trigger | Graph earns it |
|---|---|
| Shape | distinct specialties that hand off (code vs contract vs e2e) |
| Parallelism | fan-out then join |
| Tools / skills | different skill or toolset per step |
| Routing | you need an explicit, auditable path between roles |
| Failure isolation | one node must be able to fail without poisoning the rest |
| Reviewer | the wave diff touches production, contract (`docs/api/`), or e2e specs |

The reviewer node is **not** automatic. No production / contract / e2e diff → no `fresh-eyes` node. You still run the fan-in checks you can run alone.

If you drew a graph and every node is "a step I could inline", delete the graph and do the work.

A named domain skill that is itself a complete procedure (`init-project`, `migrate-project`, `open-collection`, `confluence-api-doc`, `gitlab`, `atlassian`, `falsifying`, `bug-hunter`, `attack-test`, `neo-core-sit`, `neo-aux-sit`) is **one loop**. Load and follow it yourself; dispatch `task` with "load and follow `<skill>`" only to keep its reading off your context. Do not fan it out into catalog nodes.

## Node catalog

The catalog is who you dispatch **to**. When you write a surface yourself, the same Writes / Loads first / Never touches columns describe your own discipline on it — minus the ones that exist only because a node is isolated (module-wide build, git, the shared stack), which are yours anyway.

| Kind | Agent | Writes | Loads first | Never touches |
|---|---|---|---|---|
| build | `neo-builder` | one code package / file cluster + that surface's unit tests | `tdd` red-green only — seam is in the prompt, do not re-ask | another node's files, `plan.md` / `todo.md`, module-wide build/vet/fmt, git |
| author | `neo-author` | exactly one named file: a `docs/knowledge/` entry, or one `docs/api/<domain>/<endpoint>.yaml`, or `docs/tasks/<key>/spec.md`, or one shared aggregate the prompt names (`INDEX.md`, `_meta.yaml`, `index.md`, `VERSION.md`, `CONTEXT.md`) | `markitdown` or `api-spec` | source code, tests, another source's entry, `plan.md` / `todo.md`, gate verdicts |
| e2e | `neo-e2e` | the e2e spec files for its assigned ACs | `e2e-playwright` | production code, the docker/mockoon stack, the coverage verdict |
| review | `fresh-eyes` | nothing — read-only by tool grant | the axis brief in its prompt | any file |
| research | `scout` (harness built-in; `task` where absent) | nothing — read-only | — | any file |

Two nodes that would write the same file are never in one wave.

## Dispatch template

Every node prompt carries these sections, in this order:

```
NODE <id> · WAVE <n>
SURFACE — you may write only these paths: <explicit paths or globs>
SKILL — load before your first edit: <skill>; also read: <steering guide path, when the surface is code>
SEAM — where your tests sit, if any: <handler | use case | repository | http spec | none>
EVIDENCE — contracts come from these paths only: <docs/knowledge/…, docs/api/…, or none>
TASK — <the work>
FORBIDDEN — files outside SURFACE; the record's graph half (docs/tasks/<key>/plan.md + todo.md);
            docs/tasks/<key>/e2e-run.txt;
            module-wide build/vet/fmt;
            the e2e stack; the coverage command; neocheck.py; any git command; messaging another node
REPORT — files_written[], commands[] with real output, blocked[] with reason
```

Batch-level context (one per wave): the user ask, closed decisions, contract paths, `docs/tasks/<key>/spec.md` when one exists, non-goals, the wave id.

## Node report schema

```json
{
  "type": "object",
  "required": ["files_written", "commands", "blocked"],
  "properties": {
    "files_written": { "type": "array", "items": { "type": "string" } },
    "commands": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["cmd", "result"],
        "properties": { "cmd": { "type": "string" }, "result": { "type": "string" } }
      }
    },
    "blocked": { "type": "array", "items": { "type": "string" } }
  }
}
```

## Wave rules

- Edge test: A depends on B when A consumes a symbol, field, or file B creates. Nothing else is an edge.
- Same-file writers serialize.
- The graph half of the record is yours and never appears in a SURFACE: `docs/tasks/<key>/plan.md` + `todo.md`. `docs/tasks/<key>/spec.md` is a normal surface — yours when you write it, a node's when you delegate it, never both in the same wave. Never create `docs/tasks/<slice>/` for a step.
- Wave width ≤ 6. More ready nodes → next wave.
- A single-node wave is the common case. Do not invent independence the work does not have.
- Do not pass `effort` unless the harness schema lists it. Plugin agents already pin `thinking-level: xhigh`.

## Fan-in checklist

Every wave, in this order. A surface you wrote yourself runs the same list, with your own edit in place of the node report:

1. Every returning node flips its row to `returned` — back, not yet verified — before you check anything; a surface you wrote yourself goes straight from `dispatched` into the checks below. `blocked` → that row is `blocked` with its reason, and every row that depends on it becomes `blocked — upstream <id>`; siblings still land. A dependent left `pending` is a row completeness can never settle.
2. Surface check: `git status --porcelain` lists only files inside the declared SURFACEs. Anything else is a finding, not a merge.
3. Every path in `files_written` exists.
4. If this wave wrote production code: you run the module build + the touched packages' tests (or the repo equivalent) and keep the output. Docs-only / e2e-spec-only waves skip this and say so.
5. Reviewer node — **only** if this wave's diff touches production, `docs/api/`, or e2e specs. Brief: "list incorrect claims, invented APIs, missing tests, convention breaks — evidence required". If the diff touches untrusted input, auth, secrets, money, or PII, also load `code-review`'s Security axis into that brief. A reviewer is dispatched from here, so it was never in the pre-dispatch plan: append its node row to `plan.md` with a dated re-plan line **and** write its `dispatched` row in `todo.md` before it runs, exactly as for a planned node. A reviewer that found nothing still gets a row — otherwise a resumed session cannot tell a clean review from a review that never ran.
6. Findings become rows in the next wave — yours to fix or a node's, never a silent fix folded into the reviewed diff. Each one is a `plan.md` row plus a dated re-plan line.
7. Read back every region you changed yourself (grounding rule 4). A node's region you re-read only when it reported `blocked` or returned no test output.
8. Update `docs/tasks/<key>/todo.md`: each row's status and its evidence line, plus any gate row this wave settled. No evidence line, no `done`. `plan.md` changes only when the shape did — a reviewer, a finding, or a `blocked` that forces a different cut — and every such change carries a dated re-plan line.

## Retry and escalation

A failed node is re-dispatched **once**, with its own failure output pasted into the new prompt. Second failure, or the same error twice, stops with one precise question. Never a third attempt, never a different node retrying the same task — and never a hand-fix by you that skips the record, though taking the surface over yourself with its own row and evidence is a re-plan, not a retry. The budget is spent at re-dispatch, not at the retry's fan-in: you write `retry 1/1 spent` into the row's evidence cell in the same breath as you flip it back to `dispatched`. Record it later and a session that dies mid-retry hands the row a second one.

## Harness mapping

Every supported harness runs the same graph. The table is how to dispatch, not a ranking. Sequential execution is only when the runtime has no parallel subagent API — say so in the fan-in evidence.

| Harness | Wave dispatch | Node identity | Results |
|---|---|---|---|
| omp | one `task` call per wave; `tasks[]` = one entry per node; batch `context` = ask + decisions + contract paths + non-goals | catalog name as `agent`, `name` = node id, `outputSchema` = the report schema above | auto-delivered; `hub jobs` / `hub wait` for a straggler; `hub send` to steer one node |
| Claude Code | one message, one `Agent` call per node, `run_in_background: true` on each | `subagent_type` = catalog name (`agents/*.md` in the plugin) | one tool result per call; wait for every node before fan-in |
| Cursor | same Agent/Task shape after `./cursor.sh` | `.cursor/agents/` copies of `agents/*.md` | same |
| Kiro | same after `./kiro.sh` | `.kiro/agents/` copies of `agents/*.md` | same |
| pi | `Task`/`Agent` when the runtime exposes the catalog type; otherwise one node at a time with SURFACE / FORBIDDEN / REPORT pasted | session injects `using-neo` | say so in the fan-in evidence if sequential |
| Grok | `/using-neo` if SessionStart stdout is dropped; then same as Claude Code when `Agent` exists; otherwise sequential with the template | plugin `skills/` + `agents/` | say so in the fan-in evidence if sequential |
| no subagent API | you execute the node inline, one node at a time, same template | — | say so |

## Work record

The work is written down before it is done. The durable id is a **work key**, not a JIRA card key. Resolve it in this order:

1. An explicit work key the user named for this body of work (`bingo`, `docs/tasks/bingo`, or a JIRA key presented as the card/work id — "ทำ GI-123", not an incidental mention). Folder name only. Do not invent a path.
2. An existing `docs/tasks/<key>/` folder the ask continues → that key. If `plan.md` is already there, resume. If the folder exists without `plan.md`, write the record there. If several folders could match and the ask does not pick one → ask. Never create a child folder for a slice or step.
3. File-changing work with none of the above → stop and ask for a work key. Do not invent a slug. Do not create `docs/tasks/<slice>/`. Do not write `local://plan.md` as the record.
4. Changing nothing → no record.

Never take the first `TOKEN-N` in the sentence. `AC-NNN` is a criterion id, never a work key. Never mint a work key from a slice name, a sentence, or a session id. One body of work, one folder: slices and steps are rows in `plan.md` (S0, A1, T1), not `docs/tasks/<slice>/`.

| Part | Path | Writer |
|---|---|---|
| acceptance criteria | `docs/tasks/<key>/spec.md` | you, or an `author` node — name the file in its SURFACE when you delegate it |
| the shape | `docs/tasks/<key>/plan.md` | you, sole writer |
| the run | `docs/tasks/<key>/todo.md` | you, sole writer |
| e2e run transcript | `docs/tasks/<key>/e2e-run.txt` | you, when you run the suite |

Shape and run are separate files because they move on different clocks. The shape is decided once and re-decided only when a finding or a `blocked` forces a node; the run changes every wave. Fold them together and every wave rewrites the plan, so no diff separates "the shape changed" from "a node finished" — which is exactly the question a resume asks. 3.x split them too and let both carry progress, which is how they drifted apart; here **status and evidence live only in `todo.md`, surface and seam only in `plan.md`**. One fact, one home.

File-changing work with a resolved work key gets the whole record: `plan.md` and `todo.md` before the first edit, and `spec.md` as that plan's first row — written even when the work carries no acceptance criteria, in which case the file says so in one line, which is what keeps `e2echeck`'s no-AC mode an honest verdict instead of a silent one. A request you answer directly — changing nothing — creates no files; say so instead. The harness todo tool mirrors `todo.md` inside the session and is not the record.

### `plan.md` — the shape

Written in full before the first edit — including the row that writes `spec.md`, which is a planned row like any other — then left alone unless the shape itself changes. It carries no status: a plan that tracks progress is a todo.

```
# GI-123 — <one-line ask>

mode: loop | graph
trigger: <the earned graph trigger, or "none — single loop">
spec: docs/tasks/GI-123/spec.md

## nodes

| id | kind | agent | surface | seam | depends |
|---|---|---|---|---|---|
| N1 | author | you | docs/tasks/GI-123/spec.md | none | none |
| N2 | build | neo-builder | internal/account/** | use case | N1 |
| N3 | e2e | neo-e2e | tests/e2e/specs/account/** | http spec | N1 |

## re-plan

- 2026-08-23T22:10 — added N4 (build) from a fresh-eyes finding on N2
```

`depends` is the edge test and nothing else: A depends on B when A consumes a symbol, field, or file B creates. Waves fall out of that column — they are not authored here. The `agent` column says who writes the surface: `you` for an inline row, a catalog agent for a dispatched one. A row added mid-flight is a re-plan: append it plus one dated line naming what forced it, so the next session can tell a planned row from an improvised one.

### `todo.md` — the run

Created alongside `plan.md`, with one `pending` row per planned row, and rewritten twice per wave: you flip a row to `dispatched` **as** the work starts — as you dispatch the node, or as you begin the surface yourself — and settle it at fan-in. It is the only file that says what actually happened.

```
# GI-123 — run

session: 2026-08-23T21:40      # rewritten on every resume; each row keeps the stamp that settled it

## waves

| wave | node | status | evidence |
|---|---|---|---|
| 1 | N1 | done | docs/tasks/GI-123/spec.md written + read back, 6 ACs · 2026-08-23T21:40 |
| 2 | N2 | done | go test ./internal/account/... ok · 2026-08-23T21:40 |
| 2 | N3 | dispatched | — |

## gates

| gate | verdict | session |
|---|---|---|
| package tests + coverage | make cover 84.2% ≥ 80% | 2026-08-23T21:40 |
| e2echeck (AC coverage) | not triggered — no HTTP-observable AC | — |
| apispeccheck + drift | not triggered — no docs/api or wire change | — |
| neocheck.py | not run — not claiming the work done yet | — |
| MR / ship | not triggered — user has not asked | — |
```

`status` ∈ `pending` | `dispatched` | `returned` | `blocked` | `done`, and every one of them is written by someone: `pending` when the plan is written, `dispatched` as the work starts — the node goes out, or you pick the surface up — `returned` when a node comes back, then `blocked` or `done` at fan-in. Every row in `plan.md` owns exactly one row here from the moment the plan is written. A row reaches `done` only after fan-in, and only with an evidence line: what settled it, plus this session's stamp. What counts as evidence follows the kind — a **code** row gives the command and its result; a **docs** row gives the file written and the read-back, because a docs-only wave runs no build (fan-in step 4); an **e2e** row gives the spec files written and the `AC-NNN` ids they cover, since the suite is not run there; a **review** row gives the finding count and where each finding went (a row id, or "none"); a **research** row gives where the answer landed.

`dispatched` is written before the work runs, not after — when the node goes out, and equally when you pick the surface up yourself. That single flip is what lets a later session tell "planned, never started" from "started, never verified" — the two states that look identical in a working tree.

The ledger carries a row for **every** gate in the conditional-gate table below, fired or not. "not triggered — <why>" is a verdict, and it needs no session stamp; a gate that actually ran carries the stamp of the session that ran it. A missing row reads as a skipped gate, which is the ambiguity this record exists to kill.

## Resume

A work key whose `plan.md` already exists is a resume, never a restart. Work through this before you start.

1. Read all three: `spec.md`, `plan.md`, `todo.md`. Report the row tally and the row you continue from. Never rewrite an existing `spec.md` from scratch — yourself or through an author node; the one amendment path is step 4.
2. Reconcile shape against run: every `plan.md` row needs a `todo.md` row. A planned row with no run row is a lost write, not proof it never ran — the realistic cause is a mid-wave append whose row write was lost — so treat it as `returned` and put it through step 6, never as `pending`.
3. Write a new `session:` stamp at the top of `todo.md`. Every row still carrying an older stamp is history: an earlier session's verdict, not yours.
4. Did the source of intent change? Re-read the card, the user-set brief, or the knowledge paths against `spec.md`. If an AC was added, reworded, or dropped, `spec.md` is amended — by you or an `author` node — and then every `done` row whose surface implements a touched AC drops back to `pending` with the reason. `e2echeck` will not catch this for you: it matches AC **ids** to test titles, so an `AC-003` whose text changed still reads as covered.
5. `done` rows — keep the row, distrust the verdict. Grounding rule 1 binds: re-run any gate whose verdict you are about to claim, and stamp it with this session.
6. `dispatched` / `returned` rows are the dangerous ones: a session ended between the edit and its fan-in, whoever made it. Run that row's fan-in now. Never promote it because the files exist. A row already carrying `retry 1/1 spent` has no retry left.
7. Continue from the first row that is not `done`. Never redo the work behind a `done` row. The shape in `plan.md` still holds — changing it is a dated re-plan line, never a silent edit.
8. Every row `done` or explicitly `blocked`, and every gate that fired carrying a verdict stamped with this session → the work is finished. Say so and stop.

## Conditional gates

Run only when the touched surface matches. Unstated = skipped. If not triggered, say so in one line.

| Touched | You run | Verdict |
|---|---|---|
| production code | package tests for touched packages, then the repo coverage command | tests green; coverage ≥ 80% before you call the work done |
| `docs/api/` or HTTP-observable wire | `openapi-doc` + `apispeccheck` | drift = 0; apispeccheck green |
| HTTP-observable ACs / e2e specs | e2e stack + `e2echeck` | every HTTP-observable AC covered |
| a work key, and you are claiming that work done | `neocheck.py <repo> <key>` — `<key>` is the work-key folder name. Add `--ac-source PATH` when the ACs live in a legacy `docs/design/<usecase>/` layout instead of `spec.md`, or the AC gate hard-fails on a file that was never meant to exist | its table, pasted |
| user asked to ship / open an MR | `gitlab` — wait for confirm first | no push before that confirm |

Shared commands are yours: module build, vet, fmt, coverage, `neocheck.py`, `e2echeck`, `apispeccheck`, docker/mockoon, `openapi-doc`, every `git` read (`status`, `diff`). A node may run read-only checks scoped to its own surface.

Direction on contract drift:

- spec still correct, code drifted → fix the code (you, or a **build** node)
- structural code matches already-agreed intent with an evidence path → update the spec surface only (you, or an **author** node)
- code encodes a new or superseded decision with no evidence → **stop and ask**. Do not invent the field. Do not promote code to requirement SOT.
