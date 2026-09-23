#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$SCRIPT_DIR/.." && pwd)"
installer="$repo_root/scripts/install-cursor-cloud.sh"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

home="$tmp_dir/home"
project="$tmp_dir/project"
mkdir -p "$home/.cursor/skills/using-neo" "$home/.cursor/skills/keep-mine" "$project"
printf '%s\n' '# stale' > "$home/.cursor/skills/using-neo/SKILL.md"
printf '%s\n' '# mine' > "$home/.cursor/skills/keep-mine/SKILL.md"
(
  cd "$project"
  HOME="$home" "$installer" >/dev/null
)

if [ -d "$project/.cursor" ]; then
  echo "FAIL: cloud install wrote .cursor into the working tree" >&2
  exit 1
fi
if [ ! -f "$home/.cursor/skills/markitdown/SKILL.md" ]; then
  echo "FAIL: cloud install omitted markitdown" >&2
  exit 1
fi
if [ ! -f "$home/.cursor/skills/advice-mode/SKILL.md" ]; then
  echo "FAIL: cloud install omitted advice-mode" >&2
  exit 1
fi
if [ -e "$home/.cursor/skills/using-neo" ]; then
  echo "FAIL: cloud install left using-neo" >&2
  exit 1
fi
if [ ! -f "$home/.cursor/skills/keep-mine/SKILL.md" ]; then
  echo "FAIL: cloud install removed a user-owned skill" >&2
  exit 1
fi
if ! grep -qx 'markitdown' "$home/.cursor/.neo-skills"; then
  echo "FAIL: .neo-skills does not record markitdown" >&2
  exit 1
fi
if grep -qx 'using-neo' "$home/.cursor/.neo-skills" || grep -qx 'keep-mine' "$home/.cursor/.neo-skills"; then
  echo "FAIL: .neo-skills recorded a skill this installer does not own" >&2
  exit 1
fi
if [ -e "$home/.cursor/agents" ]; then
  echo "FAIL: cloud install created agents/" >&2
  exit 1
fi

HOME="$home" "$installer" >/dev/null
if [ ! -f "$home/.cursor/skills/http-audit-log/SKILL.md" ]; then
  echo "FAIL: second run dropped http-audit-log" >&2
  exit 1
fi

standalone="$tmp_dir/standalone.sh"
cp "$installer" "$standalone"
chmod +x "$standalone"
if HOME="$tmp_dir/no-ref-home" "$standalone" >/dev/null 2>"$tmp_dir/no-ref.err"; then
  echo "FAIL: standalone install ran without NEO_REF" >&2
  exit 1
fi
if [ -d "$tmp_dir/no-ref-home/.cursor" ]; then
  echo "FAIL: missing NEO_REF still wrote ~/.cursor" >&2
  exit 1
fi
if ! grep -qF 'NEO_REF must be a tag or branch name' "$tmp_dir/no-ref.err"; then
  echo "FAIL: missing NEO_REF did not explain the pin" >&2
  exit 1
fi

for bad in 'v1;id' 'foo bar' '../v5' '-rf' 'v5.0.1~1'; do
  if NEO_REF="$bad" HOME="$tmp_dir/bad-home" "$standalone" >/dev/null 2>>"$tmp_dir/bad.err"; then
    echo "FAIL: accepted unsafe NEO_REF '$bad'" >&2
    exit 1
  fi
done
if [ -d "$tmp_dir/bad-home/.cursor" ]; then
  echo "FAIL: unsafe NEO_REF still wrote ~/.cursor" >&2
  exit 1
fi
if grep -qF 'cloning' "$tmp_dir/bad.err"; then
  echo "FAIL: unsafe NEO_REF reached git clone" >&2
  exit 1
fi

echo "PASS: install-cursor-cloud.sh installs the checkout globally and refuses an unpinned standalone run"
