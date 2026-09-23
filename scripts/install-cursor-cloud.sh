#!/bin/bash
# Install neo skills onto a Cursor Cloud Agent VM so the Build snapshot has them.
#
# Put this in environment.json "install", not "start". "install" runs while
# Cursor creates a Build and the resulting disk is snapshotted. "start" runs
# on every agent boot and is for processes, not skill files.
#
# Do not curl | bash. Pin NEO_REF to a tag when this file is not already inside
# a neo-plugin checkout.
#
# From a neo-plugin checkout (installs this tree; NEO_REF is ignored):
#   ./scripts/install-cursor-cloud.sh
#
# From a vendored copy of this file:
#   NEO_REF=v5.0.1 ./scripts/install-cursor-cloud.sh

set -euo pipefail

NEO_URL="${NEO_URL:-https://github.com/witooh/neo-plugin.git}"

# Names this pack used to install before ~/.cursor/.neo-skills recorded ownership.
# A later removal is pruned from that manifest. Other skill directories stay.
RETIRED_SKILLS=(
  audit-log
  code-review
  codebase-design
  diagnosing-bugs
  domain-modeling
  grilling
  prototype
  research
  resolving-merge-conflicts
  tdd
  using-neo
)

usage() {
  cat <<'EOF'
Install neo skills into ~/.cursor for a Cursor Cloud Agent Build snapshot.

  ./scripts/install-cursor-cloud.sh
      Run from a neo-plugin checkout. Installs that tree. NEO_REF is ignored.

  NEO_REF=<tag> ./scripts/install-cursor-cloud.sh
      Clone that tag or branch, then install its skills/. Required when this
      file is not inside a neo-plugin checkout.

  NEO_URL=<git url>   override the clone URL (default: the public GitHub repo)

Writes ~/.cursor/skills only. The service working tree is not modified.
EOF
}

if [ "${1:-}" = "-h" ] || [ "${1:-}" = "--help" ]; then
  usage
  exit 0
fi
if [ "$#" -gt 0 ]; then
  echo "install-cursor-cloud.sh: unknown argument '$1' (try --help)" >&2
  exit 1
fi

valid_ref() {
  case "$1" in
    ""|-*|*..*|*[[:space:]]*|*'~'*|*'^'*|*'?'*|*'['*|*'@{'*) return 1 ;;
  esac
  case "$1" in
    *[!A-Za-z0-9._/-]*) return 1 ;;
  esac
  return 0
}

safe_name() {
  case "$1" in
    ""|.*|*/*|*..*) return 1 ;;
  esac
  return 0
}

skill_is_current() {
  local name="$1"
  local current
  if [ "${#current_skills[@]}" -eq 0 ]; then
    return 1
  fi
  for current in "${current_skills[@]}"; do
    if [ "$current" = "$name" ]; then
      return 0
    fi
  done
  return 1
}

install_pack() {
  local pack="$1"
  local root="$HOME/.cursor"
  local dest="$root/skills"
  local manifest="$root/.neo-skills"
  local dir name manifest_tmp
  mkdir -p "$dest"

  current_skills=()
  for dir in "$pack"/skills/*/; do
    if [ ! -f "${dir}SKILL.md" ]; then
      continue
    fi
    name="$(basename "$dir")"
    if safe_name "$name"; then
      current_skills+=("$name")
    fi
  done
  if [ "${#current_skills[@]}" -eq 0 ]; then
    echo "install-cursor-cloud.sh: $pack/skills has no SKILL.md" >&2
    exit 1
  fi

  prune_one() {
    local stale="$1"
    safe_name "$stale" || return 0
    if skill_is_current "$stale"; then
      return 0
    fi
    if [ -d "$dest/$stale" ]; then
      rm -rf "$dest/$stale"
    fi
  }

  for name in "${RETIRED_SKILLS[@]}"; do
    prune_one "$name"
  done
  if [ -f "$manifest" ]; then
    while IFS= read -r name || [ -n "$name" ]; do
      case "$name" in
        ""|\#*) continue ;;
      esac
      prune_one "$name"
    done < "$manifest"
  fi

  for dir in "$pack"/skills/*/; do
    if [ ! -f "${dir}SKILL.md" ]; then
      continue
    fi
    name="$(basename "$dir")"
    safe_name "$name" || continue
    rm -rf "$dest/$name"
    cp -R "$dir" "$dest/$name"
  done

  manifest_tmp="$(mktemp)"
  printf '%s\n' "${current_skills[@]}" | sort > "$manifest_tmp"
  mv "$manifest_tmp" "$manifest"
  echo "install-cursor-cloud.sh: ${#current_skills[@]} skills → $dest"
}

script_dir="$(cd "$(dirname "$0")" && pwd)"
pack=""
if [ -f "$script_dir/../.cursor-plugin/plugin.json" ] && [ -d "$script_dir/../skills" ]; then
  pack="$(cd "$script_dir/.." && pwd)"
fi

cleanup() {
  if [ -n "${clone_dir:-}" ]; then
    rm -rf "$clone_dir"
  fi
}
trap cleanup EXIT

if [ -n "$pack" ]; then
  echo "install-cursor-cloud.sh: installing checkout $pack"
  install_pack "$pack"
else
  ref="${NEO_REF:-}"
  if ! valid_ref "$ref"; then
    echo "install-cursor-cloud.sh: NEO_REF must be a tag or branch name (example: NEO_REF=v5.0.1)" >&2
    exit 1
  fi
  if ! command -v git >/dev/null 2>&1; then
    echo "install-cursor-cloud.sh: git is required to clone $ref" >&2
    exit 1
  fi
  clone_dir="$(mktemp -d)"
  echo "install-cursor-cloud.sh: cloning $ref"
  GIT_TERMINAL_PROMPT=0 git clone --depth 1 --branch "$ref" "$NEO_URL" "$clone_dir"
  install_pack "$clone_dir"
fi

if [ ! -f "$HOME/.cursor/skills/markitdown/SKILL.md" ]; then
  echo "install-cursor-cloud.sh: install finished but ~/.cursor/skills/markitdown/SKILL.md is missing" >&2
  exit 1
fi
if [ -e "$HOME/.cursor/skills/using-neo" ]; then
  echo "install-cursor-cloud.sh: retired skill using-neo is still installed" >&2
  exit 1
fi

echo "install-cursor-cloud.sh: neo skills are in $HOME/.cursor/skills"
