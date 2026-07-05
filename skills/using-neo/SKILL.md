---
name: using-neo
description: Discovers and invokes agent skills. Use when starting a session or when you need to discover which skill applies to the current task. This is the meta-skill that governs how all other skills are discovered and invoked.
---

# Using Neo

## Overview

Neo is a collection of engineering workflow skills organized by development phase. Each skill encodes a specific process that senior engineers follow. This meta-skill helps you discover and apply the right skill for your current task.

To drive the whole neo-* lifecycle end to end from a single command — detecting the current phase and running each `neo-<phase>` in turn, with a gate at every boundary — use the `neo` skill (`/neo`, or `/neo auto` to flow after one approval). `neo` and `using-neo` coexist with different scopes: `neo` sequences only the neo-* phases, while `using-neo` (this skill) discovers *which* skill applies across the full catalog — including the non-neo-* skills that `neo` does not drive.

## Skill Discovery

When a task arrives, identify the development phase and apply the corresponding skill:

```
Task arrives
    │
    ├── Have an external source to capture first? → neo-ingest
    ├── Don't know what you want yet? ──────→ interview-me
    ├── Have a rough concept, need variants? → idea-refine
    ├── New project/feature/change? ──→ neo-spec
    │   └── Exposes HTTP endpoints? ──→ api-spec  (draft the docs/api contract spec-first, before code)
    ├── Have a spec, need tasks? ──────→ neo-plan
    ├── Implementing code? ────────────→ neo-build
    │   ├── UI work? ─────────────────→ frontend-ui-engineering
    │   ├── API work? ────────────────→ api-and-interface-design  (interfaces/boundaries; for the docs/api contract → api-spec)
    │   ├── Need better context? ─────→ context-engineering
    │   ├── Need doc-verified code? ───→ source-driven-development
    │   └── Stakes high / unfamiliar code? ──→ doubt-driven-development
    ├── Writing/running tests? ────────→ neo-test
    │   ├── Browser-based? ───────────→ browser-testing-with-devtools
    │   └── HTTP/API acceptance (AC-driven)? → e2e-playwright
    ├── Something broke? ──────────────→ debugging-and-error-recovery
    ├── Reviewing code? ───────────────→ neo-review
    │   ├── Too complex? ─────────────→ neo-code-simplify
    │   ├── Security concerns? ───────→ security-and-hardening
    │   └── Performance concerns? ────→ performance-optimization
    │       └── Web app CWV audit? ───→ neo-webperf
    ├── Committing/branching? ─────────→ neo-commit
    ├── CI/CD pipeline work? ──────────→ ci-cd-and-automation
    ├── Deprecating/migrating? ────────→ deprecation-and-migration
    ├── Writing docs/ADRs? ───────────→ documentation-and-adrs
    ├── Adding logs/metrics/alerts? ───→ observability-and-instrumentation
    ├── Shipping API docs (from docs/api)?
    │   ├── Code drifted from the contract? → openapi-doc  (read-only drift report)
    │   ├── Need a runnable API collection? → open-collection  (Bruno collection)
    │   └── Publish the contract to Confluence? → confluence-api-doc
    └── Deploying/launching? ─────────→ neo-ship
```

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

Don't silently fill in ambiguous requirements. The most common failure mode is making wrong assumptions and running with them unchecked. Surface uncertainty early — it's cheaper than rework.

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

Sycophancy is a failure mode. "Of course!" followed by implementing a bad idea helps no one. Honest technical disagreement is more valuable than false agreement.

### 4. Enforce Simplicity

Your natural tendency is to overcomplicate. Actively resist it.

Before finishing any implementation, ask:
- Can this be done in fewer lines?
- Are these abstractions earning their complexity?
- Would a staff engineer look at this and say "why didn't you just..."?

If you build 1000 lines and 100 would suffice, you have failed. Prefer the boring, obvious solution. Cleverness is expensive.

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

Every skill includes a verification step. A task is not complete until verification passes. "Seems right" is never sufficient — there must be evidence (passing tests, build output, runtime data).

Per-skill verification is the local check. The project-wide bar that applies to *every* change, regardless of which skill is active, is the Definition of Done: tests pass, no regressions, behavior verified at runtime, docs updated. See `references/definition-of-done.md`. It complements each task's acceptance criteria rather than replacing them.

"Docs updated" includes the card's working documents as a set: when a fact changes mid-flow — a source ingested, an open question answered, a decision made in conversation, a scope change — update **every** doc that states it (`docs/tasks/<card>/spec.md`, `plan.md`, `todo.md`, and `docs/knowledge/`), not just the nearest one. See `references/task-docs-sync.md`.

### 7. Read Before You Ask

Load the context that already exists **before** generating output or asking the user anything. First and foremost, check the knowledge base at `docs/knowledge/` (start with its `INDEX.md`) — this is where `/neo-ingest` curates external sources: JIRA cards, docs, specs. Also consult the existing spec (`docs/tasks/<card>/`), the codebase, and `docs/design/` when relevant.

**Never ask the user a question that the knowledge base or the repo already answers.** Reaching for a question before reading the curated context wastes the context the user deliberately ingested — and "sorry, I didn't check the KB" is exactly the failure this rule exists to prevent. Read first; ask only about what genuinely remains unresolved.

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
11. Asking the user what `docs/knowledge/` or the codebase already answers — not reading curated context before acting

