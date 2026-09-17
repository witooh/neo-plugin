# pi Setup

neo ships native pi wiring; no manual copying. Harnesses discover skills only.

## How discovery works

- `package.json` carries the `pi` block:

  ```json
  "pi": { "skills": ["./skills"] }
  ```

- There is no `extensions` key. Skills load from `skills/`.
- `.pi/skills` is a symlink to `../skills` when present, so a project-local checkout is discovered the same way as an installed package. There is no `.pi/extensions`.

## Verify

```bash
node scripts/validate-pi-package.js
```

Asserts `pi.skills` includes `./skills` and that `pi` has no `extensions` key.
