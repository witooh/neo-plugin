#!/usr/bin/env bash
# Waits for the pipeline of an MR's approved commit and ends with one RESULT line.
# Usage: bash watch-mr.sh <repo-dir> <mr-iid> <approved-sha>
# Exit:  0 success | 1 failed | 2 canceled, skipped, manual | 3 sha_mismatch, no_pipeline, stalled
set -u

repo_dir=$1
iid=$2
approved=$3
poll=${POLL_SECONDS:-60}
no_pipeline_limit=${NO_PIPELINE_SECONDS:-600}
stall_limit=${STALL_SECONDS:-3600}

cd "$repo_dir" || exit 3

finish() {
  echo "RESULT $1 mr=!$iid pipeline=${2:-none} sha=${3:-none}"
  exit "$4"
}

last=""
while :; do
  elapsed=$SECONDS
  if ! json=$(glab mr view "$iid" --output json 2>/dev/null); then
    [ "$elapsed" -ge "$stall_limit" ] && finish stalled "" "$approved" 3
    sleep "$poll"
    continue
  fi

  head=$(jq -r '.sha // ""' <<<"$json")
  pipeline_sha=$(jq -r '.head_pipeline.sha // ""' <<<"$json")
  pipeline_id=$(jq -r '.head_pipeline.id // ""' <<<"$json")
  status=$(jq -r '.head_pipeline.status // ""' <<<"$json")

  if [[ -z "$head" || "$head" != "$approved"* ]]; then
    [ "$elapsed" -ge "$no_pipeline_limit" ] && finish sha_mismatch "$pipeline_id" "$head" 3
  elif [ "$pipeline_sha" != "$head" ]; then
    [ "$elapsed" -ge "$no_pipeline_limit" ] && finish no_pipeline "" "$head" 3
  else
    case "$status" in
      success) finish success "$pipeline_id" "$head" 0 ;;
      failed) finish failed "$pipeline_id" "$head" 1 ;;
      canceled | skipped | manual) finish "$status" "$pipeline_id" "$head" 2 ;;
    esac
    [ "$elapsed" -ge "$stall_limit" ] && finish stalled "$pipeline_id" "$head" 3
    if [ "$status" != "$last" ]; then
      echo "STATUS $status mr=!$iid pipeline=$pipeline_id"
      last=$status
    fi
  fi
  sleep "$poll"
done
