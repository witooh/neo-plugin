# neo

A thin engineering router plus org-specific domain skills for AI coding agents. neo drives feature work end to end — ingest → align → api → spec → build → verify → review → doc → MR — stopping only at four gates, two of which are machine-verified. The generic method layer (TDD, code review, debugging, grilling) is vendored from [mattpocock/skills](https://github.com/mattpocock/skills) into `skills/` via the repo-local `sync-mattpocock` skill.

## Architecture

```text
┌─ ROUTER ─────────────────────────────────────────────┐
│ using-neo — injected at session start                │
│ intent detection · flow · gates · resume             │
├─ METHOD LAYER (vendored from mattpocock/skills) ─────┤
│ grilling · domain-modeling · tdd · code-review       │
│ diagnosing-bugs · research · prototype               │
│ codebase-design · resolving-merge-conflicts          │
├─ DOMAIN LAYER (neo-owned) ───────────────────────────┤
│ api-spec · e2e-playwright · openapi-doc              │
│ open-collection · confluence-api-doc · markitdown    │
│ init-project · migrate-project · atlassian · gitlab  │
└──────────────────────────────────────────────────────┘
```

- **Router** decides *when* things happen. One skill, injected into every session, ~150 lines.
- **Method layer** defines *how* generic engineering is done. Vendored via `sync-mattpocock` (allowlist + 3-way compare), ships inside the plugin.
- **Domain layer** defines *how* org-specific work is done: API contract chain, AC-driven e2e gates, JIRA/GitLab operations, Go service scaffolding.

## Install

### Claude Code

```
/plugin marketplace add witooh/neo-plugin
/plugin install neo@neo
```

Method skills ship inside the plugin — no second install.

### pi

The repo ships a `pi` package block (`package.json`) with `.pi/` discovery symlinks; the `extensions/using-neo-session-start.js` extension injects the router at session start. Skills under `skills/` (router + method + domain) are discovered automatically.

### Updating the method layer (maintainers)

```bash
python3 .agents/skills/sync-mattpocock/assets/sync.py          # dry run
python3 .agents/skills/sync-mattpocock/assets/sync.py --apply  # write
node scripts/validate-skills.js
```

## How it works

Every request routes through `using-neo`. It detects intent and drives the matching flow:

| Intent | Flow |
|---|---|
| Card key / feature | INGEST → ALIGN → API → SPEC ⟶gate⟶ BUILD → VERIFY ⟶gate⟶ REVIEW → DOC ⟶gate⟶ MR ⟶gate |
| Bug | diagnosing-bugs → red test → fix → review |
| Refactor | codebase-design → small steps → review |
| Question | direct answer — no ceremony |
| Docs / MR / JIRA / scaffold | direct domain-skill route |

The four gates:

| Gate | Kind | Decider |
|---|---|---|
| Spec + plan approval | human | you |
| AC coverage | machine | `e2echeck.py` |
| API contract | machine | `apispeccheck.py` + drift report |
| MR / ship | human | you |

Everything between gates runs continuously. Git branching is yours: neo never creates or switches branches; the only git side effects sit behind the MR gate.

## Skills

| Skill | Purpose |
|---|---|
| `using-neo` | Router: intent, flows, gates, resume |
| `api-spec` | Author the custom-YAML API contract at `docs/api/` (spec-first source of truth) |
| `e2e-playwright` | AC-driven HTTP e2e tests (Jest + Playwright request), `e2echeck` coverage gate |
| `openapi-doc` | Read-only drift report: Go code vs `docs/api/` |
| `open-collection` | Runnable Bruno collection generated from the API spec |
| `confluence-api-doc` | Publish API docs to Confluence |
| `markitdown` | Ingest external sources (JIRA, Confluence, URLs, files) into `docs/knowledge/` with provenance |
| `init-project` | Scaffold a Go hexagonal/DDD service from a frozen template |
| `migrate-project` | Restructure an existing Go service to the same blueprint, slice by slice |
| `atlassian` | JIRA/Confluence operations via `acli` |
| `gitlab` | GitLab MR operations via `glab` |

## Validation

```bash
node scripts/validate-skills.js      # frontmatter + dead-reference scan
node scripts/validate-pi-package.js  # pi package wiring
bash hooks/session-start-test.sh     # Claude hook
claude plugin validate .             # plugin structure
```

## License

MIT
