# Graph mechanics

Read by the orchestrator only, before the first dispatch. A node gets what its prompt pastes — never this file.

## When not to use a graph

Default is a **loop**. A graph is earned. Forcing a job into nodes, edges, and waves because the router can is the failure mode this file exists to prevent.

Stay a loop when:

- one job, one finish line
- steps are sequential and use the same skill / toolset
- the ask is a question, research, or diagnosis
- one writer can hold the whole edit
- collapsing the nodes back into one loop loses nothing

A single edit job is **one writer node**. That node runs its own loop (discover / do / check). That is not a graph.

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

If you drew a graph and every node is "a step I could inline", delete the graph and dispatch one node.

A named domain skill that is itself a complete procedure (`init-project`, `migrate-project`, `open-collection`, `confluence-api-doc`, `gitlab`, `atlassian`, `falsifying`, `bug-hunter`, `attack-test`, `neo-core-sit`, `neo-aux-sit`) is **one loop**. Dispatch `task` with "load and follow `<skill>`" (inline if no subagent). Do not fan it out into catalog nodes.

## Node catalog

| Kind | Agent | Writes | Loads first | Never touches |
|---|---|---|---|---|
| build | `neo-builder` | one code package / file cluster + that surface's unit tests | `tdd` red-green only — seam is in the prompt, do not re-ask | another node's files, graph state, module-wide build/vet/fmt, git |
| author | `neo-author` | exactly one named file: a `docs/knowledge/` entry, or one `docs/api/<domain>/<endpoint>.yaml`, or one shared aggregate the prompt names (`INDEX.md`, `_meta.yaml`, `index.md`, `VERSION.md`, `CONTEXT.md`) | `markitdown` or `api-spec` | source code, tests, another source's entry, gate verdicts |
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
FORBIDDEN — files outside SURFACE; local://graph.md; module-wide build/vet/fmt;
            the e2e stack; the coverage command; neocheck.py; any git command; messaging another node
REPORT — files_written[], commands[] with real output, blocked[] with reason
```

Batch-level context (one per wave): the user ask, closed decisions, contract paths, non-goals, the wave id.

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
- Graph state is orchestrator-only and never appears in a SURFACE: `local://graph.md` or the harness todo tool.
- Wave width ≤ 6. More ready nodes → next wave.
- A single-node wave is the common case. Do not invent independence the work does not have.
- Do not pass `effort` unless the harness schema lists it. Plugin agents already pin `thinking-level: xhigh`.

## Fan-in checklist

Every wave, in this order:

1. Every dispatched node returned. `blocked` → dependents stay pending; siblings still land.
2. Surface check: `git status --porcelain` lists only files inside the declared SURFACEs. Anything else is a finding, not a merge.
3. Every path in `files_written` exists.
4. If this wave wrote production code: you run the module build + the touched packages' tests (or the repo equivalent) and keep the output. Docs-only / e2e-spec-only waves skip this and say so.
5. Reviewer node — **only** if this wave's diff touches production, `docs/api/`, or e2e specs. Brief: "list incorrect claims, invented APIs, missing tests, convention breaks — evidence required". If the diff touches untrusted input, auth, secrets, money, or PII, also load `code-review`'s Security axis into that brief.
6. Findings become new nodes in the next wave. You do not fix them.
7. Read a changed region yourself only when a node reported `blocked` or returned no test output.
8. Update graph state (`local://graph.md` or the harness todo tool): status + the evidence line. No evidence line, no `done`.

## Retry and escalation

A failed node is re-dispatched **once**, with its own failure output pasted into the new prompt. Second failure, or the same error twice, stops with one precise question. Never a third attempt, never a different node retrying the same task, never a hand-fix by you.

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

## Graph state

`local://graph.md` is the graph when the harness has that URI (omp). Otherwise keep the same table in the harness todo tool — never create a repo file for it. You are the only writer, and you write state only when you dispatch at least one node. A direct answer creates neither.

```
# graph

ask: <one line>
mode: loop | graph
trigger: <why a graph, or "none — single loop">

## nodes

| id | kind | agent | surface | depends | status | evidence |
|---|---|---|---|---|---|---|
| N1 | build | neo-builder | internal/account/** | none | done | go test ./internal/account/... ok |
```

`status` ∈ `pending` | `dispatched` | `returned` | `blocked` | `done`. `done` only after fan-in for that row.

Do not create `docs/tasks/<card>/` to hold this state. If that folder already exists, a node may write it when it is the named SURFACE — you still do not.

## Conditional gates

Run only when the touched surface matches. Unstated = skipped. If not triggered, say so in one line.

| Touched | You run | Verdict |
|---|---|---|
| production code | package tests for touched packages, then the repo coverage command | tests green; coverage ≥ 80% before you call the work done |
| `docs/api/` or HTTP-observable wire | `openapi-doc` + `apispeccheck` | drift = 0; apispeccheck green |
| HTTP-observable ACs / e2e specs | e2e stack + `e2echeck` | every HTTP-observable AC covered |
| a card folder already under `docs/tasks/<card>/` and you are claiming that card done | `neocheck.py <repo> <card>` | its table, pasted |
| user asked to ship / open an MR | `gitlab` — wait for confirm first | no push before that confirm |

Shared commands are yours: module build, vet, fmt, coverage, `neocheck.py`, `e2echeck`, `apispeccheck`, docker/mockoon, `openapi-doc`, every `git` read (`status`, `diff`). A node may run read-only checks scoped to its own surface.

Direction on contract drift:

- spec still correct, code drifted → a **build** node fixes code
- structural code matches already-agreed intent with an evidence path → an **author** node updates the spec surface only
- code encodes a new or superseded decision with no evidence → **stop and ask**. Do not invent the field. Do not promote code to requirement SOT.
