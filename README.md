# neo

**A thin engineering router for AI coding agents.** The injected main agent
orchestrates: it decides loop vs graph, dispatches specialist nodes to do the
edits, and stops only where a machine can prove the work or a human confirms.

Most agent setups hand you a pile of skills and hope the model picks the right one. neo picks for
you: every request enters through a single router. The default is a **loop**. A **graph** is earned
when specialties hand off, work fans out, or a reviewer is required.

- **Loop first.** One job stays one node. Do not draw an org chart to summarize a PDF.
- **Conditional machine gates.** Unit coverage, AC coverage, and the API contract fire from the
  touched surface, decided by scripts, not by an agent's opinion of its own work.
- **Evidence before assertion.** External fields, endpoints, and error codes come from ingested
  sources with a citable path — never from memory.
- **Your git stays yours.** neo never creates, switches, or guards a branch. Commit / push only
  when you ask, through `gitlab`.
- **One orchestrator, many nodes.** The main agent owns the graph and the verdict. `neo-builder`,
  `neo-author`, and `neo-e2e` make the edits. `fresh-eyes` reviews only a production / contract / e2e diff.

## How a request runs

```text
ask → loop or graph?
         │
         ├─ loop (default) ── one node or a direct answer ── fan-in ─┤ gates? ├─ done
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
# three machine gates, one table — only when a card folder already exists
python3 skills/using-neo/assets/neocheck.py <repo> <card>
```

There is no FEATURE / BUG / RECONCILE pipeline. Domain skills (`tdd`, `api-spec`, `e2e-playwright`, …)
are what a **node** loads, not a step list the router walks.

| You say | neo runs |
|---|---|
| a question | answers — one loop, no graph |
| "แก้ X", a card key, a behavior change | loop or graph; writer node(s) do the edit |
| a bug, a failing test | `diagnosing-bugs` → one `build` node |
| a refactor | `codebase-design` → `build` node(s) if you asked for the edit |
| "everything's green but I don't trust it" | `falsifying` (the gate), `bug-hunter` (the product), or `attack-test` (live HTTP) |
| docs, MR, JIRA, scaffolding | the matching domain skill, via an `author` node when a file is written |

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
- **Node layer** — _who_ writes. Specialist agents; the orchestrator never edits the product.
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
| `using-neo`  | The orchestrator — loop-or-graph, dispatch, gates, verdict                          |
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

## Testing

The validators below are static — frontmatter and wiring. The runtime harness is the other layer:
it drives a **real agent** against a throwaway fixture project and asserts what the agent actually
did — which skills it loaded, in what order it wrote files, which CLI commands it fired, and whether
it stopped at the gates.

```bash
node tests/runtime/run.mjs                          # every case
node tests/runtime/run.mjs --list                   # cases + skill coverage, no model calls
node tests/runtime/run.mjs --group flow             # one group (flow | skill)
node tests/runtime/run.mjs --skill tdd              # every case that exercises one skill
node tests/runtime/run.mjs --case bug-404 --repeat 3
node tests/runtime/run.mjs --case api-spec --keep   # keep the workdir for inspection
```

Each run copies `tests/runtime/fixtures/<fixture>/` to a temp dir, commits it, then drives
`pi -p --mode json` with **only this plugin** loaded (`-ne`, an explicit `-e` for the provider,
`--skill ./skills`) so nothing else in your `pi` install can colour the result. Needs `pi` with the
`grok-cli` provider, plus `go` and `python3` for the fixtures' own checks. Verdict, full tool trace,
and raw transcript land in `tests/runtime/reports/<case>/run-N.{json,jsonl}`.

**A case** is one JSON file under `cases/flow/` or `cases/skill/`:

| Field            | Meaning                                                                                                     |
| ---------------- | ----------------------------------------------------------------------------------------------------------- |
| `skills`         | which skills the case covers — drives `--skill` and the coverage line                                       |
| `fixture`        | directory under `fixtures/` to copy                                                                         |
| `setup`          | bash run in the workdir before the agent — stage a conflict, a diff, a branch                               |
| `stubs`          | recording stubs from `stubs/` placed first on `PATH` (`glab`, `acli`, `curl`); every call logged, none reach the network |
| `prompt`         | what the user says                                                                                          |
| `expect`         | the assertions                                                                                              |

Assertions: `skillsLoaded`, `redBeforeGreen`, `fixApplied`, `filesWritten`, `filesNotWritten`,
`writeOrder`, `ranCommand`, `outputContains`, `cliCalled`, `cliNotCalled`, `sandbox`,
`noGitWrites`, `postCommand`.

File assertions read the **working tree** (`git status` plus a diff against the base commit), not
the tool trace — an agent can write through `cat >` as easily as through the edit tool, and it may
commit its own work.

Two things to expect. The harness is **non-deterministic**: read a failure as a pass-rate, not a
verdict, and re-run with `--repeat` before believing it. And it **costs money**: ~$0.12 per case,
~$1.8 for the full suite of 15.

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
