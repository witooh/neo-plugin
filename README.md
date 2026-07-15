# Neo

**Production-grade engineering skills for AI coding agents.**

Skills encode the workflows, quality gates, and best practices that senior engineers use when building software. These ones are packaged so AI agents follow them consistently across every phase of development.

```
  INGEST        DEFINE        PLAN          BUILD         VERIFY        REVIEW        SHIP
 ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐      ┌──────┐
 │Source│ ───▶ │ Idea │ ───▶ │ Spec │ ───▶ │ Code │ ───▶ │ Test │ ───▶ │  QA  │ ───▶ │  Go  │
 │Curate│      │Refine│      │  PRD │      │ Impl │      │Debug │      │ Gate │      │ Live │
 └──────┘      └──────┘      └──────┘      └──────┘      └──────┘      └──────┘      └──────┘
                       using-neo — one adaptive entry point
```

---

## Single Entry Point

Start every workflow with **`using-neo`**. It reads your intent and repository
state, loads only the relevant phase contract, then invokes the underlying
method skills automatically.

| What you're doing | Routed workflow | Core method |
|---|---|---|
| Capture external context | Ingest | `markitdown` |
| Define what to build | Define | `spec-driven-development` |
| Break work into tasks | Plan | `planning-and-task-breakdown` |
| Build incrementally | Build | `incremental-implementation` + `test-driven-development` |
| Prove behavior | Verify | `test-driven-development` and runtime companions |
| Review and simplify | Review | review, security, performance, and simplification skills |
| Prepare commits | Commit | `git-workflow-and-versioning` |
| Audit web performance | Webperf | `web-performance-auditor` / `performance-optimization` |
| Decide production readiness | Ship | `shipping-and-launch` plus specialist fan-out |

With no mode, `using-neo` adapts to a focused request. **`using-neo single`** runs
one task or phase. **`using-neo auto`** advances after one approval while still
stopping at commit, ship, blockers, and high-risk work. Asking it to implement
an approved full plan selects Build auto without widening the request to Ship.

---

## Quick Start

<details>
<summary><b>Codex</b></summary>

**Marketplace install:**

```bash
codex plugin marketplace add witooh/neo-plugin
codex plugin add neo@neo
```

**Local / development:**

```bash
git clone https://github.com/witooh/neo-plugin.git
cd neo-plugin
codex plugin marketplace add .
codex plugin add neo@neo
```

Start a new Codex thread after installation to load the skills.

</details>

<details>
<summary><b>Claude Code (recommended)</b></summary>

**Marketplace install:**

```
/plugin marketplace add witooh/neo-plugin
/plugin install neo@neo
```

> **SSH errors?** The marketplace clones repos via SSH. If you don't have SSH keys set up on GitHub, either [add your SSH key](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account) or use the full HTTPS URL to force the HTTPS cloning:
>
> ```bash
> /plugin marketplace add https://github.com/witooh/neo-plugin.git
> /plugin install neo@neo
> ```

**Local / development:**

```bash
git clone https://github.com/witooh/neo-plugin.git
claude --plugin-dir /path/to/neo
```

</details>

<details>
<summary><b>GitHub Copilot</b></summary>

Install as a native Copilot plugin to load all skills, four custom subagents, and the neo session-start router together. See [docs/copilot-setup.md](docs/copilot-setup.md).

**Marketplace install:**

```bash
copilot plugin marketplace add witooh/neo-plugin
copilot plugin install neo@neo
```

**Direct install from GitHub:**

```bash
copilot plugin install witooh/neo-plugin
```

**Local / development:**

```bash
git clone https://github.com/witooh/neo-plugin.git
copilot plugin install ./neo-plugin
```

</details>

<details>
<summary><b>Gemini CLI</b></summary>

Install as native skills for auto-discovery, or add to `GEMINI.md` for persistent context. See [docs/gemini-cli-setup.md](docs/gemini-cli-setup.md).

**Install from the repo:**

```bash
gemini skills install https://github.com/witooh/neo-plugin.git --path skills
```

**Install from a local clone:**

```bash
gemini skills install ./neo/skills/
```

</details>

<details>
<summary><b>Cursor</b></summary>

