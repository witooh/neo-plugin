---
name: neo-spec
description: >
  Entry point for the Define phase of the neo workflow — produce a structured
  spec before any code. Orchestrates `spec-driven-development` as the method,
  then runs the ingest-first gate (detect an unread named source, offer
  `markitdown`), loads docs/knowledge/ context, writes docs/tasks/<card>/spec.md
  with a stable-ID Acceptance Criteria section (AC-001…) and a Sources section,
  and for HTTP features invokes `api-spec` in Draft mode as the single source of
  truth for the contract. Use when starting a new feature or change in a neo
  project, when you need AC IDs downstream tests trace to, or when you invoke
  /neo-spec. The method itself is `spec-driven-development`.
---

# Neo Spec — spec-driven Define entry point

## Overview

This is the neo entry point for the Define phase. It orchestrates
`spec-driven-development` as the underlying method and layers neo's conventions
on top: the ingest-first gate, `docs/knowledge/` context loading, the
`docs/tasks/<card>/spec.md` layout with stable acceptance-criteria IDs and a
Sources section, and — for HTTP features — an `api-spec` Draft that becomes the
single source of truth for the contract. It does **not** reimplement the spec
method; the method lives in `spec-driven-development`.

## When to Use

- When starting a new project, feature, or significant change in a neo project
  and no spec exists yet.
- When you need acceptance criteria with stable IDs that `api-spec` `covers_ac`
  and downstream tests trace back to.
- When you invoke `/neo-spec`.
- Route elsewhere: for the bare spec method with no neo gate/artifacts →
  `spec-driven-development`; to capture a source first → `neo-ingest`; once a spec
  exists → `neo-plan`.

## The Workflow

1. **Ingest-first gate.** If the request names an external source (URL,
   JIRA/Confluence link, file) that isn't curated in `docs/knowledge/` yet, do
   not silently proceed: tell the user it isn't ingested, then offer to run
   `neo-ingest` (the `markitdown` skill) now or wait while they do. Continue only
   once it is curated, or the user says to proceed without it. A plain feature
   description with no external source needs no ingest.
2. **Load existing context.** Before asking the user anything, read
   `docs/knowledge/` (start with `INDEX.md`) for material relevant to this
   feature. Never ask a question the knowledge base already answers.
3. **Run `spec-driven-development`.** Ask clarifying questions (objective and
   users; core features and acceptance criteria; tech stack and constraints;
   boundaries), then generate a spec covering the six core areas.
4. **Acceptance Criteria + Sources.** Always include an `## Acceptance Criteria`
   section; if the source already lists criteria, capture every one faithfully —
   never drop, merge, or invent. Give each a stable id (`AC-001`, `AC-002`, …);
   every AC must be independently testable. Include a `## Sources` section
   linking every `docs/knowledge/` entry the spec drew on.
5. **Save + confirm.** Ask for the feature name or JIRA card id (`<card>`), save
   to `docs/tasks/<card>/spec.md`, and confirm before proceeding.
6. **HTTP features → `api-spec` Draft.** If the spec describes an HTTP API,
   invoke `api-spec` in Draft mode to author the `docs/api/` contract spec-first,
   from the acceptance criteria, before any code. Then keep the contract in one
   place: replace endpoint-contract detail in the spec with a reference to
   `docs/api/` (link `docs/api/index.md` + the relevant `<domain>/<endpoint>.yaml`).
   The spec keeps business intent and AC; `docs/api/` is the single source of truth.
7. **Amending an existing spec?** If `docs/tasks/<card>/spec.md` already exists
   and this run changes it (a scope change, a deferral, a source resolution, a
   new decision), the spec is not the only doc stating those facts — sync
   `plan.md`/`todo.md` and the `docs/knowledge/` Related blocks per
   `references/task-docs-sync.md`, so no downstream doc keeps the
   pre-amendment state.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "The knowledge base is probably empty, I'll just ask." | Read `docs/knowledge/INDEX.md` first — asking what the KB already answers wastes the context the user deliberately ingested. |
| "I'll number the acceptance criteria later." | Stable `AC-NNN` IDs are what `api-spec` `covers_ac` and downstream tests trace to — assign them now. |
| "I'll put the endpoint shapes in the spec too, for convenience." | The contract lives in `docs/api/` only; duplicating it in the spec creates two sources of truth that drift. |
| "No source is linked, so there's nothing to ingest." | A named-but-unread URL/JIRA is exactly what the ingest-first gate is for. |

## Red Flags

- Writing spec content before reading `docs/knowledge/`.
- Acceptance criteria with no stable IDs, or invented ACs not traceable to a source.
- Endpoint/field tables duplicated in both `spec.md` and `docs/api/`.
- Proceeding on a named-but-unread source without offering ingest.

## Verification

- `spec-driven-development`'s own checklist passed (six core areas, human-approved).
- `docs/tasks/<card>/spec.md` is written with an `## Acceptance Criteria` section
  of independently-testable, stable-ID (`AC-NNN`) criteria and a `## Sources` section.
- For HTTP features, `api-spec` authored `docs/api/` and the spec references it
  (no duplicated contract).
- If the run amended an existing spec, the task-docs sweep passed
  (`references/task-docs-sync.md`): no `plan.md`/`todo.md` line still states
  the pre-amendment fact.
