#!/bin/bash
# session-start-test.sh - Verifies the Codex SessionStart hook payload

set -euo pipefail

script_dir="$(cd "$(dirname "$0")" && pwd)"
plugin_root="$(cd "$script_dir/../.." && pwd)"
manifest_path="$plugin_root/.codex-plugin/plugin.json"

hooks_path="$(MANIFEST_PATH="$manifest_path" node <<'NODE'
const fs = require('fs');
const manifest = JSON.parse(fs.readFileSync(process.env.MANIFEST_PATH, 'utf8'));

if (typeof manifest.hooks !== 'string') {
  throw new Error('plugin manifest must select a Codex-specific hooks file');
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

tmp_payload="$(mktemp)"
trap 'rm -f "$tmp_payload"' EXIT

PLUGIN_ROOT="$plugin_root" bash -c "$command" > "$tmp_payload"

PAYLOAD_PATH="$tmp_payload" node <<'NODE'
const fs = require('fs');
const payload = JSON.parse(fs.readFileSync(process.env.PAYLOAD_PATH, 'utf8'));
const output = payload.hookSpecificOutput;

if (output?.hookEventName !== 'SessionStart') {
  throw new Error('payload is missing the Codex SessionStart event name');
}
if (!output.additionalContext?.includes('neo loaded.')) {
  throw new Error('payload is missing the startup preface');
}
if (!output.additionalContext.includes('# Using Neo')) {
  throw new Error('payload is missing using-neo content');
}
if ('priority' in payload || 'message' in payload) {
  throw new Error('payload still contains legacy priority/message fields');
}

console.log('Codex SessionStart payload OK');
NODE
