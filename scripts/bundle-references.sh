#!/bin/bash
# Fan each shared references/<file>.md into every skills/<name>/ whose SKILL.md
# cites it, so the relative `references/<file>.md` pointer resolves inside the
# skill's own dir and each skill is self-contained (portable to Kiro, pi, or any
# installer that copies skill dirs as-is).
#
# The top-level references/ dir stays the source of truth (upstream-synced; also
# cited by agents/ and command files). The per-skill copies are GENERATED — edit
# the top-level file and re-run this script; sync-upstream re-runs it on --apply.
#
# Idempotent: overwrites copies that drifted from their source and prunes copies
# whose SKILL.md citation is gone. A skill-own references file (one that is not
# byte-identical to a same-named shared source) is never touched.

set -euo pipefail
shopt -s nullglob

ROOT="$(cd "$(dirname "$0")/.." && pwd)"

bundled=0
pruned=0

for ref in "$ROOT"/references/*.md; do
  rname="$(basename "$ref")"
  while IFS= read -r skillmd; do
    skdir="${skillmd%SKILL.md}"
    if [ ! -f "${skdir}references/$rname" ] || ! cmp -s "$ref" "${skdir}references/$rname"; then
      mkdir -p "${skdir}references"
      cp "$ref" "${skdir}references/$rname"
      echo "  bundle  ${skdir#"$ROOT"/}references/$rname"
      bundled=$((bundled + 1))
    fi
  done < <(grep -lF "references/$rname" "$ROOT"/skills/*/SKILL.md || true)
done

# prune: a bundled copy whose skill no longer cites it
for copy in "$ROOT"/skills/*/references/*.md; do
  rname="$(basename "$copy")"
  src="$ROOT/references/$rname"
  skdir="$(dirname "$(dirname "$copy")")"
  [ -f "$src" ] || continue                                  # not a shared name
  cmp -s "$copy" "$src" || continue                          # skill-own file, leave it
  grep -qF "references/$rname" "$skdir/SKILL.md" 2>/dev/null && continue
  rm "$copy"
  rmdir "$skdir/references" 2>/dev/null || true
  echo "  prune   ${copy#"$ROOT"/}"
  pruned=$((pruned + 1))
done

echo "bundle-references: $bundled bundled, $pruned pruned"
