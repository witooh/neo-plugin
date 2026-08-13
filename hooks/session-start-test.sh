#!/bin/bash
# session-start-test.sh - Tests for the SessionStart hook JSON payload

set -euo pipefail

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

without_index="$tmp_dir/without-index"
with_index="$tmp_dir/with-index"
mkdir -p "$without_index" "$with_index/.kiro/steering"
printf '%s\n' 'STEERING_INDEX_SENTINEL' >"$with_index/.kiro/steering/INDEX.md"

has_jq=0
if command -v jq >/dev/null 2>&1; then
	has_jq=1
fi

run_hook() {
	local project_dir="$1"
	printf '{"cwd":"%s"}' "$project_dir" |
		CLAUDE_PROJECT_DIR="$project_dir" bash hooks/session-start.sh
}

run_hook "$without_index" >"$tmp_dir/without-index.json"
run_hook "$with_index" >"$tmp_dir/with-index.json"

HAS_JQ="$has_jq" PAYLOAD_DIR="$tmp_dir" node <<'NODE'
const fs = require('fs');
const path = require('path');

const withoutIndex = JSON.parse(
  fs.readFileSync(path.join(process.env.PAYLOAD_DIR, 'without-index.json'), 'utf8'),
);
const withIndex = JSON.parse(
  fs.readFileSync(path.join(process.env.PAYLOAD_DIR, 'with-index.json'), 'utf8'),
);
const hasJq = process.env.HAS_JQ === '1';

if (hasJq) {
  if (withoutIndex.priority !== 'IMPORTANT') {
    throw new Error(`expected IMPORTANT priority, got ${withoutIndex.priority}`);
  }

  if (withoutIndex.additionalContext !== withoutIndex.message) {
    throw new Error('additionalContext must match message');
  }
  if (withoutIndex.hookSpecificOutput?.hookEventName !== 'SessionStart') {
    throw new Error('hookSpecificOutput.hookEventName must be SessionStart');
  }
  if (withoutIndex.hookSpecificOutput?.additionalContext !== withoutIndex.message) {
    throw new Error('hookSpecificOutput.additionalContext must match message');
  }

  if (!withoutIndex.message.includes('neo loaded.')) {
    throw new Error('message is missing startup preface');
  }

  if (!withoutIndex.message.includes('# Using Neo')) {
    throw new Error('message is missing using-neo content');
  }
  if (!withoutIndex.message.includes('## Intent table') || !withoutIndex.message.includes('## Gates')) {
    throw new Error('message is missing the routing contract (intent table + gates)');
  }
  if (withoutIndex.message.includes('STEERING_INDEX_SENTINEL')) {
    throw new Error('message must not include steering when INDEX.md is absent');
  }
  if (withoutIndex.message.includes('Read and follow .kiro/steering/INDEX.md')) {
    throw new Error('message must not mention steering INDEX.md when it is absent');
  }
  if (!withIndex.message.includes('Read and follow .kiro/steering/INDEX.md')) {
    throw new Error('message is missing the steering INDEX.md instruction');
  }
  if (!withIndex.message.includes('STEERING_INDEX_SENTINEL')) {
    throw new Error('message is missing steering INDEX.md content');
  }
} else {
  if (withoutIndex.priority !== 'INFO') {
    throw new Error(`expected INFO priority when jq is missing, got ${withoutIndex.priority}`);
  }

  if (!withoutIndex.message.includes('jq is required')) {
    throw new Error('message is missing jq fallback guidance');
  }
}

console.log('session-start JSON payload OK');
NODE
