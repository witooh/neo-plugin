#!/usr/bin/env bash
# Cloud Agent install for the neo skills pack.
#
# neo has no project runtime and no npm dependencies (no lockfile). The only
# tool the dev/CI flow needs beyond stock Node is the Claude Code CLI, used by
# `claude plugin validate .` (the plugin-structure gate in CI). Every other
# check is a plain `node scripts/validate-*.js` invocation.
#
# Must stay idempotent: it can run again on a warm/cached disk.
set -euo pipefail

pkg="@anthropic-ai/claude-code"

if command -v claude >/dev/null 2>&1; then
  echo "install.sh: claude already installed ($(claude --version 2>/dev/null | head -1))"
  exit 0
fi

# Prefer a root global install so `claude` lands on the default PATH for every
# shell. Fall back to a user-local prefix when passwordless sudo is unavailable.
if sudo -n true 2>/dev/null; then
  sudo env "PATH=$PATH" npm install -g "$pkg"
else
  prefix="$HOME/.npm-global"
  mkdir -p "$prefix/bin"
  npm install -g --prefix "$prefix" "$pkg"
  # Put the user-local bin on PATH for the login and interactive shells the
  # agent uses, without duplicating the line on re-runs.
  path_line='export PATH="$HOME/.npm-global/bin:$PATH"'
  for rc in "$HOME/.bashrc" "$HOME/.profile" "$HOME/.bash_profile"; do
    touch "$rc"
    grep -qxF "$path_line" "$rc" 2>/dev/null || echo "$path_line" >>"$rc"
  done
  export PATH="$prefix/bin:$PATH"
fi

echo "install.sh: installed $(claude --version 2>/dev/null | head -1)"
