---
name: using-neo
description: Routes engineering work through neo's single adaptive entry point. Use when starting any task, selecting a workflow, running one phase, or driving work end to end from the repository's current state.
---

# Using Neo

## Overview

`using-neo` is neo's canonical entry point. It identifies the user's intent,
loads only the workflow needed for that intent, delegates method work to the
relevant specialist skills, and preserves the lifecycle's approval and safety
gates.

## Single Entry Point

Start every neo workflow here. Do not ask the user to choose among
phase-specific entry points or recreate separate phase commands.

Use this order of precedence:

1. Follow an explicitly requested scope such as review, test, plan, or ship.
2. If the user asks for end-to-end work or to resume a feature, detect the
   current lifecycle phase from repository state.
3. Otherwise, select the narrowest workflow that fully satisfies the request.
4. Load only the directly linked phase reference needed for that workflow.
5. Invoke the method skills named by that reference; do not duplicate them.

Never expand a focused request into the full lifecycle without the user asking
for end-to-end work. Repository rules and explicit user instructions override
the defaults here.

## Adaptive Routing

Read existing context before routing: `AGENTS.md` or equivalent guidance,
`docs/knowledge/INDEX.md`, relevant `docs/tasks/<card>/` artifacts, and the
code/configuration in scope. Do not ask for facts the repository already
contains.

```text
Task arrives
    |
    |-- Named external source not curated? -> Ingest
    |-- Intent still unclear? --------------> interview-me
    |-- Rough idea needs variants? ---------> idea-refine
    |-- New feature or significant change? -> Define
    |     `-- HTTP contract? ---------------> api-spec Draft
    |-- Approved spec needs tasks? ---------> Plan
    |-- Implementing approved work? --------> Build
    |     |-- UI? --------------------------> frontend-ui-engineering
    |     |-- Public interface? ------------> api-and-interface-design
    |     |-- Official docs required? ------> source-driven-development
    |     `-- High stakes/uncertain? --------> doubt-driven-development
    |-- Testing or proving a bug? ----------> Verify
    |     |-- Browser runtime? -------------> browser-testing-with-devtools
    |     `-- AC-driven HTTP e2e? ----------> e2e-playwright
    |-- Unexpected failure? ----------------> debugging-and-error-recovery
    |-- Reviewing a change? ----------------> Review
    |     |-- Too complex? -----------------> Simplify
    |     |-- Security focus? --------------> security-and-hardening
    |     `-- Performance focus? -----------> performance-optimization
    |            `-- Web app audit? --------> Webperf
    |-- Preparing atomic commits? ----------> Commit
    |-- CI/CD, ADR, observability, migration? -> matching method skill
    `-- Production readiness/deploy? --------> Ship
```

Load the matching phase contract before acting:

| Workflow | Required reference |
|---|---|
| Ingest, Define, Plan | `references/ingest-define-plan.md` |
| Build, Verify | `references/build-verify.md` |
| Review, Simplify, Commit, Webperf, Ship | `references/review-ship.md` |

The Webperf fallback also uses the bundled
`references/performance-checklist.md` when browser/subagent tooling is absent.

## Modes and Lifecycle Control

### Adaptive default

With no mode, infer the workflow from the request:

- A focused request runs only the selected workflow and stops after reporting
  its result.
- A request to implement an approved full plan selects Build auto. A request
  for the next task selects Build single.
- If Build scope is ambiguous and multiple tasks remain, ask whether to run the
  whole plan (`auto`) or the next task (`single`).
- An end-to-end request detects the earliest incomplete phase, runs it, then
  offers `go`, `stop`, or `auto` at each lifecycle boundary.

### Explicit modes

- **`using-neo single`** (also `one` or `next`) runs one unit and stops. In
  Build, the unit is the next pending task; elsewhere it is the selected phase.
- **`using-neo auto`** (also `all`) gets one approval, then advances without
  routine boundary prompts. It does not delegate material decisions discovered
  during execution.

