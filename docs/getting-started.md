# Getting Started

neo is a bag of org domain skills in `skills/`. One plugin install. Developers pick a skill themselves — there is no router and no bundled workflow.

## Install (Claude Code)

```
/plugin marketplace add witooh/neo-plugin
/plugin install neo@neo
```

For Grok Build, see [grok-setup.md](grok-setup.md). For pi, see [pi-setup.md](pi-setup.md). For omp, see [omp-setup.md](omp-setup.md). Cursor: `./cursor.sh`. Kiro: `./kiro.sh`.

## First run

Open a session in your service repo. Invoke a skill (slash command or by name), or state the task and let the host auto-load a matching one. There is no session-start hook.

```
แก้ GET /accounts/{id} ให้คืน 404 ตอนหาไม่เจอ
```

Git is yours — neo never touches branches; commit / push only when you ask, through `gitlab`.

## Skills

Seventeen skills under `skills/`. Full list in the [README](../README.md). Brief map:

- **Ingest / tracker / VCS:** `markitdown`, `atlassian`, `gitlab`
- **API contract chain:** `api-spec`, `openapi-doc`, `open-collection`, `confluence-api-doc`
- **HTTP e2e / audit:** `e2e-playwright`, `http-audit-log`
- **QA probes:** `falsifying`, `bug-hunter`, `attack-test`
- **Go service:** `init-project`, `migrate-project`
- **SIT:** `neo-core-sit`, `neo-aux-sit`
- **User-invoked:** `advice-mode`
