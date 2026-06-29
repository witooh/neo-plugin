---
name: neo
description: >
  Customized `using-agent-skills` meta-skill wrapped in loop engineering. neo forks the
  upstream discovery router (flowchart, 6 Core Operating Behaviors, spec→ship lifecycle)
  and drives it inside Addy Osmani's *loop engineering*: it turns a task into a recursive
  goal with an OBSERVABLE exit condition, then iterates — act, check with a fresh-context
  maker-checker, record to STATE.md memory — until "done" is proven, with four independent
  exits (verifier, iteration cap, budget, no-progress) and a
  human gate at commit/PR. Three local router additions: `ingest` (Define), `api-spec` (Define + Ship),
  and `e2e-playwright` (Verify — HTTP e2e per AC). The lifecycle skills it
  points to ship in the separately-installed upstream agent-skills plugin (a prerequisite).
  Triggers: "/neo", "neo", a JIRA card id or URL, a GitLab MR URL, or any task that benefits
  from a recursive-goal loop with durable memory and a human gate; resume with
  "/neo continue <slug>". NOT for single-file fixes, quick questions, or pure research.
compatibility:
  environment: claude-code
  tools:
    - Read
    - Glob
    - Grep
    - Edit
    - Write
    - Bash
    - Skill
    - Agent
    - AskUserQuestion
---

## Overview

`neo` is the `using-agent-skills` meta-skill in a **customized form** — its discovery router
(the skill-selection flowchart, the 6 Core Operating Behaviors, the spec→ship Lifecycle
Sequence) is adapted from the upstream agent-skills plugin and then **wrapped in a loop**.

Agent Skills represents a curated collection of engineering workflow competencies arranged by
development phase. Each skill codifies a specific process that experienced engineers follow.
This meta-skill facilitates identifying and applying the appropriate skill for your current
task.

The lifecycle skills this router points to — `spec-driven-development`,
`test-driven-development`, and the rest — live in the **separately-installed upstream
agent-skills plugin** (`github.com/addyosmani/agent-skills`), a prerequisite. neo adds only
three of its own skills into the router: `ingest` (Define), `api-spec` (Define draft + Ship
reconcile), and `e2e-playwright` (Verify). What makes neo
more than the upstream meta-skill is the **`## Loop Engineering`** section below: it turns
whatever task arrives into a recursive goal and drives this lifecycle until a checkable exit
condition is provably met.

## Loop Engineering

This is the outer driver that wraps everything below. The skill is no longer writing one good
prompt — it is **designing a loop whose "done" actually means done** (Addy Osmani, *loop
engineering*; the primer lives in `LOOP.md` at the repo root). neo turns the task into a
**recursive goal** and iterates the lifecycle — act, check, decide, repeat — until a checkable
exit is provably met.

**Run this loop on every neo invocation — it is mandatory, not a concept.** First move, before
any source-code Edit/Write/Bash: create or resume `docs/tasks/<slug>/STATE.md`, write the goal +
the observable exit condition, and **announce them to the user as neo's first output**.
`STATE.md` on disk is the proof the loop ran; if you are about to edit source and it does not
exist, STOP — you skipped the loop. A skipped phase is a recorded `waiver:` in STATE.md, never a
silent skip (the process-integrity gate rejects a silent skip); the spec/design artifact is
**non-waivable for feature work**. The full operational contract is in
`references/loop-engineering.md`; the durable-memory shape is in `references/state-schema.md`
(+ `templates/STATE.md`).

1. **Frame the recursive goal + an OBSERVABLE exit condition.** "Make the code better" is not
   a loop goal; "all tests pass", "the linter returns zero errors", "every acceptance
   criterion is traced by a passing test" are. The exit condition **augments** Core Operating
   Behavior #6 ("Verify, Don't Assume") — it never replaces it. Each criterion is
   evidence-backed and tagged `verify_method: machine | judgment`.

2. **Ingest-first.** If the goal needs knowledge that is not yet on disk, route to the
   `ingest` skill (the Define-phase "have a context, need knowledge" branch) *before*
   building. External memory is the sixth building block: the agent forgets, the repo doesn't.

