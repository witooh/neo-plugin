# Getting Started

neo = router (`using-neo`) + method skills (vendored from [mattpocock/skills](https://github.com/mattpocock/skills)) + org-specific domain skills. One plugin install covers all three layers.

## Install (Claude Code)

```
/plugin marketplace add witooh/neo-plugin
/plugin install neo@neo
```

For Grok Build, see [grok-setup.md](grok-setup.md). For pi, see [pi-setup.md](pi-setup.md). For omp (GitHub install + force upgrade), see [omp-setup.md](omp-setup.md).

## First run

Open a session in your service repo. On Claude Code the session-start hook injects `using-neo` (and `.kiro/steering/INDEX.md` when present). On Grok Build, invoke `/using-neo` or state the task and let skill auto-invocation pick the router — hook stdout is not injected. Then state your task:

```
ทำ GI-543
```

neo fetches the card, ingests referenced sources into `docs/knowledge/`, closes open design decisions with you (grilling), drafts the API contract, writes `docs/tasks/GI-543/spec.md` + `plan.md` + `todo.md`, and waits for your approval. After one approval it runs TDD build, per-AC e2e (`e2echeck` gate), code review, doc sync (`apispeccheck` gate), and stops at the MR gate.

## The six gates

| Gate | Kind |
|---|---|
| Spec + plan approval | human (FEATURE) |
| Decision evidence (CAPTURE) | human (RECONCILE) — source + who/why/scope before any KB/task/api write |
| AC coverage (`e2echeck.py`) | machine |
| Unit coverage (repo coverage command ≥ 80%) | machine |
| API contract (`apispeccheck.py` + drift) | machine |
| MR / ship | human |

Everything between FEATURE gates runs continuously. RECONCILE stops at CAPTURE until the decision is named. Git branching is yours — neo never touches branches; the only git side effects sit behind the MR gate.

## Other entry points

- Bug: paste the bug card or describe the failure — diagnose, red test, fix, review.
- Refactor: state the target — behavior-preserving steps with tests green throughout.
- RECONCILE: when code already leads the written requirement — CAPTURE → ingest KB → align task docs → structural api-spec → verify (never promote code to requirement SOT).
- Direct ops: `docs/api` work, Bruno collections, Confluence publishing, JIRA/GitLab operations, and Go service scaffolding route straight to the matching domain skill.

## Updating the method layer (maintainers)

```bash
python3 .agents/skills/sync-mattpocock/assets/sync.py --apply
node scripts/validate-skills.js
```

See `.agents/skills/sync-mattpocock/SKILL.md` for the allowlist and conflict rules.
