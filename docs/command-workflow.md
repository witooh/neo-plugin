# Single-Entry Workflow

`using-neo` is neo's canonical entry point. Describe the outcome you want; the
router reads repository state, selects the narrowest applicable workflow, loads
its phase contract, and invokes the underlying method skills.

## Lifecycle at a glance

```text
INGEST (conditional) -> DEFINE -> PLAN -> BUILD -> VERIFY -> REVIEW
                     -> SIMPLIFY -> COMMIT -> SHIP
```

Webperf branches around Review/Ship only for browser-facing web apps. Focused
requests do not run the entire lifecycle: a review request reviews, a bug report
uses Prove-It, and a context-capture request only ingests.

## Modes

| Mode | Behavior | Use when |
|---|---|---|
| adaptive (default) | Infer the focused workflow; end-to-end requests gate every phase | Most work |
| `using-neo single` | Run one pending task or one selected phase, then stop | You want an inspection point |
| `using-neo auto` | Continue after one approval, retaining all quality gates | The scope is approved and stable |

An explicit request to “implement the approved/full plan” selects Build auto.
It does not silently widen into Review or Ship. If Build scope is ambiguous and
multiple tasks remain, the router asks auto versus single.

Auto always stops at the standalone Commit phase, Ship, unresolved blockers,
decision stops for newly discovered material decisions, and high-risk or
irreversible work. A decision stop preserves the evidence and asks before
changing approved scope, task boundaries, architecture, data models, public
contracts, persistence strategy, or safety posture. Repository rules may
require the user to make all commits; those rules override Build auto's normal
per-task commit behavior.

## State detection for end-to-end work

The router starts at the earliest incomplete output:

| Repository state | Next workflow |
|---|---|
| Named source absent from `docs/knowledge/` | Ingest |
| Missing/unapproved `docs/tasks/<card>/spec.md` | Define |
| Missing `plan.md` or `todo.md` | Plan |
| Pending tasks or missing implementation/tests | Build, then Verify |
| Implementation complete and tests green | Review, then Simplify |
| Review gates clear | Commit, then Ship |

If more than one feature is plausible, the router asks for the card identifier.
Otherwise it derives the card from repository state instead of asking.

## Workflow contracts

| Workflow | Reads | Produces or verifies |
|---|---|---|
| Ingest | External source | Curated `docs/knowledge/` entry and index |
| Define | Knowledge base, existing code, user decisions | `spec.md` with stable AC IDs; `docs/api/` for HTTP contracts |
| Plan | Approved spec and codebase | Vertically sliced `plan.md` and `todo.md` |
| Build | Plan, ACs, code | Test-first implementation and synchronized task status |
| Verify | Behavior and ACs | RED/GREEN proof, regression/runtime/e2e evidence |
| Review | Diff, spec, ACs | Six-axis findings; conditional AC -> evidence matrix; reproducible project-wide unit line coverage >=80% |
| Simplify | Recently changed code | Smaller/clearer code with identical behavior |
| Commit | Working tree and history | Precisely staged atomic commits when authorized |
| Webperf | Web app and optional metrics/trace | Sourced scorecard and ranked findings |
| Ship | Full production-bound change | GO/NO-GO decision and rollback plan |

Task artifacts are a shared contract. When a source, decision, scope, blocker, or
status changes, update every document that states it: `spec.md`, `plan.md`,
`todo.md`, and relevant knowledge entries.

## Common focused paths

| Situation | Routed path |
|---|---|
| Bug fix | Verify (Prove-It) -> Review -> Commit when authorized |
| Small tweak | Build -> Verify; lightweight Ship rules may apply |
| Refactor for clarity | Simplify -> Review -> Commit when authorized |
| Capture context only | Ingest |
| Web performance audit | Webperf -> remediation -> Webperf verification |
| Production readiness | Ship specialist gate |

For non-trivial production-bound changes, Ship runs independent code, security,
and test reviews, merges them in the main context, and requires an executable
rollback plan. Critical findings default to NO-GO.
