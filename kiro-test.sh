#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

project_dir="$tmp_dir/project"
global_home="$tmp_dir/home"
mkdir -p "$project_dir/.kiro/hooks" "$global_home"
printf '%s\n' '{"version":"v1","hooks":[]}' > "$project_dir/.kiro/hooks/user-owned.json"

user_hook_before="$tmp_dir/user-owned.json.before"
cp "$project_dir/.kiro/hooks/user-owned.json" "$user_hook_before"

"$SCRIPT_DIR/kiro.sh" --project "$project_dir" >/dev/null

if [ ! -f "$project_dir/.kiro/skills/markitdown/SKILL.md" ]; then
  echo "FAIL: kiro.sh omitted markitdown from project skills" >&2
  exit 1
fi
if [ -e "$project_dir/.kiro/skills/using-neo" ]; then
  echo "FAIL: kiro.sh copied using-neo" >&2
  exit 1
fi
if [ -e "$project_dir/.kiro/agents" ]; then
  echo "FAIL: kiro.sh created .kiro/agents/" >&2
  exit 1
fi
if [ -e "$project_dir/.kiro/hooks/neo-session-context.json" ]; then
  echo "FAIL: kiro.sh installed .kiro/hooks/neo-session-context.json" >&2
  exit 1
fi
if ! cmp -s "$user_hook_before" "$project_dir/.kiro/hooks/user-owned.json"; then
  echo "FAIL: kiro.sh mutated a user-owned hook" >&2
  exit 1
fi

HOME="$global_home" "$SCRIPT_DIR/kiro.sh" --global >/dev/null
if [ ! -f "$global_home/.kiro/skills/markitdown/SKILL.md" ]; then
  echo "FAIL: global install omitted markitdown" >&2
  exit 1
fi
if [ -e "$global_home/.kiro/skills/using-neo" ]; then
  echo "FAIL: global install copied using-neo" >&2
  exit 1
fi
if [ -e "$global_home/.kiro/agents" ]; then
  echo "FAIL: global install created agents/" >&2
  exit 1
fi
if [ -e "$global_home/.kiro/hooks/neo-session-context.json" ]; then
  echo "FAIL: global install installed neo-session-context.json" >&2
  exit 1
fi

echo "PASS: kiro.sh installs Kiro skills only"
