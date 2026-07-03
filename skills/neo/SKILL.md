---
name: neo
description: >
  Single entry point that drives the whole neo-* lifecycle from one command.
  Detects the current phase from repo state (docs/knowledge/,
  docs/tasks/<card>/spec.md, plan.md, code, tests) and runs each phase by
  delegating to its neo-<phase> skill in turn — ingest, spec, plan, build, test,
  review, code-simplify, commit, ship (webperf is a conditional branch for web
  apps). It orchestrates the phases, never reimplements them. Default `/neo` stops
  at every phase boundary and asks go / stop / auto; `/neo auto` runs after one
  approval, stopping only at commit, ship, blockers, or high-risk steps. Use when
  you want to run the full neo workflow from one entry, drive a feature from spec
  to ship, or resume one mid-flow. Route elsewhere: for a single phase, invoke that
  neo-<phase> directly; to discover any skill including non-neo-* ones (api-spec,
  security, frontend) use using-neo.
---

# Neo — the neo-* lifecycle driver

## Overview

Neo is the single entry point that drives the neo-* workflow end to end. It is a
thin orchestrator: it detects which phase a feature is in, runs that phase by
delegating to the matching `neo-<phase>` skill, and hands control back to you at
each phase boundary. It does **not** reimplement any phase — every `neo-<phase>`
owns its own method and gates; neo only sequences them and manages the boundaries.

It coexists with `using-neo`, and they have different scopes. `using-neo` is the
broad discovery router over *every* skill — including non-neo-* ones like
`api-spec`, `security-and-hardening`, and `frontend-ui-engineering`. Neo drives
only the neo-* lifecycle. Neo is not a replacement for `using-neo`.

## When to Use

- When you want to run the full neo workflow from one command instead of invoking
  `/neo-spec`, `/neo-plan`, `/neo-build`… one at a time.
- When driving a feature from spec to ship, or resuming one mid-flow.
- When you invoke `/neo` or `/neo auto`.
- Route elsewhere: for a single phase, invoke that `neo-<phase>` directly
  (`neo-spec`, `neo-build`, …) — neo does not replace them; to discover any skill
  including non-neo-* ones → `using-neo`.

## The Workflow

### The phase line

```
ingest(cond) → spec → plan → build → test → review → code-simplify → commit → ship
```

- **ingest** runs only if the request names an external source not yet curated in
  `docs/knowledge/`; otherwise skip it.
- **webperf** is a conditional branch, not a linear step — offer it around
  review/ship only when the target is a web app.

### 1. Detect where to start

Start at the earliest phase whose output is missing or incomplete — never redo a
finished one:

| Check | If missing / incomplete → start at |
|---|---|
| named source not in `docs/knowledge/` | ingest |
| `docs/tasks/<card>/spec.md` | spec |
| `docs/tasks/<card>/plan.md` | plan |
| plan has pending tasks, or code/tests missing | build → test |
| code built and tests green | review → code-simplify → commit → ship (in order) |

If you can't tell which feature this is, ask for the `<card>` (feature name or
JIRA id) before starting.

### 2. Run the current phase

Delegate to the matching `neo-<phase>` skill and let it run its own method and
internal gates — `neo-spec` needs human sign-off, `neo-build auto` has its own
single approval, and so on. Neo does not duplicate any of that; it just invokes
the phase and reads back what it produced.

### 3. Gate at the boundary

When a phase finishes, summarize what it produced, then ask before advancing.

- **Default `/neo` — ask every boundary.** Offer three choices every time:
  - **go** → run the next phase, then stop and ask again at the next boundary.
  - **stop** → halt here.
  - **auto** → run the rest of the flow unattended from here (switch to auto mode).
- **`/neo auto` — flow after one approval.** Take one approval up front, then
  advance through phases without asking, **stopping only** at: `commit`; `ship`; a
  blocker (→ `debugging-and-error-recovery`); or a high-risk/irreversible step —
  auth, destructive migration, payments, deletions, deploys, secrets (→
  `doubt-driven-development`, get explicit sign-off).

`commit` and `ship` are always gated, in **both** modes — never commit or deploy
without an explicit go.

### 4. Drive, don't menu

Pick the next phase yourself from the detected state; do not present a
"choose a methodology" menu. The user approves, redirects, or switches to auto —
they don't navigate the workflow by hand.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I'll just run every phase without stopping." | Default `/neo` stops at every boundary; only `/neo auto` (or choosing `auto` mid-flow) skips the asks — and even then commit/ship still gate. |
| "The driver should reimplement the phase to save a hop." | Each `neo-<phase>` owns its method and gates; neo only sequences them. Duplicating a phase creates two sources of truth that drift. |
| "A spec probably doesn't exist, I'll start at build." | Detect the phase from repo state first — don't skip spec/plan on an assumption. |
| "auto means I can commit and ship unattended." | commit and ship are hard gates in every mode; auto also stops at any blocker or high-risk step. |
| "This is like using-neo, I'll route to any skill." | Neo drives only the neo-* lifecycle; broad discovery (incl. non-neo-*) is `using-neo`'s job. |

## Red Flags

- Reimplementing a phase's logic inside neo instead of delegating to its `neo-<phase>`.
- Committing or shipping in auto mode without an explicit go.
- Presenting a methodology menu instead of driving to the next phase.
- Skipping phase detection and starting at the wrong phase (redoing finished work).
- Treating `neo` as a replacement for `using-neo` — they have different scopes.

## Verification

- The phase that ran matches the repo's current state (no finished phase redone).
- Each phase ran via its `neo-<phase>` skill, and that skill's own verification passed.
- In default mode every boundary offered go / stop / auto; in auto mode only
  commit, ship, blockers, and high-risk steps stopped.
- The project-wide Definition of Done that `using-neo` enforces holds for each
  phase's change, on top of that phase's own acceptance criteria.