Mode changes autonomy, not quality. Tests, verification, documentation sync,
and risk checks remain mandatory.

### Lifecycle path and state detection

```text
ingest (conditional) -> define -> plan -> build -> verify -> review
                     -> simplify -> commit -> ship
```

Webperf is a conditional branch around Review/Ship for browser-facing web apps,
not a mandatory linear phase.

For end-to-end or resume requests, start at the earliest incomplete output:

| Repository state | Start at |
|---|---|
| Named source absent from `docs/knowledge/` | Ingest |
| Missing or unapproved `docs/tasks/<card>/spec.md` | Define |
| Missing `plan.md` or `todo.md` | Plan |
| Pending tasks or missing implementation/tests | Build, then Verify |
| Implementation complete and tests green | Review, then Simplify |
| Review gates clear | Commit, then Ship |

Ask for `<card>` only when more than one feature is plausible and repository
state cannot disambiguate it.

### Boundaries and hard stops

- Default end-to-end mode pauses after each phase with `go / stop / auto`.
- Auto mode stops at the standalone **commit** phase, **ship**, any unresolved
  **blocker**, any newly discovered **material decision**, or any
  **high-risk**/irreversible step such as auth, payments, secrets, destructive
  migration, deletion, or deploy.
- Build auto's per-task commits are covered only when the user explicitly
  approved that Build mode and repository guidance permits agent commits.
  Otherwise leave commits to the user.
- Never deploy, push, rewrite shared history, or accept a Critical finding
  without explicit authorization.
- After every phase, sync decisions, scope changes, resolved questions, source
  updates, and task status across all relevant task documents per
  `references/task-docs-sync.md`.

### Decision stops in auto mode

Treat unexpected evidence as a decision stop when continuing would require a
material decision that the user has not already approved. A material decision
changes approved scope or ACs, task boundaries or dependency order,
architecture, the data model, a public interface, persistence strategy, or the
safety posture; it also includes choosing among remedies with materially
different tradeoffs.

At a decision stop:

1. Preserve the failing evidence and stop before implementing the proposed
   change.
2. Synchronize the paused status and discovered issue across affected task
   documents.
3. State the issue, impact, evidence, and recommended remedy or concrete
   alternatives.
4. Ask for explicit approval and resume only after the user decides.

Continue automatically through routine bounded fixes that preserve every
approved decision, such as formatting, syntax repair, deterministic
regeneration, or a source-of-truth-mandated correction. If the fix would alter
an approved decision, the decision stop takes precedence even when one remedy
looks obvious. For example, concurrency evidence that invalidates an approved
persistence strategy requires a decision stop before redesigning that strategy.

## Core Operating Behaviors

### Surface assumptions

Before non-trivial implementation, state assumptions about requirements,
architecture, and scope. Stop and ask when an unresolved choice would materially
change the result.

### Push back with evidence

Name concrete downsides and safer alternatives when an approach creates a clear
risk. Follow the user's final decision once the tradeoff is understood.

### Keep changes minimal

Implement the smallest complete solution. Do not refactor adjacent code, remove
unrelated dead code, or add speculative flexibility.

### Verify before completion

Every selected method skill's verification must pass. Apply the project-wide
Definition of Done in `references/definition-of-done.md` in addition to task
acceptance criteria.

## Failure Modes to Avoid

- Loading every phase reference for a focused task.
- Presenting a menu of methodologies instead of routing from intent.
- Treating auto as permission to skip tests, commit, ship, or risk gates.
- Treating auto approval as authority to make a material decision discovered
  mid-flow.
- Reimplementing method-skill guidance inside this router.
- Asking questions already answered by the knowledge base or repository.
- Leaving task documents contradictory after a decision or scope change.

## Verification

- The chosen workflow matches explicit intent and repository state.
- Only the relevant phase reference and method skills were loaded.
- Adaptive, single, and auto modes followed their boundary rules.
- Commit, ship, blocker, material-decision, and high-risk stops were honored.
- Phase-specific verification and the Definition of Done passed.
- Task artifacts remain synchronized.
