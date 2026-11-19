#!/usr/bin/env bash
# Lists branches and merge requests that already mention a card, across every workspace repo.
# Usage: bash find-existing.sh <card-key-or-term> [workspace-dir]
# A WARN line means part of the scan failed, so the result is incomplete.
set -u

term=$1
root=${2:-$PWD}

scan() {
  local dir=${1%/} repo
  repo=$(basename "$dir")
  [ -d "$dir/.git" ] || return 0

  git -C "$dir" fetch --quiet origin 2>/dev/null || echo "WARN $repo fetch failed"

  git -C "$dir" for-each-ref \
    --format="BRANCH $repo %(refname:short) | %(authorname) | %(committerdate:short)" \
    refs/heads refs/remotes/origin | grep -iF -- "$term"
}

top_group() {
  git -C "$1" remote get-url origin 2>/dev/null |
    sed -E 's#^(ssh://|https?://)?([^@/]*@)?[^/:]+(:[0-9]+)?[:/]##; s#/.*##'
}

# GitLab rate-limits merge request search, so query each top-level group once instead of each repo.
find_merge_requests() {
  local query dir group json seen=" "
  query=$(jq -rn --arg term "$term" '$term | @uri')
  for dir in "$root"/*/; do
    [ -d "$dir/.git" ] || continue
    group=$(top_group "$dir")
    [ -n "$group" ] || continue
    case "$seen" in *" $group "*) continue ;; esac
    seen="$seen$group "
    json=$(cd "$dir" && glab api --paginate \
      "groups/$group/merge_requests?scope=all&state=all&per_page=100&search=$query" 2>/dev/null)
    if [ $? -ne 0 ] || ! jq -e 'type == "array"' <<<"$json" >/dev/null 2>&1; then
      echo "WARN merge request lookup failed for group $group"
      continue
    fi
    jq -r '.[] | "MR \(.web_url | split("/-/")[0] | split("/") | last) !\(.iid) \(.state) \(.source_branch) -> \(.target_branch) | \(.author.username) | \(.web_url)"' <<<"$json"
  done
}

export -f scan
export term

out=$({
  printf '%s\n' "$root"/*/ | xargs -P 6 -I{} bash -c 'scan "$1"' _ {}
  find_merge_requests
} | sort)
[ -n "$out" ] && echo "$out"
echo "SCAN complete term=$term warnings=$(grep -c '^WARN' <<<"$out")"
