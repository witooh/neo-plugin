#!/bin/bash
# neo → Cursor installer. Copies neo's skills, subagents, and session hook into
# a Cursor config directory; shared references are bundled into consumer skills.

set -euo pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
  cat <<'EOF'
neo → Cursor installer

Copies neo's skills, subagents, and hooks into a Cursor configuration directory
so Cursor can auto-discover them.

Cursor layout:
  .cursor/skills/      skills discovered from each <name>/SKILL.md
                       (shared reference checklists ride inside consumer skills)
  .cursor/agents/      custom subagents (markdown + YAML frontmatter)
  .cursor/hooks/       neo's SessionStart hook script
  .cursor/hooks.json   merged hook registration; other hooks are preserved

Usage:
  ./cursor.sh                  install to global   ~/.cursor
  ./cursor.sh --global         install to global   ~/.cursor   (explicit)
  ./cursor.sh --project        install to project  ./.cursor
  ./cursor.sh --project DIR    install to project  DIR/.cursor
  ./cursor.sh -h | --help      show this help

Requires jq. Re-running overwrites only neo-owned entries; other Cursor content
is left intact.
EOF
}

scope="global"
project_dir="."
while [ $# -gt 0 ]; do
  case "$1" in
    --global) scope="global"; shift ;;
    --project)
      scope="project"; shift
      if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then project_dir="$1"; shift; fi
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "cursor.sh: unknown option '$1' (try --help)" >&2; exit 1 ;;
  esac
done

if ! command -v jq >/dev/null 2>&1; then
  echo "cursor.sh: jq is required to merge Cursor hooks.json safely" >&2
  exit 1
fi

if [ "$scope" = "global" ]; then
  cursor_root="$HOME/.cursor"
  hook_command="bash ./hooks/neo-session-context.sh"
else
  if [ ! -d "$project_dir" ]; then
    echo "cursor.sh: project directory '$project_dir' does not exist" >&2
    exit 1
  fi
  cursor_root="$(cd "$project_dir" && pwd)/.cursor"
  hook_command="bash .cursor/hooks/neo-session-context.sh"
fi

hooks_file="$cursor_root/hooks.json"
if [ -f "$hooks_file" ] && ! jq -e '
  .version == 1 and
  (.hooks | type == "object") and
  ((.hooks.sessionStart // []) | type == "array")
' "$hooks_file" >/dev/null; then
  echo "cursor.sh: existing '$hooks_file' is not a valid Cursor hooks version 1 config" >&2
  exit 1
fi

echo "neo → Cursor"
echo "  source: $SCRIPT_DIR"
echo "  target: $cursor_root ($scope)"
echo

mkdir -p "$cursor_root/skills"
skills=0
for dir in "$SCRIPT_DIR"/skills/*/; do
  name="$(basename "$dir")"
  rm -rf "$cursor_root/skills/$name"
  cp -R "$dir" "$cursor_root/skills/$name"
  skills=$((skills + 1))
done
printf '  %-11s %d → %s/\n' "skills:" "$skills" "$cursor_root/skills"

shared=0
copies=0
for ref in "$SCRIPT_DIR"/references/*.md; do
  rname="$(basename "$ref")"
  used=0
  for skill_dir in "$cursor_root"/skills/*/; do
    if grep -qF "references/$rname" "$skill_dir/SKILL.md" 2>/dev/null; then
      mkdir -p "$skill_dir/references"
      cp "$ref" "$skill_dir/references/"
      copies=$((copies + 1))
      used=1
    fi
  done
  shared=$((shared + used))
done
printf '  %-11s %d → %d copies inside consumer skills\n' "references:" "$shared" "$copies"

mkdir -p "$cursor_root/agents"
agents=0
for file in "$SCRIPT_DIR"/agents/*.md; do
  cp "$file" "$cursor_root/agents/"
  agents=$((agents + 1))
done
printf '  %-11s %d → %s/\n' "subagents:" "$agents" "$cursor_root/agents"

mkdir -p "$cursor_root/hooks"
cp "$SCRIPT_DIR/hooks/cursor/neo-session-context.sh" "$cursor_root/hooks/"

if [ ! -f "$hooks_file" ]; then
  printf '%s\n' '{"version":1,"hooks":{}}' > "$hooks_file"
fi

tmp_file="$(mktemp "$cursor_root/.hooks.json.XXXXXX")"
trap 'rm -f "$tmp_file"' EXIT
cp -p "$hooks_file" "$tmp_file"
jq --arg command "$hook_command" '
  .hooks.sessionStart = (
    (.hooks.sessionStart // [])
    | map(select(
        .command != "bash .cursor/hooks/neo-session-context.sh" and
        .command != "bash ./hooks/neo-session-context.sh"
      ))
    + [{command: $command, timeout: 5}]
  )
' "$hooks_file" > "$tmp_file"
mv "$tmp_file" "$hooks_file"
trap - EXIT
printf '  %-11s %d → %s\n' "hooks:" 1 "$hooks_file"

echo
echo "Done. Cursor loads neo skills and subagents on demand; using-neo and optional steering load at session start."