3. **Iterate the lifecycle — neo drives it; the user does not pick it.** Run one pass through
   the Skill Discovery flowchart + Lifecycle Sequence below, appending each step to durable
   memory at `docs/tasks/<slug>/STATE.md`. The phase order is neo's to **execute**, never a menu
   to offer the user: do not ask which methodology to run ("vertical-slice vs build-all-at-once
   vs plan-first"), and never surface an option that contradicts a lifecycle skill (building a
   whole feature at once contradicts `incremental-implementation`). This forbids offloading the
   *methodology* choice the lifecycle already makes — it does **not** suppress genuine clarifying
   questions about the goal or requirements (Behaviors #1/#2). neo's only user-facing pauses are
   three, and it judges each itself: goal/intent ambiguity, the **large-feature plan checkpoint**
   (one approval after Plan before Build, for a feature spanning multiple acceptance criteria or
   layers — small tasks skip it), and the commit/PR human gate. A phase is waived only for work
   that does **not add or change behavior** (a recorded `waiver:`); behavior-changing work is a
   feature that runs the full flow (Define non-waivable). See `references/loop-engineering.md`.

4. **Check with a fresh maker-checker.** A **separate, fresh-context** checker — not the agent
   that did the work — verifies the exit condition against *evidence*. Self-assessment is the
   weakest link in a loop; an independent checker is the fix. Intercept premature exit: if the
   model declares "done", re-check the real criteria and reinject the task if they are not met.
   The checker also runs the **process-integrity gate** — every change-iteration traces to a
   `ran:` or `waiver:`, and Define precedes Build on feature work — before any exit may pass
   (see `references/loop-engineering.md`).

5. **Decide — four independent exits, not one:**
   - **Verifier confirms the goal is met** → go to the human gate.
   - **Not met, but progress was made** → loop again.
   - **No-progress** (the last ~3 iterations log `exit_met: no` with the same unmet `next:`
     gap), **iteration cap** reached, or **token / wall-clock budget** exceeded → stop and
     escalate `STUCK`. A loop with no exit is not autonomous work — it is open-ended token
     spend.

6. **Human gate at commit/PR.** A human stays in the design-and-review path; neo does not
   auto-commit or auto-open MRs. Connectors (`gitlab`, `atlassian`) are invoked here, not
   auto-fired. See `references/loop-engineering.md` for the gate's escalation shape.

**The three risks** (carry them consciously; mitigations in `references/loop-engineering.md`):
**weak verification** (a "done" claim is still not proof), **comprehension debt** (the loop
ships faster than you can read — so read what it made), and **cognitive surrender** (designing
the loop must sharpen judgment, not replace it). Two people can build the same loop and get
opposite results; the loop does not know the difference — you do.

## Skill Discovery

When a task arrives, identify the development phase and apply the corresponding skill:

```
Task arrives
    │
    ├── Don't know what you want yet? ──────→ interview-me
    ├── Have a rough concept, need variants? → idea-refine
    ├── Have a context, need knowledge? ────→ ingest
    ├── New project/feature/change? ──→ spec-driven-development
    ├── Designing an HTTP API (draft from AC)? ──→ api-spec
    ├── Have a spec, need tasks? ──────→ planning-and-task-breakdown
    ├── Implementing code? ────────────→ incremental-implementation
    │   ├── UI work? ─────────────────→ frontend-ui-engineering
    │   ├── API work? ────────────────→ api-and-interface-design
    │   ├── Need better context? ─────→ context-engineering
    │   ├── Need doc-verified code? ───→ source-driven-development
    │   └── Stakes high / unfamiliar code? ──→ doubt-driven-development
    ├── Writing/running tests? ────────→ test-driven-development
    │   ├── Browser-based? ───────────→ browser-testing-with-devtools
    │   └── HTTP/API e2e from AC? ────→ e2e-playwright
    ├── Something broke? ──────────────→ debugging-and-error-recovery
    ├── Reviewing code? ───────────────→ code-review-and-quality
    │   ├── Too complex? ─────────────→ code-simplification
    │   ├── Security concerns? ───────→ security-and-hardening
    │   └── Performance concerns? ────→ performance-optimization
    ├── Committing/branching? ─────────→ git-workflow-and-versioning
    ├── Deprecating/migrating? ────────→ deprecation-and-migration
    ├── Writing docs/ADRs? ───────────→ documentation-and-adrs
    ├── update api-spec? ─────────────→ api-spec
    └── Adding logs/metrics/alerts? ───→ observability-and-instrumentation
```

These additions are neo's own — `ingest` (Define), `api-spec` (Define draft + Ship reconcile), and
`e2e-playwright` (Verify — HTTP e2e per acceptance criterion); every other branch routes to a skill
in the upstream agent-skills plugin.

## Core Operating Behaviors

These behaviors apply at all times, across all skills. They are non-negotiable.

### 1. Surface Assumptions

Before implementing anything non-trivial, explicitly state your assumptions:

```
ASSUMPTIONS I'M MAKING:
1. [assumption about requirements]
2. [assumption about architecture]
3. [assumption about scope]
→ Correct me now or I'll proceed with these.
```

Don't silently fill in ambiguous requirements. The most common failure mode is making wrong
assumptions and running with them unchecked. Surface uncertainty early — it's cheaper than
rework.

### 2. Manage Confusion Actively

When you encounter inconsistencies, conflicting requirements, or unclear specifications:

1. **STOP.** Do not proceed with a guess.
2. Name the specific confusion.
3. Present the tradeoff or ask the clarifying question.
4. Wait for resolution before continuing.

**Bad:** Silently picking one interpretation and hoping it's right.
**Good:** "I see X in the spec but Y in the existing code. Which takes precedence?"

### 3. Push Back When Warranted

You are not a yes-machine. When an approach has clear problems:

- Point out the issue directly
- Explain the concrete downside (quantify when possible — "this adds ~200ms latency" not "this might be slower")
- Propose an alternative
- Accept the human's decision if they override with full information

Sycophancy is a failure mode. "Of course!" followed by implementing a bad idea helps no one.
Honest technical disagreement is more valuable than false agreement.

### 4. Enforce Simplicity

Your natural tendency is to overcomplicate. Actively resist it.

Before finishing any implementation, ask:
- Can this be done in fewer lines?
- Are these abstractions earning their complexity?
- Would a staff engineer look at this and say "why didn't you just..."?

If you build 1000 lines and 100 would suffice, you have failed. Prefer the boring, obvious
solution. Cleverness is expensive.

### 5. Maintain Scope Discipline

Touch only what you're asked to touch.

Do NOT:
- Remove comments you don't understand
- "Clean up" code orthogonal to the task
- Refactor adjacent systems as a side effect
- Delete code that seems unused without explicit approval
- Add features not in the spec because they "seem useful"

Your job is surgical precision, not unsolicited renovation.

### 6. Verify, Don't Assume

Every skill includes a verification step. A task is not complete until verification passes.
"Seems right" is never sufficient — there must be evidence (passing tests, build output,
runtime data).

Per-skill verification is the local check. The project-wide bar that applies to *every*
change, regardless of which skill is active, is the **Definition of Done**: tests pass, no
regressions, behavior verified at runtime, docs updated. It complements each task's acceptance
criteria rather than replacing them. Under neo, the loop's exit condition (see
`## Loop Engineering`) AUGMENTS this bar — the fresh-context checker verifies it against
evidence before the loop may exit.

