# Using neo with Antigravity CLI (agy)

The `neo` package can be installed as a native plugin in the Antigravity CLI (`agy`), giving the agent access to structured workflows and personas.

## Setup

### Option 1: Native Plugin Installation (Recommended)

Antigravity CLI has a first-class plugin system that registers skills and agents.

**Install from the remote repository:**

```bash
agy plugin install https://github.com/witooh/neo-plugin.git
```

**Install from a local clone:**

1. Clone the repository:
   ```bash
   git clone https://github.com/witooh/neo-plugin.git
   ```
2. Install the plugin using `agy`:
   ```bash
   agy plugin install /path/to/neo
   ```

This will validate the plugin and install it into your global Antigravity configuration directory (`~/.gemini/antigravity-cli/plugins/neo/`).

### Option 2: Import from Gemini CLI

If you have already installed `neo` under your legacy Gemini CLI installation, you can import it directly:
```bash
agy plugin import gemini
```

Once installed, verify the active plugin:
```bash
agy plugin list
```

---

## Lifecycle Entry Skills

The plugin ships an entry skill per lifecycle phase, named `neo-<phase>`. Antigravity auto-discovers them alongside the other skills (see *Skills & Discovery* below) — there are no `.toml` commands. Describe your intent and Antigravity activates the matching entry skill, which runs the underlying workflow skill(s):

| Entry skill | What it does | Runs |
|-------------|--------------|------|
| `neo-ingest` | Ingest an external source into the knowledge base | `markitdown` |
| `neo-spec` | Write a structured spec before writing code | `spec-driven-development` |
| `neo-plan` | Break work into small, verifiable tasks | `planning-and-task-breakdown` |
| `neo-build` | Implement the next task incrementally | `incremental-implementation` |
| `neo-test` | Run TDD workflow — red, green, refactor | `test-driven-development` |
| `neo-review` | Five-axis code review | `code-review-and-quality` |
| `neo-code-simplify` | Reduce complexity without changing behavior | `code-simplification` |
| `neo-ship` | Pre-launch checklist via parallel persona fan-out | `shipping-and-launch` |
| `neo-webperf` | Audit browser-facing apps for Core Web Vitals and performance issues | `web-performance-auditor` |
| `neo-commit` | Create clean, atomic commits and judge when to rebase | `git-workflow-and-versioning` |

---

## Skills & Discovery

Antigravity automatically discovers skills inside the plugin's `skills/` directory. 
* Antigravity matches user tasks and intents to relevant skills on-demand.
* If a task matches a skill, the agent will load the skill and prompt you for permission before executing.

---

## Verification & Validation

To validate that your local plugin is correctly structured and contains all skills, run:
```bash
agy plugin validate /path/to/neo
```

---

## How It Works

### 1. On-Demand Skill Activation
Antigravity CLI automatically discovers the `SKILL.md` files located in the `skills/` directory of the installed plugin. Using the trigger descriptions in each skill's frontmatter, the agent will dynamically activate the appropriate workflow when it detects matching developer intent.

For example, when you ask the agent to:
- **Design a new system** &rarr; It will suggest/activate `spec-driven-development`.
- **Implement a feature** &rarr; It will activate `incremental-implementation` and `test-driven-development`.
- **Fix a bug** &rarr; It will activate `debugging-and-error-recovery`.

### 2. Specialized Agent Personas
The plugin registers reusable subagent definitions from the `agents/` directory:
- `code-reviewer.md`
- `security-auditor.md`
- `test-engineer.md`

You can invoke these personas directly within your session or when delegating tasks using subagents.

---

## Configuration & Customization

### Project-Specific Enforcements (`AGENTS.md`)
To enforce strict skill compliance (e.g. requiring a spec or plan before writing code), copy or link `AGENTS.md` into the root of your workspace. Antigravity CLI reads this file to align the agent's behavior and planning phase with your team's conventions.

To replicate Claude Code's `SessionStart` hook (which auto-loads the `using-neo` meta-skill), add the neo-load rule to that `AGENTS.md`:

> At the start of every session, before acting on any task, **load the neo meta-skill `skills/using-neo/SKILL.md`** and keep it in context for the whole session. Route every task through its **Skill Discovery** flowchart: identify the phase, then load and follow the matching `skills/<name>/SKILL.md` exactly — if a skill applies at all, it runs first; never jump straight to implementation. Obey the meta-skill's **Core Operating Behaviors** at all times. This rule is non-negotiable and persists past the first message.

Because no hook enforces it, this depends on model compliance — weaker than Claude Code's hook, but the closest hook-free equivalent.

### Sandbox Mode
If you want to run skills or scripts with limited terminal permissions (for safety when running third-party validation tests), launch the CLI with:

```bash
agy --sandbox
```

---

## Usage Tips

1. **Keep plugins up-to-date:** You can update the CLI or check for newer plugin versions using:
   ```bash
   agy update
   ```
2. **Review before execution:** When agents execute complex refactoring tasks using these skills, use `Ctrl+r` to enter the **Artifact Review** screen to review, edit, or approve code before it is committed.
3. **Control permissions:** You can use the `--dangerously-skip-permissions` flag only in trusted local projects where you want to bypass manual tool approval prompts.
