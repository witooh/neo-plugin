#!/bin/bash
# neo session start hook
# Injects the using-neo single-entry router into every new session

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SKILLS_DIR="$(dirname "$SCRIPT_DIR")/skills"
META_SKILL="$SKILLS_DIR/using-neo/SKILL.md"

if ! command -v jq >/dev/null 2>&1; then
  echo '{"priority": "INFO", "message": "neo: jq is required for the session-start hook but was not found on PATH. Install jq (e.g. `brew install jq` or `apt-get install jq`) to enable using-neo router injection. Skills remain available individually.", "additionalContext": "neo: jq is required for using-neo router injection but was not found on PATH. Skills remain available individually.", "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "neo: jq is required for using-neo router injection but was not found on PATH. Skills remain available individually."}}'
  exit 0
fi

if [ -f "$META_SKILL" ]; then
  CONTENT=$(cat "$META_SKILL")
  PROJECT_DIR="${GROK_WORKSPACE_ROOT:-${CLAUDE_PROJECT_DIR:-}}"
  if [ -z "$PROJECT_DIR" ] && [ ! -t 0 ]; then
    EVENT_INPUT=$(cat)
    PROJECT_DIR=$(printf '%s' "$EVENT_INPUT" | jq -r '.cwd // .workspaceRoot // empty' 2>/dev/null || true)
  fi
  PROJECT_DIR="${PROJECT_DIR:-$PWD}"

  MESSAGE="neo loaded. Route every task through the using-neo single entry point.

$CONTENT"
  STEERING_INDEX="$PROJECT_DIR/.kiro/steering/INDEX.md"
  if [ -f "$STEERING_INDEX" ]; then
    MESSAGE="$MESSAGE

Project steering is available. Read and follow .kiro/steering/INDEX.md now, including every file it marks with inclusion: always.

$(cat "$STEERING_INDEX")"
  fi

  # Claude reads priority/message. Grok documents SessionStart stdout as
  # ignored; still emit additionalContext in both shapes so a runner that
  # honors either format injects the same router body.
  jq -cn \
    --arg message "$MESSAGE" \
    '{
      priority: "IMPORTANT",
      message: $message,
      additionalContext: $message,
      hookSpecificOutput: {
        hookEventName: "SessionStart",
        additionalContext: $message
      }
    }'
else
  echo '{"priority": "INFO", "message": "neo: using-neo router not found. Skills may still be available individually.", "additionalContext": "neo: using-neo router not found. Skills may still be available individually.", "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "neo: using-neo router not found. Skills may still be available individually."}}'
fi
