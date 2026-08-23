#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

project_dir="$tmp_dir/project"
global_home="$tmp_dir/home"
mkdir -p "$project_dir/.kiro/hooks" "$global_home"
printf '%s\n' '{"version":"v1","hooks":[]}' > "$project_dir/.kiro/hooks/user-owned.json"

"$SCRIPT_DIR/kiro.sh" --project "$project_dir" >/dev/null

if [ -e "$project_dir/.kiro/steering/AGENTS.md" ]; then
  echo "FAIL: kiro.sh created .kiro/steering/AGENTS.md" >&2
  exit 1
fi

hook_path="$project_dir/.kiro/hooks/neo-session-context.json"
if [ ! -f "$hook_path" ]; then
  echo "FAIL: kiro.sh did not install .kiro/hooks/neo-session-context.json" >&2
  exit 1
fi

if [ ! -f "$project_dir/.kiro/hooks/user-owned.json" ]; then
  echo "FAIL: kiro.sh removed a user-owned hook" >&2
  exit 1
fi

hook_command="$(HOOK_PATH="$hook_path" node <<'NODE'
const fs = require('fs');
const config = JSON.parse(fs.readFileSync(process.env.HOOK_PATH, 'utf8'));
const hook = config.hooks?.[0];

if (config.version !== 'v1') throw new Error('expected Kiro hook schema v1');
if (config.hooks?.length !== 1) throw new Error('expected one Kiro hook');
if (hook.name !== 'neo-session-context') throw new Error('unexpected Kiro hook name');
if (hook.trigger !== 'SessionStart') throw new Error('expected SessionStart trigger');
if (hook.action?.type !== 'command') throw new Error('expected command action');
if (typeof hook.action.command !== 'string') throw new Error('missing hook command');
if (hook.enabled !== true) throw new Error('expected enabled hook');

process.stdout.write(hook.action.command);
NODE
)"

without_index="$(cd "$project_dir" && sh -c "$hook_command")"
if [[ "$without_index" != *"# Using Neo"* ]]; then
  echo "FAIL: Kiro hook omitted using-neo context without .kiro/steering/INDEX.md" >&2
  exit 1
fi
if [[ "$without_index" != *"## Intent table"* ]]; then
  echo "FAIL: Kiro hook emitted incomplete using-neo context" >&2
  exit 1
fi
if [[ "$without_index" == *"Read and follow .kiro/steering/INDEX.md"* ]]; then
  echo "FAIL: Kiro hook requested a missing .kiro/steering/INDEX.md" >&2
  exit 1
fi

mkdir -p "$project_dir/.kiro/steering"
printf '%s\n' 'STEERING_INDEX_SENTINEL' > "$project_dir/.kiro/steering/INDEX.md"
with_index="$(cd "$project_dir" && sh -c "$hook_command")"

if [[ "$with_index" != *"# Using Neo"* ]]; then
  echo "FAIL: Kiro hook omitted using-neo context when INDEX.md exists" >&2
  exit 1
fi
if [[ "$with_index" != *"Read and follow .kiro/steering/INDEX.md"* ]]; then
  echo "FAIL: Kiro hook omitted the INDEX.md instruction" >&2
  exit 1
fi
if [[ "$with_index" != *"STEERING_INDEX_SENTINEL"* ]]; then
  echo "FAIL: Kiro hook omitted INDEX.md content" >&2
  exit 1
fi

HOME="$global_home" "$SCRIPT_DIR/kiro.sh" --global >/dev/null
if [ ! -f "$global_home/.kiro/hooks/neo-session-context.json" ]; then
  echo "FAIL: global install omitted the Kiro hook" >&2
  exit 1
fi

global_project="$tmp_dir/global-project"
mkdir -p "$global_project"
global_output="$(cd "$global_project" && HOME="$global_home" sh -c "$hook_command")"
if [[ "$global_output" != *"# Using Neo"* ]]; then
  echo "FAIL: global Kiro hook did not load ~/.kiro/skills/using-neo/SKILL.md" >&2
  exit 1
fi

echo "PASS: kiro.sh installs a SessionStart hook for using-neo and optional steering"
