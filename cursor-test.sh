#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

project_dir="$tmp_dir/project"
global_home="$tmp_dir/home"
mkdir -p "$project_dir/.cursor/hooks" "$global_home/.cursor"
printf '%s\n' '# user-owned hook' > "$project_dir/.cursor/hooks/user-owned.sh"
cat > "$project_dir/.cursor/hooks.json" <<'JSON'
{
  "version": 1,
  "hooks": {
    "sessionStart": [
      { "command": "bash .cursor/hooks/user-owned.sh", "timeout": 9 }
    ],
    "stop": [
      { "command": "true" }
    ]
  },
  "userSetting": "keep"
}
JSON

"$SCRIPT_DIR/cursor.sh" --project "$project_dir" >/dev/null

if [ ! -f "$project_dir/.cursor/skills/using-neo/SKILL.md" ]; then
  echo "FAIL: cursor.sh omitted using-neo from project skills" >&2
  exit 1
fi
if [ ! -f "$project_dir/.cursor/agents/fresh-eyes.md" ]; then
  echo "FAIL: cursor.sh omitted fresh-eyes" >&2
  exit 1
fi
if [ ! -f "$project_dir/.cursor/agents/neo-builder.md" ]; then
  echo "FAIL: cursor.sh omitted neo-builder" >&2
  exit 1
fi
if [ ! -f "$project_dir/.cursor/agents/neo-author.md" ]; then
  echo "FAIL: cursor.sh omitted neo-author" >&2
  exit 1
fi
if [ ! -f "$project_dir/.cursor/agents/neo-e2e.md" ]; then
  echo "FAIL: cursor.sh omitted neo-e2e" >&2
  exit 1
fi
if [ ! -f "$project_dir/.cursor/hooks/neo-session-context.sh" ]; then
  echo "FAIL: cursor.sh omitted the project hook script" >&2
  exit 1
fi
if [ ! -f "$project_dir/.cursor/hooks/user-owned.sh" ]; then
  echo "FAIL: cursor.sh removed a user-owned hook script" >&2
  exit 1
fi

hook_path="$project_dir/.cursor/hooks.json"
hook_command="$(HOOK_PATH="$hook_path" node <<'NODE'
const fs = require('fs');
const config = JSON.parse(fs.readFileSync(process.env.HOOK_PATH, 'utf8'));
const sessionStart = config.hooks?.sessionStart;

if (config.version !== 1) throw new Error('expected Cursor hook schema version 1');
if (!Array.isArray(sessionStart)) throw new Error('expected sessionStart hooks');
if (!sessionStart.some((hook) => hook.command === 'bash .cursor/hooks/user-owned.sh')) {
  throw new Error('user-owned sessionStart hook was removed');
}
if (config.hooks?.stop?.[0]?.command !== 'true') throw new Error('stop hook was changed');
if (config.userSetting !== 'keep') throw new Error('unrelated hook config was changed');

const neoHooks = sessionStart.filter((hook) =>
  hook.command === 'bash .cursor/hooks/neo-session-context.sh'
);
if (neoHooks.length !== 1) throw new Error('expected exactly one neo sessionStart hook');
if (neoHooks[0].timeout !== 5) throw new Error('expected neo hook timeout 5');

process.stdout.write(neoHooks[0].command);
NODE
)"

event_input="$(jq -cn --arg root "$project_dir" '{workspace_roots: [$root]}')"
without_index="$(
  cd "$project_dir"
  printf '%s' "$event_input" | sh -c "$hook_command"
)"
without_index_context="$(printf '%s' "$without_index" | jq -er '.additional_context | strings')"

if [[ "$without_index_context" != *"# Using Neo"* ]]; then
  echo "FAIL: Cursor hook omitted using-neo without INDEX.md" >&2
  exit 1
fi
if [[ "$without_index_context" != *"## Intent table"* ]]; then
  echo "FAIL: Cursor hook emitted incomplete using-neo context" >&2
  exit 1
fi
if [[ "$without_index_context" == *"Read and follow .kiro/steering/INDEX.md"* ]]; then
  echo "FAIL: Cursor hook requested a missing INDEX.md" >&2
  exit 1
fi

mkdir -p "$project_dir/.kiro/steering"
printf '%s\n' 'CURSOR_STEERING_INDEX_SENTINEL' > "$project_dir/.kiro/steering/INDEX.md"
with_index="$(
  cd "$project_dir"
  printf '%s' "$event_input" | sh -c "$hook_command"
)"
with_index_context="$(printf '%s' "$with_index" | jq -er '.additional_context | strings')"

if [[ "$with_index_context" != *"# Using Neo"* ]]; then
  echo "FAIL: Cursor hook omitted using-neo when INDEX.md exists" >&2
  exit 1
fi
if [[ "$with_index_context" != *"Read and follow .kiro/steering/INDEX.md"* ]]; then
  echo "FAIL: Cursor hook omitted the INDEX.md instruction" >&2
  exit 1
fi
if [[ "$with_index_context" != *"CURSOR_STEERING_INDEX_SENTINEL"* ]]; then
  echo "FAIL: Cursor hook omitted INDEX.md content" >&2
  exit 1
fi

"$SCRIPT_DIR/cursor.sh" --project "$project_dir" >/dev/null
neo_hook_count="$(jq '[.hooks.sessionStart[] | select(.command == "bash .cursor/hooks/neo-session-context.sh")] | length' "$hook_path")"
if [ "$neo_hook_count" -ne 1 ]; then
  echo "FAIL: re-running cursor.sh duplicated the project hook" >&2
  exit 1
fi

cat > "$global_home/.cursor/hooks.json" <<'JSON'
{
  "version": 1,
  "hooks": {
    "beforeShellExecution": [
      { "command": "bash ./hooks/user-owned.sh" }
    ]
  }
}
JSON

HOME="$global_home" "$SCRIPT_DIR/cursor.sh" --global >/dev/null
global_hook_path="$global_home/.cursor/hooks.json"
global_hook_command="$(jq -er '.hooks.sessionStart[] | select(.command == "bash ./hooks/neo-session-context.sh") | .command' "$global_hook_path")"

if [ ! -f "$global_home/.cursor/skills/using-neo/SKILL.md" ]; then
  echo "FAIL: global install omitted using-neo" >&2
  exit 1
fi
if [ ! -f "$global_home/.cursor/hooks/neo-session-context.sh" ]; then
  echo "FAIL: global install omitted the hook script" >&2
  exit 1
fi
if [ "$(jq -r '.hooks.beforeShellExecution[0].command' "$global_hook_path")" != "bash ./hooks/user-owned.sh" ]; then
  echo "FAIL: global install changed a user-owned hook" >&2
  exit 1
fi

global_project="$tmp_dir/global-project"
mkdir -p "$global_project"
global_event_input="$(jq -cn --arg root "$global_project" '{workspace_roots: [$root]}')"
global_output="$(
  cd "$global_home/.cursor"
  printf '%s' "$global_event_input" | HOME="$global_home" sh -c "$global_hook_command"
)"
global_context="$(printf '%s' "$global_output" | jq -er '.additional_context | strings')"

if [[ "$global_context" != *"# Using Neo"* ]]; then
  echo "FAIL: global Cursor hook did not load ~/.cursor/skills/using-neo/SKILL.md" >&2
  exit 1
fi

echo "PASS: cursor.sh installs Cursor skills, subagents, and conditional session context"
