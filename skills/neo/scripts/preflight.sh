#!/usr/bin/env bash
# Checks that this machine and workspace can run card delivery.
# Usage: bash preflight.sh [workspace-dir]
# Prints MISSING lines for what must be fixed and ends with READY or NOT_READY.
set -u

root=${1:-$PWD}
problems=0

missing() {
  echo "MISSING $1"
  problems=$((problems + 1))
}

for tool in git glab jq docker; do
  command -v "$tool" >/dev/null 2>&1 || missing "$tool"
done

harnesses=""
for harness in claude omp; do
  command -v "$harness" >/dev/null 2>&1 && harnesses="$harnesses $harness"
done
[ -n "$harnesses" ] || missing "a worker harness: install claude or omp"

first_repo=""
repos=0
for dir in "$root"/*/; do
  [ -d "$dir/.git" ] || continue
  repos=$((repos + 1))
  [ -n "$first_repo" ] || first_repo=$dir
done
[ "$repos" -gt 0 ] || missing "git repos under $root: run this from the workspace folder"

if [ -n "$first_repo" ] && command -v glab >/dev/null 2>&1; then
  (cd "$first_repo" && glab api user >/dev/null 2>&1) || missing "GitLab login: run glab auth login"
fi

if ! command -v acli >/dev/null 2>&1; then
  echo "NOTE acli not installed: Jira cards cannot be read, written requirements still work"
elif ! acli jira auth status >/dev/null 2>&1; then
  echo "NOTE acli not logged in: Jira cards cannot be read, written requirements still work"
fi

echo "WORKSPACE $root repos=$repos"
echo "HARNESSES${harnesses:- none}"
if [ "$problems" -eq 0 ]; then
  echo READY
else
  echo NOT_READY
  exit 1
fi
