# neo

**A thin engineering router for AI coding agents.** The injected main agent owns the work:
it decides loop vs graph, makes the edits itself by default, hands a surface to a specialist
node when the work fans out or a reviewer is required, and stops only where a machine can
prove the work or a human confirms.

Most agent setups hand you a pile of skills and hope the model picks the right one. neo picks for
you: every request enters through a single router. The default is a **loop**. A **graph** is earned
when specialties hand off, work fans out, or a reviewer is required.

- **Loop first.** One job stays one job, done inline. Do not draw an org chart to summarize a PDF.
- **Conditional machine gates.** Unit coverage, AC coverage, and the API contract fire from the
  touched surface, decided by scripts, not by an agent's opinion of its own work.
- **Evidence before assertion.** External fields, endpoints, and error codes come from ingested
  sources with a citable path — never from memory.
- **Your git stays yours.** neo never creates, switches, or guards a branch. Commit / push only
  when you ask, through `gitlab`.
- **One owner, optional nodes.** The main agent does the work and owns the verdict. `neo-builder`,
  `neo-author`, and `neo-e2e` take a surface when the work fans out or must fail in isolation.
  `fresh-eyes` reviews only a production / contract / e2e diff.

## How a request runs

```text
ask → loop or graph?
         │
         ├─ loop (default) ── inline, one node, or a direct answer ── fan-in ─┤ gates? ├─ done
         │
         └─ graph (earned) ── wave of disjoint nodes ── fan-in ─┤ gates? ├─ next wave / done
```

| Gate | Kind | When |
|---|---|---|
| Package tests + unit coverage ≥ 80% | machine | production code touched |
| AC coverage (`e2echeck.py`) | machine | HTTP-observable ACs or e2e specs |
| API contract (`apispeccheck.py` + drift = 0) | machine | `docs/api/` or HTTP wire touched |
| MR / ship | human | you asked to ship |

```bash
# three machine gates, one table — AC gate reads docs/tasks/<card>/spec.md (or --ac-source PATH)
python3 skills/using-neo/assets/neocheck.py <repo> <card>
```

There is no FEATURE / BUG / RECONCILE pipeline. Domain skills (`tdd`, `api-spec`, `e2e-playwright`, …)
are what the router — or the node it hands the surface to — loads, not a step list it walks.

A card key does get a **work record** under `docs/tasks/<card>/`, three files answering three different
questions plus a transcript. `spec.md` — what was asked: objective, `AC-NNN`, non-goals, dated decisions,
and the file every AC-aware gate and skill reads. `plan.md` — how the work was cut: one row per surface
with who writes it, its seam, and `depends`, carrying no status. `todo.md` — what happened: wave, status,
and an evidence line per row, plus the gate ledger and a session stamp. The router writes the last two
itself, in full, **before** the first edit, which is what lets a later session resume instead of restart —
a row flipped to `dispatched` the moment work starts is how it tells a surface that was started from one
that was only ever planned. Add `e2e-run.txt` when the router runs the suite. None of them waits for approval.

| You say | neo runs |
|---|---|
| a question | answers — one loop, no graph |
| "แก้ X", a card key, a behavior change | loop or graph; the router edits, or writer node(s) when it fans out |
| a bug, a failing test | `diagnosing-bugs` → the fix, inline or one `build` node |
| a refactor | `codebase-design` → the edit(s) if you asked for them |
| "everything's green but I don't trust it" | `falsifying` (the gate), `bug-hunter` (the product), or `attack-test` (live HTTP) |
| docs, MR, JIRA, scaffolding | the matching domain skill — via an `author` node when several files fan out |

## Install

**Claude Code**

```
/plugin marketplace add witooh/neo-plugin
/plugin install neo@neo
```

**Grok Build**

Native Grok plugin: `.grok-plugin/marketplace.json` plus `.grok-plugin/plugin.json`, skills from `skills/`. See [docs/grok-setup.md](docs/grok-setup.md).

```bash
grok plugin install witooh/neo-plugin --trust
grok plugin enable neo
```

Grok 1.0.3 does not inject `using-neo` at session start (hook stdout is ignored). Use `/using-neo` or rely on skill auto-invocation.

**omp**

Native omp package: the `omp` block in `package.json` loads an ESM session extension that injects the
`using-neo` router, and `skills/` is discovered as-is. See [docs/omp-setup.md](docs/omp-setup.md).

```bash
# install
omp plugin install github:witooh/neo-plugin

# update (same command + --force — pulls latest tip / release)
omp plugin install github:witooh/neo-plugin --force

# uninstall
omp plugin uninstall neo
```

Lists under **npm Plugins** as `neo@<version>`. Do **not** use `omp plugin marketplace` or
`omp plugin upgrade` for neo — those are marketplace-only and will not track this install.

Dev against a working tree: `omp plugin link <path-to-local-clone>`.

**pi**

Installs as a native pi package; skills load unchanged, and a session extension injects the
`using-neo` router before every agent run. See [docs/pi-setup.md](docs/pi-setup.md).

