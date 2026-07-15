#!/bin/bash
# Codex SessionStart hook
# Injects the using-neo single-entry router into every new session

script_dir="$(cd "$(dirname "$0")" && pwd)"
plugin_root="$(cd "$script_dir/../.." && pwd)"
meta_skill="$plugin_root/skills/using-neo/SKILL.md"

if ! command -v jq >/dev/null 2>&1; then
  echo "neo: jq is required for using-neo router injection but was not found on PATH. Skills remain available individually."
  exit 0
fi

if [ -f "$meta_skill" ]; then
  content=$(cat "$meta_skill")
  project_dir=""
  if [ ! -t 0 ]; then
    event_input=$(cat)
    project_dir=$(printf '%s' "$event_input" | jq -r '.cwd // empty' 2>/dev/null || true)
  fi
  project_dir="${project_dir:-$PWD}"

  context="neo loaded. Route every task through the using-neo single entry point.

$content"
  steering_index="$project_dir/.kiro/steering/INDEX.md"
  if [ -f "$steering_index" ]; then
    context="$context

Project steering is available. Read and follow .kiro/steering/INDEX.md now, including every file it marks with inclusion: always.

$(cat "$steering_index")"
  fi

  jq -cn \
    --arg context "$context" \
    '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $context}}'
else
  jq -cn \
    --arg message "neo: using-neo router not found. Skills may still be available individually." \
    '{systemMessage: $message}'
fi
