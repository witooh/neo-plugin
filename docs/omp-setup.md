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

## Install

```bash
omp plugin install github:witooh/neo-plugin   # from GitHub
omp plugin link ./neo-plugin                  # from a local clone
```

Measured on omp 17.2.2. A local `plugin link` was checked against a dumped `systemPrompt`: two blocks, the router appended last, base block untouched, 22 neo skills in the catalog. The git install (`github:witooh/neo-plugin`, v3.2.0) was checked in a live session — the router phrase is present in the system prompt and `using-neo` is listed among the discovered skills. A `/marketplace` install of the same tree loads the router extension but its skills did not reach the catalog; prefer `plugin install` / `plugin link` until that path is confirmed.

## Verify

```bash
node scripts/validate-omp-package.js
```

Asserts the `omp` manifest block, the ESM factory export, and that `before_agent_start` appends exactly one router block while preserving the existing blocks (and no steering index).
