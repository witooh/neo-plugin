#!/bin/bash
# Codex SessionStart hook
# Injects the using-neo meta-skill into every new session

script_dir="$(cd "$(dirname "$0")" && pwd)"
plugin_root="$(cd "$script_dir/../.." && pwd)"
meta_skill="$plugin_root/skills/using-neo/SKILL.md"

if ! command -v jq >/dev/null 2>&1; then
  echo "neo: jq is required for meta-skill injection but was not found on PATH. Skills remain available individually."
  exit 0
fi

if [ -f "$meta_skill" ]; then
  content=$(cat "$meta_skill")
  jq -cn \
    --arg context "neo loaded. Use the skill discovery flowchart to find the right skill for your task.

$content" \
    '{hookSpecificOutput: {hookEventName: "SessionStart", additionalContext: $context}}'
else
  jq -cn \
    --arg message "neo: using-neo meta-skill not found. Skills may still be available individually." \
    '{systemMessage: $message}'
fi
