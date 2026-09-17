#!/bin/bash
# neo → Cursor installer. Copies neo's skills into a Cursor config directory.

set -euo pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
  cat <<'EOF'
neo → Cursor installer

Copies neo's skills into a Cursor configuration directory.

  .cursor/skills/      skills discovered from each <name>/SKILL.md

Usage:
  ./cursor.sh                  install to global   ~/.cursor
  ./cursor.sh --global         install to global   ~/.cursor   (explicit)
  ./cursor.sh --project        install to project  ./.cursor
  ./cursor.sh --project DIR    install to project  DIR/.cursor
  ./cursor.sh -h | --help      show this help

Re-running overwrites only neo-owned skill directories; other Cursor content
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

if [ "$scope" = "global" ]; then
  cursor_root="$HOME/.cursor"
else
  if [ ! -d "$project_dir" ]; then
    echo "cursor.sh: project directory '$project_dir' does not exist" >&2
    exit 1
  fi
  cursor_root="$(cd "$project_dir" && pwd)/.cursor"
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

echo
echo "Done. Cursor loads neo skills on demand as slash commands."