## Failure Modes to Avoid

These are the subtle errors that look like productivity but create problems:

1. Making wrong assumptions without checking
2. Not managing your own confusion — plowing ahead when lost
3. Not surfacing inconsistencies you notice
4. Not presenting tradeoffs on non-obvious decisions
5. Being sycophantic ("Of course!") to approaches with clear problems
6. Overcomplicating code and APIs
7. Modifying code or comments orthogonal to the task
8. Removing things you don't fully understand
9. Building without a spec because "it's obvious"
10. Skipping verification because "it looks right"

## Skill Rules

1. **Check for an applicable skill before starting work.** Skills encode processes that prevent common mistakes.

2. **Skills are workflows, not suggestions.** Follow the steps in order. Don't skip verification steps.

3. **Multiple skills can apply.** A feature implementation might involve `idea-refine` → `spec-driven-development` → `planning-and-task-breakdown` → `incremental-implementation` → `test-driven-development` → `code-review-and-quality` → `code-simplification` → `git-workflow-and-versioning` in sequence.

4. **When in doubt, start with a spec.** If the task is non-trivial and there's no spec, begin with `spec-driven-development`.

## Lifecycle Sequence

For a complete feature, the typical skill sequence is:

```
1.  interview-me                → Extract what the user actually wants
2.  idea-refine                 → Refine vague ideas
3.  ingest                      → Pull external sources into docs/knowledge/ (have a context, need knowledge)
4.  spec-driven-development     → Define what we're building
5.  api-spec (draft)            → HTTP work: draft the docs/api/ contract from the AC, before code (Draft mode)
6.  planning-and-task-breakdown → Break into verifiable chunks
7.  context-engineering         → Load the right context
8.  source-driven-development   → Verify against official docs
9.  incremental-implementation  → Build slice by slice
10. observability-and-instrumentation → Instrument as you build (runs parallel with implementation, not after)
11. doubt-driven-development    → Cross-examine non-trivial decisions in-flight
12. test-driven-development     → Prove each slice works
13. e2e-playwright              → HTTP work: author + run one e2e per acceptance criterion
14. code-review-and-quality     → Review before merge
15. code-simplification         → Reduce unnecessary complexity while preserving behavior
16. git-workflow-and-versioning → Clean commit history
17. documentation-and-adrs      → Document decisions
18. api-spec (reconcile)        → Reconcile/update the docs/api/ spec against built code (update api-spec?)
19. deprecation-and-migration   → Retire old systems and move users safely when needed
```

