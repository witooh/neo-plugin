#!/bin/bash
# Cursor SessionStart hook: injects using-neo and optional project steering.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CURSOR_ROOT="$(dirname "$SCRIPT_DIR")"

if ! command -v jq >/dev/null 2>&1; then
  printf '%s\n' '{"additional_context":"neo: jq is required for using-neo router injection but was not found on PATH. Skills remain available individually."}'
  exit 0
fi

event_input="$(cat)"
project_dir="$(printf '%s' "$event_input" | jq -r '.workspace_roots[0] // empty' 2>/dev/null || true)"
router=""

if [ -n "$project_dir" ] && [ -f "$project_dir/.cursor/skills/using-neo/SKILL.md" ]; then
  router="$project_dir/.cursor/skills/using-neo/SKILL.md"
elif [ -f "$CURSOR_ROOT/skills/using-neo/SKILL.md" ]; then
  router="$CURSOR_ROOT/skills/using-neo/SKILL.md"
fi

if [ -n "$router" ]; then
  context="neo loaded. Route every task through the using-neo single entry point.

$(cat "$router")"

  steering_index="$project_dir/.kiro/steering/INDEX.md"
  if [ -n "$project_dir" ] && [ -f "$steering_index" ]; then
    context="$context

Project steering is available. Read and follow .kiro/steering/INDEX.md now, including every file it marks with inclusion: always.

$(cat "$steering_index")"
  fi
else
  context="neo: using-neo router not found. Skills may still be available individually."
fi

jq -cn --arg additional_context "$context" '{additional_context: $additional_context}'
