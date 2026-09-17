#!/bin/bash
# neo → Kiro installer. Copies neo's skills into a Kiro config directory.
# Run with --help for the layout.

set -euo pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
  cat <<'EOF'
neo → Kiro installer

Copies neo's skills into a Kiro configuration directory.

Kiro layout (https://kiro.dev/docs/skills/):
  .kiro/skills/      skills — each is a /<name> slash command

Usage:
  ./kiro.sh                  install to global   ~/.kiro
  ./kiro.sh --global         install to global   ~/.kiro   (explicit)
  ./kiro.sh --project        install to project  ./.kiro
  ./kiro.sh --project DIR    install to project  DIR/.kiro
  ./kiro.sh -h | --help      show this help

Re-running overwrites only neo-owned skill directories; other Kiro content
is left intact.
EOF
}

# ---- parse args ----
scope="global"
project_dir="."
while [ $# -gt 0 ]; do
  case "$1" in
    --global) scope="global"; shift ;;
    --project)
      scope="project"; shift
      # optional directory argument (anything that is not another flag)
      if [ $# -gt 0 ] && [ "${1#-}" = "$1" ]; then project_dir="$1"; shift; fi
      ;;
    -h|--help) usage; exit 0 ;;
    *) echo "kiro.sh: unknown option '$1' (try --help)" >&2; exit 1 ;;
  esac
done

# ---- resolve destination ----
if [ "$scope" = "global" ]; then
  kiro_root="$HOME/.kiro"
else
  if [ ! -d "$project_dir" ]; then
    echo "kiro.sh: project directory '$project_dir' does not exist" >&2
    exit 1
  fi
  kiro_root="$(cd "$project_dir" && pwd)/.kiro"
fi

echo "neo → Kiro"
echo "  source: $SCRIPT_DIR"
echo "  target: $kiro_root ($scope)"
echo

# skills: each skills/<name>/ -> .kiro/skills/<name>/  (owns its subdir, so rm+copy
# replaces cleanly and prunes files deleted upstream)
mkdir -p "$kiro_root/skills"
skills=0
for dir in "$SCRIPT_DIR"/skills/*/; do
  name="$(basename "$dir")"
  rm -rf "$kiro_root/skills/$name"
  cp -R "$dir" "$kiro_root/skills/$name"
  skills=$((skills + 1))
done
printf '  %-11s %d → %s/  %s\n' "skills:" "$skills" "$kiro_root/skills" "(as /<skill-name>)"

echo
echo "Done. In Kiro, skills appear as /<name> slash commands."