Run `cursor.sh` to install neo's native skills, subagents, and a `sessionStart` hook that loads `using-neo` plus `.kiro/steering/INDEX.md` when present. The installer supports project (`.cursor/`) and global (`~/.cursor/`) scopes and preserves unrelated hooks. See [docs/cursor-setup.md](docs/cursor-setup.md).

</details>

<details>
<summary><b>Antigravity CLI</b></summary>

Install as a native plugin for skills and subagents. See [docs/antigravity-setup.md](docs/antigravity-setup.md).

**Install from the repo:**

```bash
agy plugin install https://github.com/witooh/neo-plugin.git
```

**Install from a local clone:**

```bash
git clone https://github.com/witooh/neo-plugin.git
agy plugin install ./neo
```

</details>

<details>
<summary><b>Windsurf</b></summary>

Add skill contents to your Windsurf rules configuration. See [docs/windsurf-setup.md](docs/windsurf-setup.md).

</details>

<details>
<summary><b>OpenCode</b></summary>

Uses agent-driven skill execution via AGENTS.md and the `skill` tool.

See [docs/opencode-setup.md](docs/opencode-setup.md).

</details>

<details>
<summary><b>pi</b></summary>

Installs as a native pi package; skills load unchanged and run via agent-driven selection (no slash commands). See [docs/pi-setup.md](docs/pi-setup.md).

**Install from the repo:**

```bash
pi install git:github.com/witooh/neo-plugin
```

**Install from a local clone:**

```bash
git clone https://github.com/witooh/neo-plugin.git
pi install ./neo-plugin
```

</details>

<details>
<summary><b>Kiro IDE & CLI</b></summary>

Run `kiro.sh` to install neo's skills (as `/<name>` slash commands), agents, and a SessionStart hook that loads `using-neo` plus `.kiro/steering/INDEX.md` when present (Kiro IDE 1.0 / CLI v3) into a Kiro config directory (`.kiro/`). See the Kiro [skills](https://kiro.dev/docs/skills/) and [hooks](https://kiro.dev/docs/hooks/) docs.

**Install globally (`~/.kiro`):**

```bash
git clone https://github.com/witooh/neo-plugin.git
cd neo-plugin
./kiro.sh
```

**Install into a project (`DIR/.kiro`):**

```bash
./kiro.sh --project /path/to/your-project
```

Re-running overwrites only neo-owned entries; other Kiro content is left intact.

</details>

<details>
<summary><b>Other Agents</b></summary>

Skills are plain Markdown - they work with any agent that accepts system prompts or instruction files. See [docs/getting-started.md](docs/getting-started.md).

</details>

---

## All 34 Skills

`using-neo` is the only lifecycle entry point. Method skills remain directly
reusable when explicitly requested.

### Single entry - Route and run the lifecycle

| Skill                                  | What It Does                                                                      | Use When                                           |
| -------------------------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------- |
| [using-neo](skills/using-neo/SKILL.md) | Adaptively routes focused work or drives the lifecycle with single/auto modes and safety gates | Starting any neo-assisted task |

### Ingest - Capture external context

| Skill                                    | What It Does                                                                                                                                                               | Use When                                                                                   |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| [markitdown](skills/markitdown/SKILL.md) | Ingest an external source (URL, doc, card, image, audio) into `docs/knowledge/` as curated, reusable context with provenance — converts complex files via `uvx markitdown` | You need external docs, tickets, or specs captured into the knowledge base before building |

### Define - Clarify what to build

| Skill                                                              | What It Does                                                                                                                                   | Use When                                                                                     |
| ------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------- |
| [interview-me](skills/interview-me/SKILL.md)                       | One-question-at-a-time interview that extracts what the user actually wants instead of what they think they should want, until ~95% confidence | The ask is underspecified, or the user invokes "interview me" / "grill me"                   |
| [idea-refine](skills/idea-refine/SKILL.md)                         | Structured divergent/convergent thinking to turn vague ideas into concrete proposals                                                           | You have a rough concept that needs exploration                                              |
| [spec-driven-development](skills/spec-driven-development/SKILL.md) | Write a PRD covering objectives, commands, structure, code style, testing, and boundaries before any code                                      | Starting a new project, feature, or significant change                                       |
| [api-spec](skills/api-spec/SKILL.md)                               | Author the custom-YAML `docs/api/` HTTP contract spec-first (Draft, in Define); reconcile it from built code at Ship (Update-from-code)        | Designing or updating an HTTP API contract — before code, or syncing the spec back from code |

