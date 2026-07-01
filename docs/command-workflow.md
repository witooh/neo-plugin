# Command Workflow

neo ships 10 slash commands that map to the development lifecycle. Each one activates
the right skills automatically. This guide shows **how they chain together** — the order
you run them in, what each reads and writes, and the shorter paths when you don't need the
full flow.

> These are Claude Code slash commands (`.claude/commands/`). The same commands ship as
> `.toml` files for Gemini CLI (`.gemini/commands/`) and Antigravity (`commands/`) — the
> workflow below is identical regardless of harness.

## The lifecycle at a glance

```
  INGEST     DEFINE      PLAN       BUILD      VERIFY      REVIEW       SHIP
 ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐    ┌──────┐
 │Source│──▶│ Spec │──▶│ Plan │──▶│ Code │──▶│ Test │──▶│  QA  │───▶│  Go  │
 │Curate│   │  PRD │   │Tasks │   │ Impl │   │Debug │   │ Gate │    │ Live │
 └──────┘   └──────┘   └──────┘   └──────┘   └──────┘   └──────┘    └──────┘
 /ingest    /spec      /plan      /build     /test      /review     /ship
                                  /commit    /webperf   /code-simplify
```

Not every task needs every phase. The flow above is the **full path for a new feature**;
see [Shorter paths](#shorter-paths) for bug fixes and small changes.

## What each command reads and writes

The commands communicate through files on disk — mostly under `docs/`. Later commands read
what earlier ones wrote, so the artifacts are the contract between phases.

| Command | Reads | Writes |
|---------|-------|--------|
| `/ingest` | A URL, JIRA/Confluence link, file, or pasted text | `docs/knowledge/<topic>.md` + `docs/knowledge/INDEX.md` |
| `/spec` | `docs/knowledge/` (KB-first), your answers | `docs/tasks/<card>/spec.md` (with `AC-001…` IDs); `docs/api/` if it's an HTTP API |
| `/plan` | `docs/tasks/<card>/spec.md`, the codebase | `docs/tasks/<card>/plan.md` + `todo.md` |
| `/build` | The plan + task acceptance criteria | Source code, tests, one git commit per task |
| `/test` | The code under change, acceptance criteria | Tests (feature TDD or bug Prove-It) |
| `/commit` | The working tree | Atomic git commits |
| `/review` | Staged changes or recent commits | A structured six-axis review (no file changes) |
| `/code-simplify` | Recently changed code | Simplified code (behavior preserved) |
| `/webperf` | A web app + optional Lighthouse/trace JSON | A performance scorecard + ranked findings |
| `/ship` | The full change | A go/no-go decision + rollback plan |

`<card>` is the feature name or JIRA card id you supply — it namespaces the task folder so
multiple features can be in flight at once.

## End-to-end walkthrough — a new feature

This is the happy path from a JIRA card to production.

### 1. `/ingest` — capture the source (optional but recommended)

Point `/ingest` at the JIRA card, a requirements doc, a Confluence page, or a PDF. It
curates the source into `docs/knowledge/<topic>.md` with provenance (where it came from,
when, who validated it) and updates `INDEX.md`. Contract and behaviour-constraining clauses
are copied **verbatim** in their original language — never paraphrased.

Do this first so `/spec` has authoritative context to read instead of asking you questions
it could answer from the source.

### 2. `/spec` — define what to build

`/spec` reads `docs/knowledge/` **before** asking you anything, then asks only about what's
genuinely unresolved. It produces `docs/tasks/<card>/spec.md` covering objective, commands,
structure, code style, testing strategy, and boundaries.

The critical output is the **`## Acceptance Criteria`** section: each criterion gets a stable
id (`AC-001`, `AC-002`, …). These IDs are the thread that ties everything downstream —
`/plan` slices around them, `/test` traces tests back to them, and (for APIs) `docs/api/`
records them in `covers_ac`.

If the spec describes an HTTP API, `/spec` follows up by authoring the `docs/api/` contract
**spec-first** (before any code exists), so the implementation has a contract to build
against. Confirm the spec before moving on.

### 3. `/plan` — break it into tasks

`/plan` reads the spec, enters read-only plan mode, and slices the work **vertically** (one
complete path per task, not horizontal layers). It writes `docs/tasks/<card>/plan.md` and a
`todo.md`, with acceptance criteria and verification steps per task, plus checkpoints between
phases. Review the plan before building.

### 4. `/build` — implement, one slice at a time

`/build` picks the next pending task and runs the test-driven loop:

```
read AC → load context → failing test (RED) → minimum code (GREEN)
        → full test suite → build → commit → mark complete → stop
```

It commits each task individually, then stops so you can inspect. Run `/build` again for the
next task. See [Two build modes](#two-build-modes) to run the whole plan in one pass.

### 5. `/test` — prove behaviour (as needed)

`/build` already writes a test per task, so you often don't run `/test` separately. Reach for
it to deepen coverage or when working outside the build loop:

- **New features** — write failing tests, implement, refactor green.
- **Bug fixes (Prove-It)** — write a test that reproduces the bug (must fail), fix, confirm
  it passes, run the full suite for regressions.
- **Browser or HTTP/API work** — `/test` pulls in `browser-testing-with-devtools` or the
  AC-driven `e2e-playwright` harness to verify against a real runtime.

### 6. `/review` → `/code-simplify` — tighten before merge

`/review` runs a **six-axis** review of the current changes — correctness, readability,
architecture, security, performance, conventions & style — and reports findings as Critical /
Important / Suggestion with `file:line` references. It changes no code.

`/code-simplify` then reduces complexity in the changed code **without changing behavior**,
running tests after each simplification and reverting any that break.

For web apps, run `/webperf` here too (see [Specialist checks](#specialist-checks)).

### 7. `/ship` — the go/no-go gate

`/ship` is a **fan-out orchestrator**. It spawns three specialists in parallel against the
change — `code-reviewer`, `security-auditor`, `test-engineer` — then merges their reports in
the main context into a single **GO / NO-GO** decision with a mandatory rollback plan. Any
Critical finding defaults the verdict to NO-GO unless you explicitly accept the risk.

If the service has a `docs/api/` spec, `/ship` verifies it still matches the shipped code and
reconciles drift via api-spec **Update-from-code** mode.

## Two build modes

| Mode | Behaviour | Use when |
|------|-----------|----------|
| `/build` | Implements the **next** pending task, then stops. | You want to inspect each slice — careful, one at a time. |
| `/build auto` | Generates the plan if needed, takes **one** approval, then implements **every** task without stopping between them. | The spec is solid and you want to collapse plan + build into one run. |

`/build auto` removes the human stepping *between* tasks — **not** the verification. Every
task still earns a passing test and its own commit. It requires a real spec at
`docs/tasks/<card>/spec.md` (a README does not count), requires a clean git baseline, and
**stops to ask** when a test can't pass, the spec is ambiguous, or a task is high-risk or
irreversible (auth, payments, destructive migrations, deploys, anything `git revert` can't
undo). After you resolve a blocker, re-invoke `/build auto` — it resumes from the next pending
task.

## Where `/commit` fits

`/build` already commits each increment inside its loop, so during a normal build you rarely
call `/commit` yourself. Reach for it for **ad-hoc commits** and **pre-push history cleanup**:

- It groups the working tree into atomic commits (one logical change each), stages precisely
  (never a blind `git add -A`), runs pre-commit hygiene (secret scan, tests, lint, type-check),
  and writes conventional messages.
- It also judges **when a rebase is safe** — cleaning history only on local, unpushed commits;
  never rewriting shared history without explicit sign-off.

`/commit` does **not** cut releases, tags, or version bumps — that's `/ship`'s territory, not
the commit step.

## Specialist checks

| Command | Scope | Notes |
|---------|-------|-------|
| `/webperf` | Web apps only | Runs the `web-performance-auditor` persona. **Deep mode** when a Lighthouse/PSI/CrUX/trace JSON or a live URL + Chrome DevTools MCP is available; **Quick mode** (source-level anti-pattern scan) otherwise. Don't use it on CLIs or server-only code. |
| `/test` companions | Browser / API | `/test` pulls in `browser-testing-with-devtools` for browser issues and `e2e-playwright` for AC-driven HTTP acceptance tests. |

## Shorter paths

The full seven-phase flow is for new features. Most day-to-day work is shorter:

| Situation | Path |
|-----------|------|
| **Bug fix** | `/test` (Prove-It: reproduce → fix → regress) → `/review` → `/commit` |
| **Small tweak** (≤2 files, <50 lines, no auth/payments/data/config) | `/build` (or edit directly) → `/commit`. `/ship` may skip its fan-out here. |
| **Refactor for clarity** | `/code-simplify` → `/review` → `/commit` |
| **Just capturing context** | `/ingest` on its own — builds up the knowledge base for later specs. |
| **Web performance pass** | `/webperf` → fix → `/webperf` again to confirm. |

For any non-trivial, production-bound change, still run `/ship` before deploy — it's designed
to catch what the blast radius warrants even when the diff looks small.

## Quick reference

| Command | One-liner |
|---------|-----------|
| `/ingest` | Curate an external source into `docs/knowledge/` with provenance |
| `/spec` | Write the spec + acceptance criteria (KB-first) before any code |
| `/plan` | Slice the spec into small, vertically-sliced tasks |
| `/build` | Implement the next task test-first; `/build auto` runs the whole plan |
| `/test` | TDD for features, Prove-It for bugs, e2e/browser companions |
| `/commit` | Group the working tree into clean atomic commits |
| `/review` | Six-axis review of the current change |
| `/code-simplify` | Reduce complexity without changing behavior |
| `/webperf` | Web performance audit (web apps only) |
| `/ship` | Parallel specialist gate → GO/NO-GO + rollback plan |

See [getting-started.md](getting-started.md) for setup and [comparison.md](comparison.md) for
how neo differs from other skill packs.
