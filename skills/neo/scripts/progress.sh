#!/usr/bin/env bash
# Shows what the workers of a run are doing.
# Usage: bash progress.sh <run-dir>                     the run's tasks.md, then one line per turn log: state, minutes, actions, last action
#        bash progress.sh --follow <claude|omp> <log>   one line per commit, then the turn's end
# Follow mode prints a "working" line after 15 quiet minutes and exits 3 with STALLED after 60.
set -u

actions_filter() {
  case "$1" in
    claude) echo 'select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | "\(.name) \((.input.skill // .input.file_path // .input.command // .input.pattern // .input.description // "") | tostring | gsub("\\s+";" ") | .[0:100])"' ;;
    omp) echo 'select(.type=="tool_execution_start") | "\(.toolName) \((.args.path // .args.command // .args) | tostring | gsub("\\s+";" ") | .[0:100])"' ;;
  esac
}

end_filter='select(.type=="neo_exit") | "END exit=\(.code)"'

summary_filter() {
  case "$1" in
    claude) echo 'select(.type=="result") | "cost=$\((.total_cost_usd // 0) * 100 | round / 100) turns=\(.num_turns)"' ;;
    omp) echo 'select(.type=="agent_end") | ""' ;;
  esac
}

turn_end() {
  local end
  end=$(jq -R -r "fromjson? | $end_filter" "$2" | tail -1)
  [ -n "$end" ] && echo "$end $(jq -R -r "fromjson? | $(summary_filter "$1")" "$2" | tail -1)"
}

commit_filter() {
  local cmd
  case "$1" in
    claude) cmd='select(.type=="assistant") | .message.content[]? | select(.type=="tool_use") | (.input.command // "")' ;;
    omp) cmd='select(.type=="tool_execution_start") | (.args.command // "")' ;;
  esac
  echo "$cmd"' | select(type=="string" and test("git commit")) | "commit: " + ((capture("<<-?\\s*.?EOF.?\\s+(?<s>[^\\n]+)") // capture("-m\\s+[\"\\x27](?<s>[^\"\\x27\\n]+)") // {s:"(message not parsed)"}).s)'
}

harness_of() {
  case "$(head -1 "$1" | jq -r '.type' 2>/dev/null)" in
    session) echo omp ;;
    *) echo claude ;;
  esac
}

follow() {
  local harness=$1 log=$2 name seen=0 total chunk out now last_change last_print
  name=$(basename "$log" .jsonl)
  last_change=$(date +%s) last_print=$last_change
  while :; do
    now=$(date +%s)
    total=$(wc -l < "$log" 2>/dev/null || echo 0)
    if [ "$total" -gt "$seen" ]; then
      chunk=$(sed -n "$((seen + 1)),${total}p" "$log")
      seen=$total last_change=$now
      out=$(printf '%s\n' "$chunk" | jq -R -r "fromjson? | $(commit_filter "$harness")")
      [ -n "$out" ] && { printf '%s\n' "$out" | sed "s|^|$(date +%H:%M) $name |"; last_print=$now; }
      out=$(turn_end "$harness" "$log")
      [ -n "$out" ] && { echo "$(date +%H:%M) $name $out"; exit 0; }
    fi
    if [ $((now - last_change)) -gt 3600 ]; then
      echo "$(date +%H:%M) $name STALLED: no output for 60 minutes"
      exit 3
    fi
    if [ $((now - last_print)) -gt 900 ]; then
      out=$(jq -R -r "fromjson? | $(actions_filter "$harness")" "$log" | tail -1)
      echo "$(date +%H:%M) $name working, $seen log lines, last: $out"
      last_print=$now
    fi
    sleep 10
  done
}

snapshot() {
  local run=$1 log name harness now born actions last end state
  now=$(date +%s)
  [ -f "$run/tasks.md" ] && { cat "$run/tasks.md"; echo; }
  for log in "$run"/*.jsonl; do
    [ -f "$log" ] || continue
    name=$(basename "$log" .jsonl)
    harness=$(harness_of "$log")
    born=$(stat -f %B "$log" 2>/dev/null || stat -c %W "$log")
    actions=$(jq -R -r "fromjson? | $(actions_filter "$harness")" "$log" | wc -l | tr -d ' ')
    last=$(jq -R -r "fromjson? | $(actions_filter "$harness")" "$log" | tail -1)
    end=$(turn_end "$harness" "$log")
    if [ -n "$end" ]; then
      state=$end
    elif [ $((now - $(stat -f %m "$log" 2>/dev/null || stat -c %Y "$log"))) -gt 600 ]; then
      state="QUIET for $(((now - $(stat -f %m "$log" 2>/dev/null || stat -c %Y "$log")) / 60)) min"
    else
      state=RUNNING
    fi
    echo "$name | $state | $(((now - born) / 60)) min | $actions actions | last: $last"
  done
}

case "${1:-}" in
  --follow) follow "$2" "$3" ;;
  "") echo "usage: bash progress.sh <run-dir> | --follow <claude|omp> <log>" >&2; exit 2 ;;
  *) snapshot "$1" ;;
esac
