# pi Setup

neo ships native pi wiring; no manual copying.

## How discovery works

- `package.json` carries the `pi` block:

  ```json
  "pi": {
    "extensions": ["./extensions/using-neo-session-start.js"],
    "skills": ["./skills"]
  }
  ```

- `.pi/skills` and `.pi/extensions` are symlinks back to the repo's `skills/` and `extensions/`, so a project-local checkout is discovered the same way as an installed package.
- `extensions/using-neo-session-start.js` injects the full `using-neo` SKILL.md into the system prompt at session start. It does not inject project steering; the agent reads `.kiro/steering/` only when a skill needs it. Graph dispatch: `Task`/`Agent` when the runtime exposes the catalog type; otherwise one node at a time per `skills/using-neo/GRAPH.md`.

## Method layer

Method skills ship under `skills/` (vendored from mattpocock/skills via `sync-mattpocock`). No second install. Maintainers refresh them with:

```bash
python3 .agents/skills/sync-mattpocock/assets/sync.py --apply
```

## Verify

```bash
node scripts/validate-pi-package.js
```

Asserts the package block, both symlinks, and that session start injects only `using-neo` (no steering index).
