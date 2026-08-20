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
- `agents/fresh-eyes.md` and `agents/neo-builder.md` are omp task agents discovered from the plugin package root. Do not also install same-named files under `~/.omp/agent/agents/` — user-level names win and hide plugin updates.
- **Maintainer skills** live under `.agents/skills/` (`ship`, `sync-mattpocock`) — not the shipped plugin catalog. Project `.omp/config.yml` sets `skills.customDirectories: [.agents/skills]` so omp still discovers them when the global config has `agents` in `disabledProviders` (common on this machine). Prefer `customDirectories` here; do not touch `disabledProviders` in the project file — `customDirectories` is enough.

## Install

```bash
omp plugin install github:witooh/neo-plugin
```

Lists under **npm Plugins** as `neo@<version>` (from `package.json` on the repo tip).

### Update / uninstall

```bash
# update — same install command + --force (re-resolves github:witooh/neo-plugin)
omp plugin install github:witooh/neo-plugin --force

omp plugin uninstall neo
```

- **Update = force reinstall.** There is no `omp plugin upgrade` path for `github:` installs
  (that command is marketplace-only: `name@marketplace`).
- After a release (e.g. `v3.4.0`), `--force` pulls the new tip; `omp plugin list` shows the new
  `neo@<version>`.

### Alternatives

```bash
omp plugin link <path-to-local-clone>   # dev: live working tree
```

Claude Code still uses its own marketplace channel (`/plugin marketplace add witooh/neo-plugin` +
`neo@neo`) — that is separate from omp. Do not add `witooh/neo-plugin` as an omp marketplace for
day-to-day use; prefer `github:` so version tracks the git dependency directly.

### Measured notes

Measured on omp 17.x: `github:witooh/neo-plugin` installs as `neo@3.4.0` and is outside
`omp plugin upgrade`. A marketplace `neo@neo` cache could stay on an older tip after a release
(e.g. report "upgraded to 3.3.0" while `v3.4.0` was already shipped) — that is why omp docs use
`github:` only.

## Verify

```bash
node scripts/validate-omp-package.js
```

Asserts the `omp` manifest block, the ESM factory export, and that `before_agent_start` appends exactly one router block while preserving the existing blocks (and no steering index).