### Plan - Break it down

| Skill                                                                      | What It Does                                                                                  | Use When                                     |
| -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------- |
| [planning-and-task-breakdown](skills/planning-and-task-breakdown/SKILL.md) | Decompose specs into small, verifiable tasks with acceptance criteria and dependency ordering | You have a spec and need implementable units |

### Build - Write the code

| Skill                                                                    | What It Does                                                                                                                                                                | Use When                                                                                                                                             |
| ------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| [incremental-implementation](skills/incremental-implementation/SKILL.md) | Thin vertical slices - implement, test, verify, commit. Feature flags, safe defaults, rollback-friendly changes                                                             | Any change touching more than one file                                                                                                               |
| [test-driven-development](skills/test-driven-development/SKILL.md)       | Red-Green-Refactor, test pyramid (80/15/5), test sizes, DAMP over DRY, Beyonce Rule, browser testing                                                                        | Implementing logic, fixing bugs, or changing behavior                                                                                                |
| [context-engineering](skills/context-engineering/SKILL.md)               | Feed agents the right information at the right time - rules files, context packing, MCP integrations                                                                        | Starting a session, switching tasks, or when output quality drops                                                                                    |
| [source-driven-development](skills/source-driven-development/SKILL.md)   | Ground every framework decision in official documentation - verify, cite sources, flag what's unverified                                                                    | You want authoritative, source-cited code for any framework or library                                                                               |
| [doubt-driven-development](skills/doubt-driven-development/SKILL.md)     | Adversarial fresh-context review of every non-trivial decision in-flight - CLAIM → EXTRACT → DOUBT → RECONCILE → STOP, with optional user-authorized cross-model escalation | Stakes are high (production, security, irreversible), working in unfamiliar code, or a confident output is cheaper to verify now than to debug later |
| [frontend-ui-engineering](skills/frontend-ui-engineering/SKILL.md)       | Component architecture, design systems, state management, responsive design, WCAG 2.1 AA accessibility                                                                      | Building or modifying user-facing interfaces                                                                                                         |
| [api-and-interface-design](skills/api-and-interface-design/SKILL.md)     | Contract-first design, Hyrum's Law, One-Version Rule, error semantics, boundary validation                                                                                  | Designing APIs, module boundaries, or public interfaces                                                                                              |

### Verify - Prove it works

| Skill                                                                          | What It Does                                                                                                                                                   | Use When                                                                                              |
| ------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| [e2e-playwright](skills/e2e-playwright/SKILL.md)                               | Author + run AC-traceable HTTP e2e (Jest + Playwright-`request`), one test per acceptance criterion; three-layer verify; the suite is the HTTP acceptance gate | Writing or running AC-driven HTTP end-to-end tests for a service with a Jest + Playwright e2e harness |
| [browser-testing-with-devtools](skills/browser-testing-with-devtools/SKILL.md) | Chrome DevTools MCP for live runtime data - DOM inspection, console logs, network traces, performance profiling                                                | Building or debugging anything that runs in a browser                                                 |
| [debugging-and-error-recovery](skills/debugging-and-error-recovery/SKILL.md)   | Five-step triage: reproduce, localize, reduce, fix, guard. Stop-the-line rule, safe fallbacks                                                                  | Tests fail, builds break, or behavior is unexpected                                                   |

### Review - Quality gates before merge

| Skill                                                                | What It Does                                                                                                               | Use When                                                          |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| [code-review-and-quality](skills/code-review-and-quality/SKILL.md)   | Five-axis review, change sizing (~100 lines), severity labels (Nit/Optional/FYI), review speed norms, splitting strategies | Before merging any change                                         |
| [code-simplification](skills/code-simplification/SKILL.md)           | Chesterton's Fence, Rule of 500, reduce complexity while preserving exact behavior                                         | Code works but is harder to read or maintain than it should be    |
| [security-and-hardening](skills/security-and-hardening/SKILL.md)     | OWASP Top 10 prevention, auth patterns, secrets management, dependency auditing, three-tier boundary system                | Handling user input, auth, data storage, or external integrations |
| [performance-optimization](skills/performance-optimization/SKILL.md) | Measure-first approach - Core Web Vitals targets, profiling workflows, bundle analysis, anti-pattern detection             | Performance requirements exist or you suspect regressions         |

