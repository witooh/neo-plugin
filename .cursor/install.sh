#!/usr/bin/env bash
# Cloud Agent install for the neo skills pack.
#
# neo has no project runtime and no npm dependencies (no lockfile). The only
# tool the dev/CI flow needs beyond stock Node is the Claude Code CLI, used by
# `claude plugin validate .` (the plugin-structure gate in CI). Every other
# check is a plain `node scripts/validate-*.js` invocation.
#
# The CLI is installed into a user-local npm prefix under $HOME on purpose:
# only $HOME and the workspace survive an environment-build snapshot, so a
# root/global (`sudo npm i -g` into /usr) install would be dropped from the
# baked image and `claude` would be missing on a fresh Cloud Agent boot.
#
# Must stay idempotent: it can run again on a warm/cached disk.
set -euo pipefail

pkg="@anthropic-ai/claude-code"
prefix="$HOME/.npm-global"

# Make the user-local bin visible now and for the agent's future shells.
export PATH="$prefix/bin:$PATH"
path_line='export PATH="$HOME/.npm-global/bin:$PATH"'
for rc in "$HOME/.bashrc" "$HOME/.profile" "$HOME/.zshrc"; do
  [ -e "$rc" ] || { [ "$rc" = "$HOME/.zshrc" ] && continue; touch "$rc"; }
  grep -qxF "$path_line" "$rc" 2>/dev/null || echo "$path_line" >>"$rc"
done

if command -v claude >/dev/null 2>&1; then
  echo "install.sh: claude already installed ($(claude --version 2>/dev/null | head -1))"
  exit 0
fi

mkdir -p "$prefix/bin"
npm install -g --prefix "$prefix" "$pkg"

echo "install.sh: installed $(claude --version 2>/dev/null | head -1)"
