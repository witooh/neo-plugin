---
name: using-neo
description: Routes engineering work through neo's single entry point. Detects intent, drives the matching flow (ingest, align, api, spec, build, verify, review, doc, MR), enforces machine gates, and always applies the high-hallucination profile (small slices, hard evidence, fresh-eyes review). Use when starting any task.
---

# Using Neo

Single entry router. Every request routes here first: detect intent, run the matching flow, stop only at gates. The flow drives itself — never present a menu of methodologies.

## Layers

- **Router** (this skill): when things happen — intent, flow order, gates, resume, model profile.
- **Method layer** (vendored from [mattpocock/skills](https://github.com/mattpocock/skills) via `sync-mattpocock`): `grilling`, `domain-modeling`, `tdd`, `code-review`, `diagnosing-bugs`, `research`, `prototype`, `codebase-design`, `resolving-merge-conflicts`. Live under `skills/<name>/`.
- **Domain layer** (neo-owned): `api-spec`, `e2e-playwright`, `openapi-doc`, `open-collection`, `confluence-api-doc`, `markitdown`, `init-project`, `migrate-project`, `atlassian`, `gitlab`.

## Method-layer availability

Method skills ship inside this plugin. If `tdd` / `grilling` / `code-review` are missing, tell the maintainer once to run `sync-mattpocock`, then continue with inline minimums — do not block:

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

**Default for every session and every model.** No model detection. Payment/external-API work and unreliable models both need the same net; detection is flaky and fails open (profile off when you need it most).

Announce once per session: `profile: high-hallucination`.

**Rules (on top of grounding 1–6):**

| Area | Behavior |
|---|---|
| Slice size | One todo item = one edit surface (one package or one file cluster). No multi-package batches. |
| BUILD verify | After **every** green test: run package tests for the touched package (not only at end of all tasks). |
| API / DOC | Every new/changed request/response field lists its evidence path in the working notes or spec remark. |
| REVIEW | Run `code-review`, **then** spawn one fresh-context subagent on the diff with only: “list incorrect claims, invented APIs, missing tests, convention breaks — evidence required”. Fix before DOC. |
| BUG | Hypothesis must cite a `file:line` or log line before any fix. Concurrent/race bugs require a failing repro test first — no speculative locks. |
| Narration | Prefer short status + evidence paths over long reasoning. If unsure, stop with one question. |
| Recovery | On a wrong turn: revert or re-read source of truth, do not stack another guess on top. |

There is no opt-out flag. If a step in the table is impossible in the harness (e.g. no subagent), do the closest equivalent (second self-pass with only the diff in context) and say so.

## Intent table

| Signal | Route |
|---|---|
| Card key, feature, behavior change | FEATURE flow |
| Bug, failing test, unexpected behavior | BUG flow |
| Refactor, simplification | REFACTOR flow |
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

- `docs/tasks/<card>/spec.md` (objective, ACs, non-goals), `plan.md`, `todo.md`.
- Plan tasks must be single-surface slices (profile).
- **GATE (human)**: present spec + plan; one approval runs through to the MR gate.

### 5. BUILD

- Per task: `tdd` red-green-refactor; typecheck/lint on green; tick `todo.md`.
- Read the matching `.kiro/steering/` guide before writing in a layer; `new-feature-checklist.md` when present.
- Package-level tests after every task (profile table).

### 6. VERIFY

- Unit: `make test` (or repo equivalent) + coverage.
- E2E: `e2e-playwright` per-AC on isolated stack (docker-compose + mockoon).
- **GATE (machine)**: `e2echeck` every HTTP-observable AC; `govulncheck` when available.
- Failures → `diagnosing-bugs` — no blind retries.

### 7. REVIEW

- `code-review` on the full diff; fix; re-verify.
- Mandatory fresh-eyes pass after `code-review` (profile table).

### 8. DOC

- `api-spec` sync-back; `openapi-doc` drift = 0.
- **GATE (machine)**: `apispeccheck` passes.
- Contract changed → `open-collection` + `VERSION.md`. Confluence only on request.

### 9. MR

- **GATE (human)**: final diff summary + MR title/body; wait.
- On confirm: `gitlab` push + MR to `develop`. Never commit/push before this gate.

## BUG flow

1. Ingest report/evidence.
2. `diagnosing-bugs` — hypothesis needs `file:line` or log cite before fix.
3. `tdd` failing repro first (concurrent test for races), then fix to green.
4. HTTP-observable → e2e regression tagged to the card.
5. `code-review` + fresh-eyes. Stop — user commits.

## REFACTOR flow

1. Confirm behavior-preserving scope.
2. `codebase-design` for target shape.
3. Small steps; tests green after each (single-surface slices).
4. `code-review` + fresh-eyes. Stop.

## Gates

| Gate | Kind | Decider |
|---|---|---|
| Spec + plan approval | human | user |
| AC coverage | machine | `e2echeck.py` |
| API contract | machine | `apispeccheck.py` + drift report |
| MR / ship | human | user |

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