Install from the repo:

```bash
pi install git:github.com/witooh/neo-plugin
```

Install from a local clone:

```bash
git clone https://github.com/witooh/neo-plugin.git
pi install ./neo-plugin
```

Either way the method skills ship inside the plugin — there is no second install.

**Cursor / Kiro**

```bash
./cursor.sh --project    # or --global → ~/.cursor
./kiro.sh --project      # or --global → ~/.kiro
```

Copies `skills/`, `agents/*.md` (graph nodes), and the SessionStart hook that injects `using-neo`. Graph dispatch uses the same Agent/Task shape as Claude Code. See `skills/using-neo/GRAPH.md`.

## Architecture

```text
┌─ ROUTER ─────────────────────────────────────────────┐
│ using-neo — injected at session start                │
│ orchestrator · loop-or-graph · gates · verdict       │
├─ NODE LAYER (agents/) ───────────────────────────────┤
│ neo-builder · neo-author · neo-e2e · fresh-eyes      │
├─ METHOD LAYER (vendored from mattpocock/skills) ─────┤
│ grilling · domain-modeling · tdd · diagnosing-bugs   │
│ research · prototype                                 │
│ codebase-design · resolving-merge-conflicts          │
├─ DOMAIN LAYER (neo-owned) ───────────────────────────┤
│ code-review · falsifying · bug-hunter · attack-test  │
│ api-spec · e2e-playwright · openapi-doc              │
│ open-collection · confluence-api-doc · markitdown    │
│ init-project · migrate-project · atlassian · gitlab  │
└──────────────────────────────────────────────────────┘
```

- **Router** — _when_ things happen. One skill, injected into every session. Mechanics in `GRAPH.md`.
- **Node layer** — _who else_ writes. Specialist agents the router hands a surface to when the work
  fans out, must fail in isolation, or needs an independent reviewer.
- **Method layer** — _how_ generic engineering is done. Vendored via `sync-mattpocock`
  (allowlist + 3-way compare), shipped inside the plugin.
- **Domain layer** — _how_ this org's work is done: the API contract chain, AC-driven e2e gates,
  JIRA/GitLab operations, Go service scaffolding.

## Skills

The router and the neo-owned domain layer. The method layer is listed in the diagram above and
documented upstream.

**Driving the work**

| Skill        | Purpose                                                                         |
| ------------ | ------------------------------------------------------------------------------- |
| `using-neo`  | The router — loop-or-graph, the edits, dispatch, gates, verdict               |
| `markitdown` | Ingest JIRA, Confluence, URLs, and files into `docs/knowledge/` with provenance |
| `atlassian`  | JIRA / Confluence operations via `acli`                                         |
| `gitlab`     | GitLab MR operations via `glab`                                                 |

**Proving it works**

| Skill            | Purpose                                                                                                                                 |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| `e2e-playwright` | AC-driven HTTP e2e tests (Jest + Playwright request) behind the `e2echeck` gate                                                         |
| `code-review`    | Two-axis review of a diff — Standards (`.kiro/steering/`) and Spec (`docs/tasks/<card>/spec.md`) — plus Security when the diff earns it |
| `falsifying`     | Attacks a green signal: can this gate go red at all? Audits the apparatus, not the product                                              |
| `bug-hunter`     | Hunts defects no gate covers, starting from the ingested originals in `docs/knowledge/`                                                 |
| `attack-test`    | Fires abuse/hack paths over live HTTP after happy path — money-move, authz bypass, proof forge, idempotency                             |

**The API contract chain**

| Skill                | Purpose                                                                          |
| -------------------- | -------------------------------------------------------------------------------- |
| `api-spec`           | Authors the custom-YAML contract at `docs/api/` — the spec-first source of truth |
| `openapi-doc`        | Read-only drift report: Go source vs `docs/api/`                                 |
| `open-collection`    | Generates a runnable Bruno collection from the spec                              |
| `confluence-api-doc` | Publishes the API docs to Confluence                                             |

**Shaping a service**

| Skill             | Purpose                                                                   |
| ----------------- | ------------------------------------------------------------------------- |
| `init-project`    | Scaffolds a Go hexagonal / DDD service from a frozen template             |
| `migrate-project` | Restructures an existing Go service to the same blueprint, slice by slice |

## Maintaining

Update the vendored method layer:

```bash
python3 .agents/skills/sync-mattpocock/assets/sync.py          # dry run
python3 .agents/skills/sync-mattpocock/assets/sync.py --apply  # write
```

Validate before shipping:

```bash
node scripts/validate-skills.js       # frontmatter + dead-reference scan
node scripts/validate-pi-package.js   # pi package wiring
node scripts/validate-omp-package.js  # omp package wiring
node scripts/validate-grok-package.js # Grok marketplace + plugin wiring
bash hooks/session-start-test.sh      # Claude Code hook
claude plugin validate .              # Claude plugin structure
grok plugin validate .                # Grok plugin structure
```

## License

MIT
