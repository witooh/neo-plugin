# omp Setup

neo ships native omp wiring; no manual copying.

## How discovery works

- `package.json` carries the `omp` block (omp reads `omp` first and falls back to `pi`):

  ```json
  "omp": {
    "extensions": ["./extensions/using-neo-session-start.mjs"]
  }
  ```

- `extensions/using-neo-session-start.mjs` is an ESM factory — omp's extension loader rejects the CommonJS pi module (`Extension does not export a valid factory function`), so the two harnesses get one file each over the same `skills/using-neo/SKILL.md`.
- omp hands `before_agent_start` an ordered `systemPrompt` **block array** (14.7+) and takes one back; the extension appends the router as its own block instead of string-joining, which would flatten the base prompt into a comma-separated line.
- `skills/<name>/SKILL.md` is omp's native skill layout, so the plugin's skills are discovered alongside the extension. No `skills` entry in the manifest is needed.
- **Maintainer skills** live under `.agents/skills/` (`ship`, `sync-mattpocock`) — not the shipped plugin catalog. Project `.omp/config.yml` sets `skills.customDirectories: [.agents/skills]` so omp still discovers them when the global config has `agents` in `disabledProviders` (common on this machine). Prefer `customDirectories` here; do not touch `disabledProviders` in the project file — `customDirectories` is enough.

## Install

### Marketplace (recommended — enables upgrade)

```bash
omp plugin marketplace add witooh/neo-plugin
omp plugin install neo@neo
```

Id is `neo@neo` (plugin name @ marketplace name). Catalog is `.claude-plugin/marketplace.json` in this repo (`source: "./"` — the marketplace repo is the plugin).

### Upgrade / uninstall

```bash
omp plugin upgrade              # every outdated marketplace plugin
omp plugin upgrade neo@neo      # neo only
omp plugin uninstall neo@neo
```

- `omp plugin upgrade` **requires** `name@marketplace`. Bare `neo` is rejected.
- Version comes from the installed plugin's manifest (`package.json` / `.claude-plugin/plugin.json`) after the marketplace catalog is refreshed; cutting a release that bumps those fields is what makes a newer version visible.
- `marketplace.autoUpdate` (`off` / `notify` / `auto`, default `notify`) only applies to marketplace plugins.

### Alternatives (no upgrade channel)

```bash
omp plugin install github:witooh/neo-plugin   # git dep; reinstall/force to move versions
omp plugin link <path-to-local-clone>        # points at a working tree
```

Do not expect `omp plugin upgrade` to move a `github:` or `link` install.

### Measured notes

Measured on omp 17.2.2 / 17.2.9: marketplace `neo@neo` installs and lists under Marketplace Plugins; `github:witooh/neo-plugin` lists under npm Plugins and is outside `upgrade`. A local `plugin link` was checked against a dumped `systemPrompt` (router block appended, skills present). Prefer marketplace when you want version notify/upgrade.

## Verify

```bash
node scripts/validate-omp-package.js
```

Asserts the `omp` manifest block, the ESM factory export, and that `before_agent_start` appends exactly one router block while preserving the existing blocks (and no steering index).