### Ship - Deploy with confidence

| Skill                                                                                  | What It Does                                                                                                                                | Use When                                                                  |
| -------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| [git-workflow-and-versioning](skills/git-workflow-and-versioning/SKILL.md)             | Trunk-based development, atomic commits, change sizing (~100 lines), the commit-as-save-point pattern                                       | Making any code change (always)                                           |
| [ci-cd-and-automation](skills/ci-cd-and-automation/SKILL.md)                           | Shift Left, Faster is Safer, feature flags, quality gate pipelines, failure feedback loops                                                  | Setting up or modifying build and deploy pipelines                        |
| [deprecation-and-migration](skills/deprecation-and-migration/SKILL.md)                 | Code-as-liability mindset, compulsory vs advisory deprecation, migration patterns, zombie code removal                                      | Removing old systems, migrating users, or sunsetting features             |
| [documentation-and-adrs](skills/documentation-and-adrs/SKILL.md)                       | Architecture Decision Records, API docs, inline documentation standards - document the _why_                                                | Making architectural decisions, changing APIs, or shipping features       |
| [observability-and-instrumentation](skills/observability-and-instrumentation/SKILL.md) | Structured logging, RED metrics, OpenTelemetry tracing, symptom-based alerting - instrument as you build                                    | Adding telemetry, or shipping anything that runs in production            |
| [shipping-and-launch](skills/shipping-and-launch/SKILL.md)                             | Pre-launch checklists, feature flag lifecycle, staged rollouts, rollback procedures, monitoring setup                                       | Preparing to deploy to production                                         |
| [open-collection](skills/open-collection/SKILL.md)                                     | Generate a runnable, self-documenting Bruno OpenCollection from the `docs/api` spec — one request per endpoint, with environments and auth  | Shipping a runnable API-collection deliverable from the docs/api contract |
| [confluence-api-doc](skills/confluence-api-doc/SKILL.md)                               | Publish the `docs/api` spec to Confluence — one page per endpoint under domain-group parents; acli + REST sync with three-layer verify      | Publishing the API contract to Confluence at ship time                    |
| [openapi-doc](skills/openapi-doc/SKILL.md)                                             | Read-only drift report: diff Go against the `docs/api` spec (routes, fields, M/O, types) so api-spec can reconcile — the sync-back detector | Auditing whether the code still matches the documented API contract       |

---

## Agent Personas

Pre-configured specialist personas for targeted reviews:

| Agent                                                        | Role                     | Perspective                                                                                  |
| ------------------------------------------------------------ | ------------------------ | -------------------------------------------------------------------------------------------- |
| [code-reviewer](agents/code-reviewer.md)                     | Senior Staff Engineer    | Five-axis code review with "would a staff engineer approve this?" standard                   |
| [test-engineer](agents/test-engineer.md)                     | QA Specialist            | Test strategy, coverage analysis, and the Prove-It pattern                                   |
| [security-auditor](agents/security-auditor.md)               | Security Engineer        | Vulnerability detection, threat modeling, OWASP assessment                                   |
| [web-performance-auditor](agents/web-performance-auditor.md) | Web Performance Engineer | Core Web Vitals audit with Quick/Deep modes and a metric-honesty rule; route it through `using-neo` Webperf |

See [docs/agents.md](docs/agents.md) for the decision matrix, orchestration rules, and how personas compose with skills.

---

## Reference Checklists

Quick-reference material that skills pull in when needed:

