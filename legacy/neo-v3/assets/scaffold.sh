#!/usr/bin/env bash
# ============================================================================
# scaffold.sh — stamp the Design Docs design-system into a project's docs/design/.
#
# Usage:  bash scaffold.sh <dest-design-dir>      e.g.  bash scaffold.sh ./docs/design
#
# Idempotent — safe to run before every HTML gen:
#   - framework files (styles.css, app.js, components.js, components.html) are ALWAYS
#     refreshed to the bundled canonical version.
#   - nav.js is created ONCE and NEVER overwritten (it holds this project's
#     usecase registration + brand — clobbering it would wipe navigation).
#
# SRC resolves to this script's own directory = the bundled assets dir, which at
# runtime is the plugin cache path (…/cache/neo/neo-dev-toolkit/<ver>/skills/neo/assets).
# ============================================================================
set -euo pipefail

DEST="${1:?usage: scaffold.sh <dest-design-dir>}"
SRC="$(cd "$(dirname "$0")" && pwd)"

mkdir -p "$DEST/assets/css" "$DEST/assets/js"

# --- framework files: always refresh to bundled version ---
cp "$SRC/css/styles.css"  "$DEST/assets/css/styles.css"
cp "$SRC/js/app.js"       "$DEST/assets/js/app.js"
cp "$SRC/js/components.js" "$DEST/assets/js/components.js"
cp "$SRC/components.html" "$DEST/components.html"
echo "refreshed: assets/css/styles.css · assets/js/app.js · assets/js/components.js · components.html"

# --- nav.js: create once, never clobber (holds usecase registration + brand) ---
if [ -f "$DEST/assets/js/nav.js" ]; then
  echo "kept:      assets/js/nav.js (exists — not overwritten)"
else
  cp "$SRC/js/nav.js" "$DEST/assets/js/nav.js"
  echo "created:   assets/js/nav.js (set DOCS_BRAND.sub + add this project's usecase groups)"
fi

echo "done: design-system stamped into $DEST"
