---
name: using-neo
description: Routes engineering work through neo's single entry point. Detects intent, drives the matching flow (FEATURE, BUG, REFACTOR, RECONCILE; ingest → align → api → spec → build → verify → review → doc → MR), enforces machine gates, and always applies the high-hallucination profile (small slices, hard evidence, fresh-eyes review). Use when starting any task.
---

# Using Neo

Single entry router. Every request routes here first: detect intent, run the matching flow, stop only at gates. The flow drives itself — never present a menu of methodologies.

## Layers

- **Router** (this skill): when things happen — intent, flow order, gates, resume, model profile.
- **Method layer** (vendored from [mattpocock/skills](https://github.com/mattpocock/skills) via `sync-mattpocock`): `grilling`, `domain-modeling`, `tdd`, `diagnosing-bugs`, `research`, `prototype`, `codebase-design`, `resolving-merge-conflicts`. Live under `skills/<name>/`.
- **Domain layer** (neo-owned): `code-review`, `falsifying`, `bug-hunter`, `api-spec`, `e2e-playwright`, `openapi-doc`, `open-collection`, `confluence-api-doc`, `markitdown`, `init-project`, `migrate-project`, `atlassian`, `gitlab`.

## Method-layer availability

Method skills ship inside this plugin. If `tdd` / `grilling` / `diagnosing-bugs` are missing, tell the maintainer once to run `sync-mattpocock`, then continue with inline minimums — do not block:

- **grilling**: one question at a time; stop when no open decisions remain.
- **tdd**: failing test first, make it pass, refactor.
- **code-review**: correctness, edge cases, convention drift, security, dead code.
- **diagnosing-bugs**: reproduce first; one hypothesis; evidence before fix.
- **domain-modeling**: record new/ambiguous business terms in `CONTEXT.md`.

## Grounding rules (always on, every model)

1. **Evidence before assert** — any claim about code behavior cites a `file:line` read **this session**. No cite → do not claim.
2. **Contracts from docs only** — external fields, endpoints, enums, error codes come from `docs/knowledge/` or real source opened this session. Missing → **INGEST first**, never invent.
3. **Hard evidence before write (external surface)** — before authoring/editing an api-spec field, handler DTO, mockoon stub, or client call to another system, name the evidence path (e.g. `docs/knowledge/contracts/…`). No path → stop and ingest. Invented field names are a hard violation.
4. **Read back after edit** — re-read the changed region before declaring done.
5. **One task, one verify** — run the relevant build/tests after each task; never batch unverified edits.
6. **Unknown means say so and go look** — never fill a gap by guessing.

## High-hallucination profile (always on)

**Default for every session and every model.** No model detection. Payment/external-API work and unreliable models both need the same net; detection is flaky and fails open (profile off when you need it most). Do not announce the profile name in chat — it is always on; just follow the rules.

**Rules (on top of grounding 1–6):**

| Area | Behavior |
|---|---|
| Slice size | One todo item = one edit surface (one package or one file cluster). No multi-package batches. |
| BUILD verify | After **every** green test: run package tests for the touched package (not only at end of all tasks). |
| API / DOC | Every new/changed request/response field lists its evidence path in the working notes or spec remark. |
| REVIEW | Run `code-review`, **then** spawn one fresh-context subagent (`subagent_type: "fresh-eyes"`) on the diff with only: “list incorrect claims, invented APIs, missing tests, convention breaks — evidence required”. Fix before DOC. |
| BUG | Hypothesis must cite a `file:line` or log line before any fix. Concurrent/race bugs require a failing repro test first — no speculative locks. |
| Narration | Prefer short status + evidence paths over long reasoning. If unsure, stop with one question. |
| Recovery | On a wrong turn: revert or re-read source of truth, do not stack another guess on top. |

There is no opt-out flag. If a step in the table is impossible in the harness (e.g. no subagent), do the closest equivalent (second self-pass with only the diff in context) and say so.

## Intent table

| Signal | Route |
|---|---|
| Card key, feature, behavior change | FEATURE flow |
| Bug, failing test, unexpected behavior | BUG flow |
| Everything is green — audit the gate itself | `falsifying` |
| Everything is green — hunt what the ACs never asked | `bug-hunter` |
| Refactor, simplification | REFACTOR flow |
| Code shipped ahead of docs / reverse-sync / reconcile KB+task+api to code (with evidence) | RECONCILE flow |
| Question, investigation | Answer directly or `research` — no ceremony |
| Ingest a source (JIRA, Confluence, URL, file, Figma) | `markitdown` |
| API contract or doc work | `api-spec` / `openapi-doc` / `open-collection` / `confluence-api-doc` |
| MR or GitLab operation | `gitlab` |
| JIRA operation | `atlassian` |
| New service, restructure | `init-project` / `migrate-project` |

Explicit user command overrides detection. Git branching is the user's: never create, switch, or guard branches. Only the MR step has git side effects, behind its gate.

## FEATURE flow

Steps run in order; nothing is skipped silently.

### 1. INGEST

- Card key: fetch with `acli` (via `atlassian` conventions).
- Detect Confluence / Figma / integration specs / attachments; `markitdown` each missing source into `docs/knowledge/` (check `INDEX.md`; supersede stale; keep provenance).
- Resume: if `docs/tasks/<card>/` exists, read `spec.md` + `plan.md` + `todo.md` and offer to continue.

### 2. ALIGN — decision-grilling, not requirement discovery

- Do not re-ask ACs already on the card.
- Build the open-decision list (gaps vs ingested contracts). Empty → proceed; else `grilling` one decision at a time.
- Log closed decisions in the `spec.md` header with a date.
- **`CONTEXT.md` (business vocabulary only — never code conventions; those stay in `.kiro/steering/`):**
  - **Bootstrap (once per repo):** on a FEATURE flow, if the repo root has no `CONTEXT.md`, create a minimal skeleton only — title + one line that vocabulary accumulates during ALIGN. Do **not** invent terms. Skip bootstrap on BUG, pure DOC/MR, gate re-runs, and resume of a fully closed card with nothing left to decide.
  - **Seed (evidence only):** when ALIGN surfaces a new or unstable business term (or a closed decision that names a concept), run `domain-modeling` and append that term with a short definition grounded in the card/spec/knowledge path. Never bulk-seed from an old completed card.
  - If `CONTEXT.md` already exists, only update it when terms change — do not rewrite.

### 3. API

- Endpoints involved → draft `docs/api/` with `api-spec` **before** plan.
- Hard evidence rule applies to every external field (grounding rule 3).

### 4. SPEC + PLAN

- **Order**: with endpoints in scope, step 3's `docs/api/` files exist **before** `plan.md` is written. Writing the plan first is a flow violation — draft the contract, then plan against it.
- `docs/tasks/<card>/spec.md` (objective, ACs, non-goals), `plan.md`, `todo.md`.
- Plan tasks must be single-surface slices (profile). Each task names the **seam** its tests sit at (the public boundary — handler, use case, repository) in `plan.md`.
- Each task also states `Depends: T<n>, ...` or `Depends: none`. A task depends on another when it consumes a type, field, or file that the other creates. `todo.md` then groups tasks whose dependencies are all met into numbered **waves**, so independent slices are visible as parallelizable instead of hiding in a flat list. A single-task wave is normal — do not invent independence the code does not have.
- **GATE (human)**: present spec + plan; one approval runs through to the MR gate. Approving the plan pre-agrees its seams, so `tdd` does not re-ask per task; a task that needs a seam the plan never named stops and asks.

### 5. BUILD

- **Skill invocation is mandatory.** Before the first production edit of each task, load + follow the skill matching the work: `tdd` for any code change (red first), `api-spec` for any API-contract touch, `e2e-playwright` for HTTP-AC coverage. Never shortcut a skill because the change is small, the answer is known, it is "type/DTO/wire-only", or "e2e comes later".
- A conversational request that changes behavior or code ("แก้ X…") enters this flow — never an ad-hoc direct implement.
- Per task: `tdd` red-green-refactor; typecheck/lint on green; tick `todo.md`.
- **Waves run concurrently.** Tasks in the same wave go out in one message, one `Agent` call per task (`subagent_type: "neo-builder"`; where the harness has no such type, use `general-purpose` and paste this bullet's rules into the prompt), `run_in_background: true` on each. Different waves stay sequential. A wave agent writes only its own surface — production code plus that surface's unit tests. Build, vet, fmt, and ticking `todo.md` belong to the parent after the whole wave returns, never inside a wave agent: the slices keep source files disjoint, but a shared module build and a shared `todo.md` still collide.
- Read the matching `.kiro/steering/` guide before writing in a layer; `new-feature-checklist.md` when present.
- Package-level tests after every task (profile table).

### 6. VERIFY

- Unit: run the repo's **canonical coverage command** (`make cover` / `make test-cover` / equivalent), not a bare test run — a bare run reports no percentage.
- **GATE (machine)**: project-wide unit line coverage ≥ **80%** of first-party source. State the command, the measured number, and the verdict; a percentage never stated is a skipped gate, and passing-test or changed-line counts do not substitute. Below threshold → write tests. A new or widened coverage exclusion in this change is a finding, never the fix.
- E2E: `e2e-playwright` per-AC on isolated stack (docker-compose + mockoon).
- **GATE (machine)**: `e2echeck` every HTTP-observable AC; `govulncheck` when available.
- Failures → `diagnosing-bugs` — no blind retries.

### 7. REVIEW

- `code-review` on the full diff — Standards, Spec, and (when the diff earns it) Security.
- Mandatory fresh-eyes pass after `code-review` (profile table); fix; re-verify.

### 8. DOC

- `api-spec` sync-back; `openapi-doc` drift = 0.
- **GATE (machine)**: `apispeccheck` passes.
- A gate, checker, or verification script changed in this card → `falsifying` on it before DOC closes.
- Contract changed → `open-collection` + `VERSION.md`. Confluence only on request.

### 9. MR

- **GATE (human)**: final diff summary + MR title/body; wait.
- On confirm: `gitlab` push + MR to `develop`. Never commit/push before this gate.

## BUG flow

1. Ingest report/evidence.
2. `diagnosing-bugs` — hypothesis needs `file:line` or log cite before fix.
3. `tdd` failing repro first (concurrent test for races), then fix to green.
4. HTTP-observable → e2e regression tagged to the card.
5. `code-review` + fresh-eyes.
6. **Contract doc close** (mandatory when triggered — see below). Stop only after it passes — user commits.

## REFACTOR flow

1. Confirm behavior-preserving scope.
2. `codebase-design` for target shape.
3. Small steps; tests green after each (single-surface slices).
4. `code-review` + fresh-eyes.
5. **Contract doc close** if the refactor touched a contract surface (should be rare). Stop — user commits.

## Contract doc close (every flow that edits production code)

Docs go stale the moment code ships without them. **Skipping is not allowed when the trigger matches** — FEATURE already has DOC; BUG / REFACTOR / ad-hoc code edits use this same close.

**Trigger** — any of:

- Diff touches HTTP contract surface: route, handler, wire DTO, request/response field, status code, public error code, or anything `docs/api/` describes.
- The change is HTTP-observable to a client (even if no DTO file renamed).
- `docs/api/` exists for the service and the package that owns an endpoint changed.

**Not a trigger** — pure internal logic with no wire/status/error change (state so in the close-out; do not pretend a trigger was skipped).

**Close steps** (when triggered):

1. `openapi-doc` — must end at **drift = 0** before stop.
2. Direction per drift row:
   - Spec still correct, code drifted → fix code (or stay in BUG); do not rewrite the spec to match a bug.
   - Structural code matches an already-approved intent (bug card / existing AC / ingested knowledge) → `api-spec` **Update-from-code** for structural surface only; preserve hand-authored semantics; `apispeccheck` green; `VERSION.md` when contract files change.
   - Code encodes a **new or superseded decision** not yet in KB/task docs → **leave this close** and run **RECONCILE** (CAPTURE first). Silent Update-from-code without CAPTURE is forbidden.
3. Contract files changed → `open-collection` when the collection exists.
4. State the trigger, command(s), and drift=0 verdict. Unstated = skipped = not done.

Ad-hoc "แก้ code ตรงๆ" that changes behavior still enters a flow (BUG or FEATURE BUILD) — it does **not** get a doc exemption.

## RECONCILE flow

When **code already leads** the written requirement (hotfix, mid-card decision landed in code first, or docs/tasks still state a superseded rule). **KB stays SOT** — never promote code to SOT. Reuses existing skills only; no separate doc-from-code skill.

Triggers (examples): "code นำหน้า", "reverse-sync", "reconcile doc", "hotfix แล้ว doc ค้าง", "sync doc ตาม code (มี evidence)".

### 0. CAPTURE — **GATE (human), never skip**

A commit alone is not a requirement source. Before any KB/task/api write, name:

1. **Decision source** — JIRA comment / Confluence / chat / verbal from whom / explicit user approval of a commit+scope.
2. **Who + why** — decider and reason (one line each).
3. **Scope** — every fact being ratified (e.g. key = `referenceNo` only; fee from request into session + echo). List them; do not infer from the diff.

No evidence → **stop and ask**. Do not ingest, do not rewrite D-notes, do not Update-from-code.

### 1. INGEST

- `markitdown` a **new** knowledge entry (or supersede note) — never silent edit of an old entry.
- Provenance required: source id (e.g. `verbal:YYYY-MM-DD`, JIRA key, commit sha) + who/why/scope from CAPTURE.
- Update `docs/knowledge/INDEX.md`.

### 2. ALIGN — task-docs sync

- Sweep **every** card/file that still states the old fact (cross-card when two cards share a decision).
- `docs/tasks/<card>/{spec,plan,todo}.md` + knowledge entry: **append** dated supersede notes beside the old decision; never delete history.
- Re-grep the changed identifier and stale markers — zero remaining statements of the old state (task-docs sync rules).

### 3. API

- `openapi-doc` first — report drift; for each drift decide direction with CAPTURE evidence (code correct → reconcile spec; spec correct → fix code, not this flow).
- Semantic rules (`business_logic`, remarks, idempotency wording, fee rules) come from the **ingested knowledge / task D-notes**, never invented from Go.
- Structural surface only via `api-spec` **Update-from-code** (routes / fields / types); preserve hand-authored M/O, `business_logic`, `remark`, `errors`.
- Append `docs/api/VERSION.md`. Contract changed → `open-collection` when the collection exists.

### 4. VERIFY

- **GATE (machine)**: `apispeccheck` + `openapi-doc` drift = 0.
- Grep remaining stale wording (old composite keys, superseded decision ids) across tests / e2e / bruno / task docs — zero hits, or listed as out-of-scope with reason.
- Code changes only if VERIFY finds a real mismatch with the new SOT → hand off to BUG or FEATURE BUILD; RECONCILE does not invent product fixes.

Stop. User commits. No MR unless they ask.

## Task-docs sync

A card's `spec.md`, `plan.md`, and `todo.md` are one record split across files. When a fact changes, update **every** file that states it in the same pass — never only the nearest one. Ticking `todo.md` while `plan.md` still reads "blocked" plants a contradiction the next session will read and act on.

- **Triggers**: a source is ingested, an open question is resolved, a decision is made mid-flow (a user answer in chat counts), scope changes, a task changes state, a risk resolves.
- **Sweep**: `docs/tasks/<card>/{spec,plan,todo}.md`, plus the `docs/knowledge/` entry and its `INDEX.md`.
- **Append, never erase**: a dated note is a changelog line and is correct for its date — add the new dated note beside it instead of rewriting it.
- **Verify**: re-grep the changed identifier and the stale markers (`⛔`, "blocked", "TBD", "not yet ingested") — zero remaining statements of the old state. Grep finds identifiers, not counters: walk the file list too, since "N ingests remaining" summary lines carry no identifier.

## Gates

| Gate | Kind | Decider |
|---|---|---|
| Spec + plan approval | human | user |
| Decision evidence (RECONCILE CAPTURE) | human | user — source + who/why/scope before any KB write |
| AC coverage | machine | `e2echeck.py` |
| Unit coverage | machine | repo coverage command ≥ 80% |
| API contract | machine | `apispeccheck.py` + drift report |
| MR / ship | human | user |

`assets/neocheck.py <repo> <card>` runs all three machine gates and prints one table — use it
before claiming a card is done, and paste its output as the evidence. It applies the coverage
threshold itself, so a repo whose own target only *reports* a percentage is still gated. It does
**not** cover the judgment gates; it lists them as outstanding.

Before marking any task or card done:

| Touched | Required, already run this session |
|---|---|
| Production code | Package/unit tests for the touched package, green — plus the coverage gate before the card is done |
| Contract surface / HTTP-observable wire change | **Contract doc close** — `openapi-doc` drift = 0 (+ `api-spec` / RECONCILE as directed above). No close-out without the verdict. |
| `docs/api/` / API contract | `api-spec` verify (`apispeccheck` + its three-layer check) |
| HTTP-observable AC | `e2e-playwright` / `e2echeck` |
| DB migration, config, or a public contract | Backward-compat against the deployed version checked; rollback path stated |
| Untrusted input, auth, secrets, money, PII | REVIEW's security axis run and reported |
| Any fact in `docs/tasks/<card>/` changed | Task-docs sync swept and re-grepped |
| MR | Through `gitlab` per the MR step |

Everything else runs continuously. A blocker stops immediately with one precise question.

## Rationalizations

| Thought | Reality |
|---|---|
| "Too small for the flow" | Short flow, not no flow. |
| "ACs are clear, skip ALIGN" | Only if the open-decision list is empty — produce it first. |
| "I'll write tests after" | BUILD is `tdd`. Red test first. |
| "I remember this API" | Grounding 2–3: evidence path or ingest. |
| "Skip the profile on a strong model" | Profile is always on. Strong models still hallucinate contracts; gates + evidence are cheap insurance. |
| "Fresh-eyes is overkill" | Catches invented APIs before DOC/MR. If no subagent, do a second self-pass on the diff only. |
| "Small / known answer / type-only / e2e later — implement directly" | **Forbidden.** Load + follow the matching skill before the first edit. Size and confidence are not exceptions. |
| "Short conversational ask, no card — skip the flow" | A behavior/code change enters BUILD and its skill gates regardless of phrasing. Short request ≠ no skill. |
| "Write spec + plan first, draft the api-spec after" | API is step 3, SPEC + PLAN is step 4. A plan written before the contract plans against guessed fields. |
| "Tests pass, so coverage is fine" | Unstated is unmeasured. Run the coverage command and report the number, or the gate did not happen. |
| "Coverage is short — exclude the generated package" | Widening an exclusion manufactures the threshold. Write the tests. |
| "I ticked todo.md, that's the record" | Sweep spec + plan + knowledge in the same pass, then re-grep. A half-synced card misleads the next session. |
| "Code is right — just Update-from-code / fix api-spec" | Code ≠ requirement. RECONCILE: CAPTURE → INGEST → ALIGN, then structural API sync. Semantic rules never come from Go alone. |
| "Commit message is enough evidence" | Lacks who/why/scope. CAPTURE still asks; stop if unanswered. |
| "Only docs/api is stale" | Task D-notes and knowledge still state the old rule — next session will reverse the api fix. Sweep all three layers. |
| "Bug/hotfix — skip DOC, code is enough" | Contract doc close is mandatory when the trigger matches. Unstated drift = skipped = not done. |
| "Internal-only, so I skipped without saying" | If not triggered, say so in one line. Silence is treated as a skipped gate. |
