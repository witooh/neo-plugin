# Using neo with Cursor

Cursor natively discovers [Agent Skills](https://cursor.com/docs/skills),
[custom subagents](https://cursor.com/docs/subagents), and
[hooks](https://cursor.com/docs/hooks). The `cursor.sh` installer puts neo in
those native locations and requires `jq` to merge hook configuration safely.

## Install globally

Install for every Cursor project under `~/.cursor/`:

```bash
./cursor.sh
# or: ./cursor.sh --global
```

## Install in one project

Install under `<project>/.cursor/`:

```bash
./cursor.sh --project /path/to/project
```

Running the installer again refreshes neo-owned skills, subagents, and the neo
hook. Other files and hook entries remain intact.

## Installed layout

```text
.cursor/
├── skills/                    # one <name>/SKILL.md directory per neo skill
├── agents/                    # neo custom subagents
├── hooks/
│   └── neo-session-context.sh
└── hooks.json                 # neo sessionStart entry merged with existing hooks
```

Shared reference checklists are copied into each skill that cites them, so
relative `references/<file>.md` links continue to work inside Cursor's
self-contained skill directories.

## Session context

At `sessionStart`, the hook returns Cursor's documented `additional_context`
JSON response containing:

1. The project's `.cursor/skills/using-neo/SKILL.md`, falling back to the
   `using-neo` installed beside the hook.
2. The project's `.kiro/steering/INDEX.md` only when that file exists, including
   an instruction to read every guide it marks with `inclusion: always`.

Cursor project hooks run only in trusted workspaces. Check **View → Output →
Hooks** if the hook does not appear to run.

### Cursor IDE limitation

Some Cursor IDE versions have a confirmed issue where `sessionStart` accepts a
valid `additional_context` response but does not deliver it to the agent. The
hook and installer still follow Cursor's documented contract; if the Hooks
output shows a successful response but the agent lacks neo context, check the
[upstream Cursor issue](https://forum.cursor.com/t/cursor-app-hooks-bugs-of-additional-context/163990)
for current status.
