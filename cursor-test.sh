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

hooks_before="$tmp_dir/hooks.json.before"
user_hook_before="$tmp_dir/user-owned.sh.before"
cp "$project_dir/.cursor/hooks.json" "$hooks_before"
cp "$project_dir/.cursor/hooks/user-owned.sh" "$user_hook_before"

"$SCRIPT_DIR/cursor.sh" --project "$project_dir" >/dev/null

if [ ! -f "$project_dir/.cursor/skills/markitdown/SKILL.md" ]; then
  echo "FAIL: cursor.sh omitted markitdown from project skills" >&2
  exit 1
fi
if [ -e "$project_dir/.cursor/skills/using-neo" ]; then
  echo "FAIL: cursor.sh copied using-neo" >&2
  exit 1
fi
if [ -e "$project_dir/.cursor/agents" ]; then
  echo "FAIL: cursor.sh created .cursor/agents/" >&2
  exit 1
fi
if [ -e "$project_dir/.cursor/agents/neo-builder.md" ]; then
  echo "FAIL: cursor.sh created neo-builder.md" >&2
  exit 1
fi
if [ -e "$project_dir/.cursor/hooks/neo-session-context.sh" ]; then
  echo "FAIL: cursor.sh installed neo-session-context.sh" >&2
  exit 1
fi
if ! cmp -s "$hooks_before" "$project_dir/.cursor/hooks.json"; then
  echo "FAIL: cursor.sh mutated existing hooks.json" >&2
  exit 1
fi
if ! cmp -s "$user_hook_before" "$project_dir/.cursor/hooks/user-owned.sh"; then
  echo "FAIL: cursor.sh mutated a user-owned hook" >&2
  exit 1
fi

HOME="$global_home" "$SCRIPT_DIR/cursor.sh" --global >/dev/null
if [ ! -f "$global_home/.cursor/skills/markitdown/SKILL.md" ]; then
  echo "FAIL: global install omitted markitdown" >&2
  exit 1
fi
if [ -e "$global_home/.cursor/skills/using-neo" ]; then
  echo "FAIL: global install copied using-neo" >&2
  exit 1
fi
if [ -e "$global_home/.cursor/agents" ]; then
  echo "FAIL: global install created agents/" >&2
  exit 1
fi
if [ -e "$global_home/.cursor/hooks/neo-session-context.sh" ]; then
  echo "FAIL: global install installed neo-session-context.sh" >&2
  exit 1
fi

echo "PASS: cursor.sh installs Cursor skills only"
