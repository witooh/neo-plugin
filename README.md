# neo

**A thin engineering router for AI coding agents.** One entry point drives a feature from a card
to a merge request — and stops only where a human decides or a machine can prove it.

Most agent setups hand you a pile of skills and hope the model picks the right one. neo picks for
you: every request enters through a single router that detects intent, runs the matching flow, and
refuses to call work done until the gates agree.

- **Five gates, three of them machine-verified.** AC coverage, unit coverage, and the API contract
  are decided by scripts, not by an agent's opinion of its own work.
- **Evidence before assertion.** External fields, endpoints, and error codes come from ingested
  sources with a citable path — never from memory. A citation that points nowhere fails the build.
- **Your git stays yours.** neo never creates, switches, or guards a branch. The only git side
  effects sit behind the MR gate.

## The flow

```text
  ingest → align → api → spec ─┤ 1 ├─ build → verify ─┤2 3├─ review → doc ─┤ 4 ├─ mr ─┤ 5 ├
                                you                  machine              machine      you
```

|  #  | Gate                 | Kind    | Decided by                                                 |
| :-: | -------------------- | ------- | ---------------------------------------------------------- |
|  1  | Spec + plan approval | human   | you                                                        |
|  2  | AC coverage          | machine | `e2echeck.py` — every HTTP-observable criterion has a test |
|  3  | Unit coverage        | machine | the repo's own coverage command, ≥ 80%                     |
|  4  | API contract         | machine | `apispeccheck.py` + drift report                           |
|  5  | MR / ship            | human   | you                                                        |

```bash
# all three machine gates, one table, one exit code
python3 skills/using-neo/assets/neocheck.py <repo> <card>
```

Everything between gates runs continuously — one approval carries through to the MR gate.

Other intents route straight to where they belong:

| You say                                   | neo runs                                              |
| ----------------------------------------- | ----------------------------------------------------- |
| a card key, a feature, "แก้ X"            | the full flow above                                   |
| a bug, a failing test                     | `diagnosing-bugs` → red test → fix → review           |
| a refactor                                | `codebase-design` → small steps → review              |
| a question                                | answers — no ceremony                                 |
| "everything's green but I don't trust it" | `falsifying` (the gate) or `bug-hunter` (the product) |
| docs, MR, JIRA, scaffolding               | the matching domain skill                             |

## Install

**Claude Code**

```
/plugin marketplace add witooh/neo-plugin
/plugin install neo@neo
```

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
│ intent detection · flow · gates · resume             │
├─ METHOD LAYER (vendored from mattpocock/skills) ─────┤
│ grilling · domain-modeling · tdd · diagnosing-bugs   │
│ research · prototype                                 │
│ codebase-design · resolving-merge-conflicts          │
├─ DOMAIN LAYER (neo-owned) ───────────────────────────┤
│ code-review · falsifying · bug-hunter                │
│ api-spec · e2e-playwright · openapi-doc              │
│ open-collection · confluence-api-doc · markitdown    │
│ init-project · migrate-project · atlassian · gitlab  │
└──────────────────────────────────────────────────────┘
```

- **Router** — _when_ things happen. One skill, injected into every session.
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
| `using-neo`  | The router — intent, flows, gates, resume                                       |
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
node scripts/validate-skills.js      # frontmatter + dead-reference scan
node scripts/validate-pi-package.js  # pi package wiring
bash hooks/session-start-test.sh     # Claude Code hook
claude plugin validate .             # plugin structure
```

## License

MIT
