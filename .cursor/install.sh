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
  export NPM_CONFIG_PREFIX="$HOME/.npm-global"
  mkdir -p "$NPM_CONFIG_PREFIX/bin"
  npm install -g "$pkg"
  path_line='export PATH="$HOME/.npm-global/bin:$PATH"'
  grep -qxF "$path_line" "$HOME/.bashrc" 2>/dev/null || echo "$path_line" >>"$HOME/.bashrc"
  export PATH="$HOME/.npm-global/bin:$PATH"
fi

echo "install.sh: installed $(claude --version 2>/dev/null | head -1)"
