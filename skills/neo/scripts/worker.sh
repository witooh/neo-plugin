#!/usr/bin/env bash
# Runs one headless worker turn and continues the same session on later turns.
# Usage: bash worker.sh run <claude|omp> <worktree> <session-file> <brief-file> <log-file>
#        bash worker.sh result <claude|omp> <log-file>
# Pass absolute paths. NEO_WORKER_ARGS adds harness flags, for example "--model sonnet".
set -u

run_claude() {
  if [ -s "$session_file" ]; then
    set -- --resume "$(cat "$session_file")"
  else
    uuidgen | tr 'A-Z' 'a-z' > "$session_file"
    set -- --session-id "$(cat "$session_file")"
  fi
  claude -p "$prompt" "$@" --permission-mode bypassPermissions \
    --output-format stream-json --verbose ${NEO_WORKER_ARGS:-}
}

run_omp() {
  mkdir -p "$session_file.d"
  if [ -s "$session_file" ]; then
    set -- --resume "$(cat "$session_file")"
  fi
  omp -p --mode json --auto-approve --session-dir "$session_file.d" "$@" ${NEO_WORKER_ARGS:-} "$prompt"
}

result_filter() {
  case "$1" in
    claude) echo 'select(.type=="result").result // empty' ;;
    omp) echo 'select(.type=="agent_end") | [.messages[] | select(.role=="assistant")] | last | [.content[] | select(.type=="text").text] | join("")' ;;
  esac
}

command=${1:-}
harness=${2:-}
case "$harness" in
  claude | omp) ;;
  *) echo "unsupported harness: $harness (use claude or omp)" >&2; exit 2 ;;
esac

case "$command" in
  run)
    worktree=$3 session_file=$4 brief=$5 log=$6
    prompt=$(cat "$brief") || exit 2
    (cd "$worktree" && "run_$harness") > "$log" 2> "$log.err" < /dev/null
    status=$?
    echo "{\"type\":\"neo_exit\",\"code\":$status}" >> "$log"
    if [ "$harness" = omp ] && [ ! -s "$session_file" ]; then
      jq -R -r 'fromjson? | select(.type=="session").id' "$log" | head -1 > "$session_file"
    fi
    exit "$status"
    ;;
  result)
    final=$(jq -R -r "fromjson? | $(result_filter "$harness")" "$3" | sed '/^[[:space:]]*$/d' | tail -1)
    [ -n "$final" ] || exit 1
    echo "$final"
    ;;
  *)
    echo "unknown command: $command (use run or result)" >&2
    exit 2
    ;;
esac