## Skill Rules

1. **Check for an applicable skill before starting work.** Skills encode processes that prevent common mistakes.

2. **Skills are workflows, not suggestions.** Follow the steps in order. Don't skip verification steps.

3. **Multiple skills can apply.** A feature implementation might involve `idea-refine` → `spec-driven-development` → `planning-and-task-breakdown` → `incremental-implementation` → `test-driven-development` → `code-review-and-quality` → `code-simplification` → `shipping-and-launch` in sequence.

4. **When in doubt, start with a spec.** If the task is non-trivial and there's no spec, begin with `spec-driven-development`.

## Lifecycle Sequence

For a complete feature, the typical skill sequence is:

```
0.  neo-ingest (/neo-ingest)    → Capture external context into the knowledge base (optional; runs markitdown)
1.  interview-me                → Extract what the user actually wants
2.  idea-refine                 → Refine vague ideas
3.  neo-spec                    → Define what we're building (runs spec-driven-development)
3b. api-spec (Draft)            → Draft the docs/api HTTP contract spec-first, before code (if the feature exposes endpoints)
4.  neo-plan                    → Break into verifiable chunks (runs planning-and-task-breakdown)
5.  context-engineering         → Load the right context
6.  source-driven-development   → Verify against official docs
7.  neo-build                   → Build slice by slice (runs incremental-implementation + test-driven-development)
8.  observability-and-instrumentation → Instrument as you build (runs parallel with 7-9, not after)
9.  doubt-driven-development    → Cross-examine non-trivial decisions in-flight
10. neo-test                    → Prove each slice works (runs test-driven-development)
10b. e2e-playwright             → Run the AC-traceable HTTP e2e acceptance gate (if the service has an e2e harness)
11. neo-review                  → Review before merge (runs code-review-and-quality)
12. neo-code-simplify           → Reduce unnecessary complexity while preserving behavior (runs code-simplification)
13. neo-commit                  → Clean commit history (runs git-workflow-and-versioning)
14. documentation-and-adrs      → Document decisions
14b. api-spec (Update-from-code) → Reconcile docs/api against the built code, structural sync-back (if an api-spec exists; openapi-doc gives a read-only drift report first, on demand)
14c. open-collection            → Regenerate the runnable Bruno collection deliverable from docs/api (if one is maintained)
14d. confluence-api-doc         → Publish the docs/api contract to Confluence (if published there)
15. deprecation-and-migration   → Retire old systems and move users safely when needed
16. neo-ship                    → Deploy safely (runs shipping-and-launch)
```

Not every task needs every skill. A bug fix might only need: `debugging-and-error-recovery` → `test-driven-development` → `code-review-and-quality`.

## Quick Reference

| Phase | Skill | One-Line Summary |
|-------|-------|-----------------|
| Ingest | neo-ingest | Curate an external source into the knowledge base with provenance (via markitdown) |
| Define | interview-me | Surface what the user actually wants before any plan, spec, or code exists |
| Define | idea-refine | Refine ideas through structured divergent and convergent thinking |
| Define | neo-spec | Requirements and acceptance criteria before code (via spec-driven-development) |
| Define | api-spec | Draft the custom-YAML API contract (docs/api) spec-first; reconcile from code at Ship |
| Plan | neo-plan | Decompose into small, verifiable tasks (via planning-and-task-breakdown) |
| Build | neo-build | Thin vertical slices, test each before expanding (via incremental-implementation + test-driven-development) |
| Build | source-driven-development | Verify against official docs before implementing |
| Build | doubt-driven-development | Adversarial fresh-context review of every non-trivial decision |
| Build | context-engineering | Right context at the right time |
| Build | frontend-ui-engineering | Production-quality UI with accessibility |
| Build | api-and-interface-design | Stable interfaces with clear contracts |
| Verify | neo-test | Failing test first, then make it pass (via test-driven-development) |
| Verify | e2e-playwright | AC-traceable HTTP e2e suite, run as the acceptance gate |
| Verify | browser-testing-with-devtools | Chrome DevTools MCP for runtime verification |
| Verify | debugging-and-error-recovery | Reproduce → localize → fix → guard |
| Review | neo-review | Six-axis review with quality gates (via code-review-and-quality) |
| Review | neo-code-simplify | Preserve behavior while reducing unnecessary complexity (via code-simplification) |
| Review | security-and-hardening | OWASP prevention, input validation, least privilege |
| Review | performance-optimization | Measure first, optimize only what matters |
| Ship | neo-commit | Atomic commits, clean history (via git-workflow-and-versioning) |
| Ship | ci-cd-and-automation | Automated quality gates on every change |
| Ship | deprecation-and-migration | Remove old systems and migrate users safely |
| Ship | documentation-and-adrs | Document the why, not just the what |
| Ship | observability-and-instrumentation | Structured logs, RED metrics, traces, symptom-based alerts |
| Ship | neo-ship | Pre-launch checklist, monitoring, rollback plan (via shipping-and-launch) |
| Ship | open-collection | Runnable Bruno API collection generated from the docs/api spec |
| Ship | confluence-api-doc | Publish the docs/api spec to Confluence — one page per endpoint |
| Ship | openapi-doc | Read-only drift report: Go ↔ docs/api spec (on-demand sync-back audit) |
