# Codex Setup

neo installs through a Codex plugin marketplace. It loads the shared `skills/` directory.

## Install from GitHub

With a Codex CLI that supports `codex plugin add` (tested with 0.159.3):

```bash
codex plugin marketplace add witooh/neo-plugin
codex plugin add neo@neo
codex plugin list --marketplace neo
```

Start a new Codex session after installing. You can also open `/plugins` in Codex to browse the registered marketplace and install neo.

## Desktop

Add this marketplace with the CLI command above, then restart the desktop app. Open the Plugins directory, choose the neo marketplace, and install neo. Start a new chat to use its skills.

## Local checkout

Run from this repo:

```bash
codex plugin marketplace add .
codex plugin add neo@neo
```

The catalog points at `./`, relative to the marketplace root. A local marketplace installs this working tree; a GitHub marketplace installs its fetched snapshot. Skill content is shared across all channels.

## Update / uninstall

Refresh a GitHub marketplace and reinstall:

```bash
codex plugin marketplace upgrade neo
codex plugin add neo@neo
```

For a local marketplace, rerun `codex plugin add neo@neo` after editing the checkout. Start a new session after updating.

```bash
codex plugin remove neo@neo
codex plugin marketplace remove neo
```

## Package wiring

- `.agents/plugins/marketplace.json` lists neo at the repo root with an explicit install policy.
- Root `plugin.json` supplies the portable Agent Plugins identity and discovers `skills/` by convention.
- `.codex-plugin/plugin.json` supplies the Codex compatibility metadata, listing, and `./skills/` path. Keep its version in sync with `.claude-plugin/plugin.json`.
- `.agents/skills/ship` stays outside `skills/` and is not an installed domain skill.

## Verify

```bash
node scripts/validate-codex-package.js
node scripts/test-codex-install.js
```

The installation check requires Codex CLI. It uses a temporary Codex home, checks the installed plugin through `skills/list`, and cleans up afterward.

Format and path rules: [OpenAI — Package your plugin](https://developers.openai.com/plugins/build/plugins).