| Reference                                                           | Covers                                                                                                      |
| ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| [definition-of-done.md](references/definition-of-done.md)           | Project-wide standing bar every change clears, contrasted with per-task acceptance criteria                 |
| [testing-patterns.md](references/testing-patterns.md)               | Test structure, naming, mocking, React/API/E2E examples, anti-patterns                                      |
| [security-checklist.md](references/security-checklist.md)           | Pre-commit checks, auth, input validation, headers, CORS, OWASP Top 10                                      |
| [performance-checklist.md](references/performance-checklist.md)     | Core Web Vitals targets, frontend/backend checklists, measurement commands                                  |
| [accessibility-checklist.md](references/accessibility-checklist.md) | Keyboard nav, screen readers, visual design, ARIA, testing tools                                            |
| [observability-checklist.md](references/observability-checklist.md) | On-call questions, structured logging, RED/USE metrics, tracing, symptom-based alerting, pre-launch gate    |
| [orchestration-patterns.md](references/orchestration-patterns.md)   | Endorsed multi-persona orchestration patterns, anti-patterns, and the "personas don't invoke personas" rule |

---

## How Skills Work

Every skill follows a consistent anatomy:

```
┌─────────────────────────────────────────────────┐
│  SKILL.md                                       │
│                                                 │
│  ┌─ Frontmatter ─────────────────────────────┐  │
│  │ name: lowercase-hyphen-name               │  │
│  │ description: Guides agents through [task].│  │
│  │              Use when…                    │  │
│  └───────────────────────────────────────────┘  │
│  Overview         → What this skill does        │
│  When to Use      → Triggering conditions       │
│  Process          → Step-by-step workflow       │
│  Rationalizations → Excuses + rebuttals         │
│  Red Flags        → Signs something's wrong     │
│  Verification     → Evidence requirements       │
└─────────────────────────────────────────────────┘
```

**Key design choices:**

- **Process, not prose.** Skills are workflows agents follow, not reference docs they read. Each has steps, checkpoints, and exit criteria.
- **Anti-rationalization.** Every skill includes a table of common excuses agents use to skip steps (e.g., "I'll add tests later") with documented counter-arguments.
- **Verification is non-negotiable.** Every skill ends with evidence requirements - tests passing, build output, runtime data. "Seems right" is never sufficient.
- **Progressive disclosure.** The `SKILL.md` is the entry point. Supporting references load only when needed, keeping token usage minimal.

---

## Project Structure

```
neo/
├── skills/                            # 34 active skills
│   ├── using-neo/                     #   Single adaptive entry + phase references
│   ├── markitdown/                    #   Ingest
│   ├── interview-me/                  #   Define
│   ├── idea-refine/                   #   Define
│   ├── spec-driven-development/       #   Define
│   ├── api-spec/                      #   Define / Ship (docs/api contract)
│   ├── planning-and-task-breakdown/   #   Plan
│   ├── incremental-implementation/    #   Build
│   ├── context-engineering/           #   Build
│   ├── source-driven-development/     #   Build
│   ├── doubt-driven-development/      #   Build
│   ├── frontend-ui-engineering/       #   Build
│   ├── test-driven-development/       #   Build
│   ├── api-and-interface-design/      #   Build
│   ├── browser-testing-with-devtools/ #   Verify
│   ├── debugging-and-error-recovery/  #   Verify
│   ├── e2e-playwright/                #   Verify (AC-driven HTTP e2e)
│   ├── code-review-and-quality/       #   Review
│   ├── code-simplification/          #   Review
│   ├── security-and-hardening/        #   Review
│   ├── performance-optimization/      #   Review
│   ├── git-workflow-and-versioning/   #   Ship
│   ├── ci-cd-and-automation/          #   Ship
│   ├── deprecation-and-migration/     #   Ship
│   ├── documentation-and-adrs/        #   Ship
│   ├── observability-and-instrumentation/ # Ship
│   ├── shipping-and-launch/           #   Ship
│   ├── openapi-doc/                   #   API docs (Go↔spec drift report)
│   ├── open-collection/               #   API docs (Bruno collection)
│   ├── confluence-api-doc/            #   API docs (Confluence)
│   ├── init-project/                  #   Scaffold (new Go service)
│   ├── migrate-project/               #   Scaffold (brownfield migration)
│   ├── atlassian/                     #   Integration (Jira/Confluence acli)
│   └── gitlab/                        #   Integration (GitLab)
├── agents/                            # 4 specialist personas
├── references/                        # 7 shared checklists (source of truth — copies bundled into citing skills)
├── hooks/                             # Session lifecycle hooks
├── plugin.json                        # Antigravity plugin manifest
├── package.json                       # pi package manifest
└── docs/                              # Setup guides per tool
```
