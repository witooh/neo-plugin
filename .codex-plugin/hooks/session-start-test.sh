#!/bin/bash
# session-start-test.sh - Verifies the Codex SessionStart hook payload

set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
plugin_root="$(cd "$script_dir/../.." && pwd)"
manifest_path="$plugin_root/.codex-plugin/plugin.json"

hooks_path="$(MANIFEST_PATH="$manifest_path" node <<'NODE'
const fs = require('fs');
const manifest = JSON.parse(fs.readFileSync(process.env.MANIFEST_PATH, 'utf8'));

if (manifest.hooks !== './.codex-plugin/hooks/hooks.json') {
  throw new Error('plugin manifest must select the Codex-specific hooks file');
}

process.stdout.write(manifest.hooks);
NODE
)"

hooks_path="$plugin_root/${hooks_path#./}"
command="$(HOOKS_PATH="$hooks_path" node <<'NODE'
const fs = require('fs');
const config = JSON.parse(fs.readFileSync(process.env.HOOKS_PATH, 'utf8'));
const commandHook = config.hooks?.SessionStart?.[0]?.hooks?.find(
  (hook) => hook.type === 'command',
);

if (typeof commandHook?.command !== 'string') {
  throw new Error('Codex hooks file must define a SessionStart command');
}

process.stdout.write(commandHook.command);
NODE
)"

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

without_index="$tmp_dir/without-index"
with_index="$tmp_dir/with-index"
mkdir -p "$without_index" "$with_index/.kiro/steering"
printf '%s\n' 'STEERING_INDEX_SENTINEL' > "$with_index/.kiro/steering/INDEX.md"

run_hook() {
  local project_dir="$1"
  printf '{"cwd":"%s"}' "$project_dir" |
    PLUGIN_ROOT="$plugin_root" bash -c "$command"
}

run_hook "$without_index" > "$tmp_dir/without-index.json"
run_hook "$with_index" > "$tmp_dir/with-index.json"

PAYLOAD_DIR="$tmp_dir" node <<'NODE'
const fs = require('fs');
const path = require('path');

const withoutIndex = JSON.parse(
  fs.readFileSync(path.join(process.env.PAYLOAD_DIR, 'without-index.json'), 'utf8'),
);
const withIndex = JSON.parse(
  fs.readFileSync(path.join(process.env.PAYLOAD_DIR, 'with-index.json'), 'utf8'),
);
const output = withoutIndex.hookSpecificOutput;
const outputWithIndex = withIndex.hookSpecificOutput;

if (output?.hookEventName !== 'SessionStart') {
  throw new Error('payload is missing the Codex SessionStart event name');
}
if (!output.additionalContext?.includes('neo loaded.')) {
  throw new Error('payload is missing the startup preface');
}
if (!output.additionalContext.includes('# Using Neo')) {
  throw new Error('payload is missing using-neo content');
}
if (!output.additionalContext.includes('## Single Entry Point')) {
  throw new Error('payload is missing the single-entry routing contract');
}
if ('priority' in withoutIndex || 'message' in withoutIndex) {
  throw new Error('payload still contains legacy priority/message fields');
}
if (output.additionalContext.includes('STEERING_INDEX_SENTINEL')) {
  throw new Error('payload must not include steering when INDEX.md is absent');
}
if (output.additionalContext.includes('Read and follow .kiro/steering/INDEX.md')) {
  throw new Error('payload must not mention steering INDEX.md when it is absent');
}
if (!outputWithIndex?.additionalContext?.includes('Read and follow .kiro/steering/INDEX.md')) {
  throw new Error('payload is missing the steering INDEX.md instruction');
}
if (!outputWithIndex.additionalContext.includes('STEERING_INDEX_SENTINEL')) {
  throw new Error('payload is missing steering INDEX.md content');
}

console.log('Codex SessionStart payload OK');
NODE
