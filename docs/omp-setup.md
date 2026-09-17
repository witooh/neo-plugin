# omp Setup

neo ships native omp wiring; no manual copying. Harnesses discover skills only.

## How discovery works

- `package.json` carries an empty `omp` block (enough for harness discovery). There is no `extensions` array:

  ```json
  "omp": {}
  ```

- Root `plugin.json` targets **Agent Plugins 1.0.0** (`$schema: https://agent-plugins.org/schemas/1.0.0/plugin.schema.json`). On omp 18.1+, that routes `skills/` through the native `agent-plugins` provider instead of the foreign-gated `claude-plugins` path (skills used to vanish unless `enabledProviders` included `claude-plugins`).
- `skills/<name>/SKILL.md` stays the skill layout. Frontmatter is the closed Agent Skills set: `name`, `description`, plus optional `license` / `allowed-tools` / `metadata` / `compatibility` (a **string**, not a mapping). No `skills` entry in any manifest is needed.
- `.omp-plugin/marketplace.json` is the preferred omp marketplace catalog; `.claude-plugin/marketplace.json` remains the Claude Code fallback. Day-to-day install is still `github:`, not marketplace.
- **Maintainer skill** lives under `.agents/skills/` (`ship`) — not the shipped plugin catalog. Project `.omp/config.yml` sets `skills.customDirectories: [.agents/skills]` so omp still discovers `ship` when the global config has `agents` in `disabledProviders` (common on this machine). Prefer `customDirectories` here; do not touch `disabledProviders` in the project file — `customDirectories` is enough.

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
- After a release (e.g. `v5.0.0`), `--force` pulls the new tip; `omp plugin list` shows the new
  `neo@<version>`.

### Alternatives

```bash
omp plugin link <path-to-local-clone>   # dev: live working tree
```

Claude Code still uses its own marketplace channel (`/plugin marketplace add witooh/neo-plugin` +
`neo@neo`) — that is separate from omp. Do not add `witooh/neo-plugin` as an omp marketplace for
day-to-day use; prefer `github:` so version tracks the git dependency directly.

### Measured notes

Measured on omp 18.1.9: `github:witooh/neo-plugin` installs as `neo@<package.json version>` and is outside `omp plugin upgrade`. A marketplace `neo@neo` cache could stay on an older tip after a release — that is why omp docs use `github:` only. Agent Plugins `$schema` on root `plugin.json` is what keeps user-scope skills loading without `enabledProviders: [claude-plugins]`.

## Verify

```bash
node scripts/validate-omp-package.js
```

Asserts the `omp` block, Agent Plugins 1.0 root `plugin.json`, and marketplace catalog.
