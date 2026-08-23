# Getting Started

neo = router (`using-neo`) + method skills (vendored from [mattpocock/skills](https://github.com/mattpocock/skills)) + org-specific domain skills. One plugin install covers all three layers.

## Install (Claude Code)

```
/plugin marketplace add witooh/neo-plugin
/plugin install neo@neo
```

For Grok Build, see [grok-setup.md](grok-setup.md). For pi, see [pi-setup.md](pi-setup.md). For omp, see [omp-setup.md](omp-setup.md). Cursor: `./cursor.sh`. Kiro: `./kiro.sh`.

## First run

Open a session in your service repo. On Claude Code the session-start hook injects `using-neo` (and `.kiro/steering/INDEX.md` when present). On Grok Build, invoke `/using-neo` or state the task and let skill auto-invocation pick the router — hook stdout is not injected. Then state your task.

The router owns the work. Default is a **loop** — it edits inline, or answers you directly. A **graph** is earned when specialties hand off, work fans out, or a reviewer is required; then `neo-builder` / `neo-author` / `neo-e2e` take a surface each. Delegating is a choice the router makes, not a rule that keeps it off the keyboard.

```
แก้ GET /accounts/{id} ให้คืน 404 ตอนหาไม่เจอ
```

That is one job: the router edits it inline under `tdd`, then runs the package tests. No ingest → align → spec pipeline, no node dispatch to watch.

## Gates (conditional)

| Gate | Kind | When |
|---|---|---|
| Package tests + unit coverage ≥ 80% | machine | production code touched |
| AC coverage (`e2echeck.py`) | machine | HTTP-observable ACs or e2e specs |
| API contract (`apispeccheck.py` + drift) | machine | `docs/api/` or HTTP wire touched |
| MR / ship | human | you asked to ship |

There is no FEATURE / BUG / RECONCILE pipeline and no spec+plan approval gate. Git branching is yours — neo never touches branches; commit / push only when you ask, through `gitlab`.

## Other entry points

- Question / research: answered in one loop — no graph.
- Bug: paste the failure — `diagnosing-bugs`, then the fix inline (a `build` node only if it fans out).
- Refactor: `codebase-design`, then the edit(s) if you asked for them.
- Direct ops: `docs/api` work, Bruno collections, Confluence publishing, JIRA/GitLab operations, and Go service scaffolding route to the matching domain skill (an `author` node writes the file when the work fans out across several).

## Updating the method layer (maintainers)

```bash
python3 .agents/skills/sync-mattpocock/assets/sync.py --apply
node scripts/validate-skills.js
```

See `.agents/skills/sync-mattpocock/SKILL.md` for the allowlist and conflict rules.