Not every task needs every skill. A bug fix might only need: `debugging-and-error-recovery` →
`test-driven-development` → `code-review-and-quality`. Whatever the subset, neo wraps it in the
loop above — frame the goal, iterate, verify the exit with a fresh checker, gate at commit.

## Quick Reference

| Phase | Skill | One-Line Summary |
|-------|-------|-----------------|
| Define | interview-me | Surface what the user actually wants before any plan, spec, or code exists |
| Define | idea-refine | Refine ideas through structured divergent and convergent thinking |
| Define | ingest | Ingest an external source once into docs/knowledge/ as curated, reusable context (have a context, need knowledge) |
| Define | spec-driven-development | Requirements and acceptance criteria before code |
| Define | api-spec | Draft the custom-YAML docs/api/ contract from the AC, before code (HTTP work; Draft mode) |
| Plan | planning-and-task-breakdown | Decompose into small, verifiable tasks |
| Build | incremental-implementation | Thin vertical slices, test each before expanding |
| Build | source-driven-development | Verify against official docs before implementing |
| Build | doubt-driven-development | Adversarial fresh-context review of every non-trivial decision |
| Build | context-engineering | Right context at the right time |
| Build | frontend-ui-engineering | Production-quality UI with accessibility |
| Build | api-and-interface-design | Stable interfaces with clear contracts |
| Verify | test-driven-development | Failing test first, then make it pass |
| Verify | browser-testing-with-devtools | Chrome DevTools MCP for runtime verification |
| Verify | e2e-playwright | Author + run HTTP e2e per acceptance criterion (Jest + Playwright request) |
| Verify | debugging-and-error-recovery | Reproduce → localize → fix → guard |
| Review | code-review-and-quality | Five-axis review with quality gates |
| Review | code-simplification | Preserve behavior while reducing unnecessary complexity |
| Review | security-and-hardening | OWASP prevention, input validation, least privilege |
| Review | performance-optimization | Measure first, optimize only what matters |
| Ship | git-workflow-and-versioning | Atomic commits, clean history |
| Ship | deprecation-and-migration | Remove old systems and migrate users safely |
| Ship | documentation-and-adrs | Document the why, not just the what |
| Ship | api-spec | Reconcile/update the custom-YAML docs/api/ spec against built code — the spec-first source of truth (update api-spec?) |
| Ship | observability-and-instrumentation | Structured logs, RED metrics, traces, symptom-based alerts |
