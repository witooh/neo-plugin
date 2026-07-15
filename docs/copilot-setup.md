# Using neo with GitHub Copilot

neo installs as a native GitHub Copilot plugin. One installation provides the complete `skills/` pack, all custom agents as Copilot subagents, and a `sessionStart` hook that routes each session through the `using-neo` single entry point.

This guide targets the current `copilot` CLI, not the legacy `gh copilot` extension.

## Prerequisites

Install GitHub Copilot CLI if it is not already available:

```bash
npm install -g @github/copilot
```

The npm installation requires Node.js 22 or later. Copilot plugin availability can also be controlled by organization or enterprise policy.

## Native plugin installation (recommended)

### Install from the neo marketplace

Register this repository as a marketplace, then install neo:

```bash
copilot plugin marketplace add witooh/neo-plugin
copilot plugin install neo@neo
```

The equivalent commands inside an interactive Copilot session are:

```text
/plugin marketplace add witooh/neo-plugin
/plugin install neo@neo
```

### Install directly from GitHub

Use a direct install when you do not need marketplace discovery:

```bash
copilot plugin install witooh/neo-plugin
```

### Install from a local clone

Use this during neo development:

```bash
git clone https://github.com/witooh/neo-plugin.git
copilot plugin install ./neo-plugin
```

Copilot caches installed plugins. Re-run the local install command after changing the plugin source.

## Verify the installation

List installed plugins from the shell:

```bash
copilot plugin list
```

Then start an interactive session and verify the bundled components:

```text
/skills list
/agent
```

The installation should expose:

- Every skill under `skills/`, with `using-neo` as the canonical lifecycle entry point.
- `code-reviewer`, `security-auditor`, `test-engineer`, and `web-performance-auditor` as custom agents. Copilot can select eligible custom agents as isolated subagents, or you can select one explicitly with `/agent`.
- A `sessionStart` hook that tells Copilot to load `using-neo` before acting, so skill discovery remains on-demand instead of injecting all skill bodies into context.

## Update or remove neo

```bash
copilot plugin update neo
copilot plugin uninstall neo
```

After uninstalling neo, inspect or remove the marketplace itself:

```bash
copilot plugin marketplace list
copilot plugin marketplace remove neo
```

## How the cross-harness package is structured

The Copilot adapter reuses the canonical neo content wherever the formats agree:

- `.plugin/plugin.json` is the Copilot-specific manifest. It points directly to the shared `skills/` and `agents/` directories.
- `.plugin/hooks.json` is separate because Copilot hooks use a versioned, camel-case schema that differs from the Claude and Codex hook payloads.
- `.github/plugin/marketplace.json` publishes the repo-root plugin as `neo@neo`.
- Claude Code and Codex keep their own manifests and hook adapters under `.claude-plugin/` and `.codex-plugin/`; Antigravity keeps using the root `plugin.json`.

This avoids copied skill or persona content while allowing each harness to keep its native manifest and hook contract.

## Manual project-local fallback

If plugins are disabled in your Copilot environment, install the same content at repository scope.

### Skills

Copilot discovers skills from `.github/skills/`, `.agents/skills/`, or `.claude/skills/`:

```bash
mkdir -p .github/skills
cp -R /path/to/neo/skills/. .github/skills/
```

### Custom agents

Repository-level Copilot agent files use the `*.agent.md` convention:

```bash
mkdir -p .github/agents
cp /path/to/neo/agents/code-reviewer.md \
  .github/agents/code-reviewer.agent.md
cp /path/to/neo/agents/test-engineer.md \
  .github/agents/test-engineer.agent.md
cp /path/to/neo/agents/security-auditor.md \
  .github/agents/security-auditor.agent.md
cp /path/to/neo/agents/web-performance-auditor.md \
  .github/agents/web-performance-auditor.agent.md
```

### Always-on routing without the plugin hook

Add this rule to the project's `AGENTS.md`:

> At the start of every session, before acting on any task, load `.github/skills/using-neo/SKILL.md` as neo's single entry point. Route every request through its adaptive rules, then load and follow only the selected phase contract and method skills before implementation.

This fallback relies on model compliance; the native plugin's `sessionStart` hook is the stronger setup.

## Official references

- [Finding and installing plugins for GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-finding-installing)
- [Creating a plugin for GitHub Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/customize-copilot/plugins-creating)
- [GitHub Copilot CLI plugin reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference)
- [GitHub Copilot hooks reference](https://docs.github.com/en/copilot/reference/hooks-reference)
- [Custom agents configuration](https://docs.github.com/en/copilot/reference/custom-agents-configuration)
