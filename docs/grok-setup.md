# Grok Build Setup

neo ships as a native Grok Build plugin. Skills load from `skills/` by convention. There is no session injection.

## How discovery works

- Root `plugin.json` + `.grok-plugin/plugin.json` are the Grok plugin manifests (`name`, `version`, metadata). Skills load from `skills/` by convention.
- `.grok-plugin/marketplace.json` is the catalog. It lists one plugin, `neo`, with a **git URL** source back to this repo.
- Grok 1.0.3 rejects a local marketplace path of `.` or `./` (`marketplace path is empty` / `must not contain current-directory components`). A single-plugin repo therefore cannot vendor itself as `{ "type": "local", "path": "./" }` the way Claude Code does.
- Skills are the same files every other channel uses. Do not fork `SKILL.md` for Grok.

## Install

Direct install (repo is the plugin — measured):

```bash
grok plugin install witooh/neo-plugin --trust
grok plugin enable neo
```

Or add this repo as a marketplace, then install by catalog name. That clones the git URL in the index, not a local working tree:

```bash
grok plugin marketplace add witooh/neo-plugin
grok plugin install neo --trust
grok plugin enable neo
```

`--trust` is required by the CLI. `enable` is separate: Grok leaves plugins off until they are listed in `[plugins].enabled` or enabled in the Plugins tab (`/plugins`, then Space).

Start a new session after enabling. Skills show up as slash commands (`/api-spec`, `/gitlab`, …). When a name collides, Grok shows the qualified form `/neo:api-spec`.

## Update / uninstall

```bash
grok plugin update neo
grok plugin uninstall neo --confirm
```

If you installed via marketplace, refresh the source first: `grok plugin marketplace update`.

Orgs that set `[marketplace] require_sha = true` must pin a 40-character commit `sha` on the url source in `.grok-plugin/marketplace.json` before `install neo` will succeed.

## Local / development

```bash
# copy of this working tree (measured: grok plugin install <abs-path> --trust)
grok plugin install . --trust
grok plugin enable neo
```

`grok plugin marketplace add .` then `install neo` does **not** use the working tree — the catalog entry is the GitHub URL, so it clones `origin`.

For a live working tree (no copy), point Grok at the clone:

```toml
# ~/.grok/config.toml
[plugins]
paths = ["/absolute/path/to/neo-plugin"]
enabled = ["neo"]
```

Then trust it (`grok plugin install . --trust`, or place it under `~/.grok/plugins/`, which is auto-trusted).

## Verify

```bash
node scripts/validate-grok-package.js
grok plugin validate .
```

The script checks the marketplace index, version sync against `.claude-plugin/plugin.json`, default skill paths, and (when `grok` is on PATH) `grok plugin validate`.
