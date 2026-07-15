#!/bin/bash
# neo → Kiro installer. Copies neo's skills, agents, and hooks into a Kiro
# config directory; shared reference checklists are bundled into the skills
# that cite them. Run with --help for the layout.

set -euo pipefail
shopt -s nullglob

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

usage() {
  cat <<'EOF'
neo → Kiro installer

Copies neo's skills, agents, and hooks into a Kiro configuration directory
so Kiro can auto-discover them.

Kiro layout (https://kiro.dev/docs/skills/):
  .kiro/skills/      skills — each is a /<name> slash command
                     (shared reference checklists ride inside the skills that cite them)
  .kiro/agents/      custom agent personas (markdown + YAML frontmatter)
  .kiro/hooks/       SessionStart hook — loads using-neo and optional steering/INDEX.md
                     (Kiro IDE 1.0 / CLI v3)

Usage:
  ./kiro.sh                  install to global   ~/.kiro
  ./kiro.sh --global         install to global   ~/.kiro   (explicit)
  ./kiro.sh --project        install to project  ./.kiro
  ./kiro.sh --project DIR    install to project  DIR/.kiro
  ./kiro.sh -h | --help      show this help

Re-running overwrites only neo-owned entries; other Kiro content is left intact.
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

# references: bundle each shared references/<file>.md into every skill whose SKILL.md
# cites it, so the relative `references/<file>.md` pointer resolves inside the skill's
# own dir (Kiro's self-contained skill model — no top-level references dir needed).
shared=0
copies=0
for ref in "$SCRIPT_DIR"/references/*.md; do
  rname="$(basename "$ref")"
  used=0
  for skdir in "$kiro_root"/skills/*/; do
    if grep -qF "references/$rname" "$skdir/SKILL.md" 2>/dev/null; then
      mkdir -p "$skdir/references"
      cp "$ref" "$skdir/references/"
      copies=$((copies + 1))
      used=1
    fi
  done
  shared=$((shared + used))
done
printf '  %-11s %d → %d copies inside consumer skills\n' "references:" "$shared" "$copies"

# agents: agents/*.md -> .kiro/agents/  (flat dir shared with the user's own agents,
# so overwrite same-named files only, never prune)
mkdir -p "$kiro_root/agents"
agents=0
for file in "$SCRIPT_DIR"/agents/*.md; do
  cp "$file" "$kiro_root/agents/"
  agents=$((agents + 1))
done
printf '  %-11s %d → %s/\n' "agents:" "$agents" "$kiro_root/agents"

# hooks: overwrite only neo's named hook; preserve every other user hook.
mkdir -p "$kiro_root/hooks"
cp "$SCRIPT_DIR/hooks/kiro/neo-session-context.json" "$kiro_root/hooks/"
printf '  %-11s %d → %s/\n' "hooks:" 1 "$kiro_root/hooks"

echo
echo "Done. In Kiro, skills appear as /<name> slash commands; using-neo and optional steering load at session start."
