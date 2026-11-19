#!/usr/bin/env bash
# Exercises worker.sh against stub claude and omp binaries.
script="$(cd "$(dirname "$0")/.." && pwd)/skills/neo/scripts/worker.sh"
work=$(mktemp -d); mkdir -p "$work/bin" "$work/wt" "$work/run"; fails=0
cat > "$work/bin/claude" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "PWD=$PWD" "ARGS=$*" >> "$STUB_LOG"
echo '{"type":"system","subtype":"init"}'
echo '{"type":"result","subtype":"success","result":"working notes\n{\"status\":\"done\",\"repo\":\"r\"}"}'
STUB
cat > "$work/bin/omp" <<'STUB'
#!/usr/bin/env bash
printf '%s\n' "PWD=$PWD" "ARGS=$*" >> "$STUB_LOG"
echo 'Warning: mcp failed' >&2
echo '{"type":"session","id":"omp-session-1"}'
echo '{"type":"agent_end","messages":[{"role":"assistant","content":[{"type":"text","text":"notes\n{\"status\":\"done\",\"repo\":\"o\"}"}]}]}'
STUB
chmod +x "$work/bin/claude" "$work/bin/omp"
export PATH="$work/bin:$PATH" STUB_LOG="$work/calls.log"
echo 'do the work' > "$work/run/brief.md"
check() { if eval "$2"; then echo "ok   $1"; else echo "FAIL $1 :: $2"; fails=$((fails+1)); fi; }
w() { (cd "$work" && bash "$script" "$@"); }

: > "$STUB_LOG"; w run claude "$work/wt" "$work/run/c.session" "$work/run/brief.md" "$work/run/c1.jsonl"; check claude_start_exit "[ $? = 0 ]"
id=$(cat "$work/run/c.session" 2>/dev/null)
check claude_session_saved "[ -n '$id' ]"
check claude_uses_session_id "grep -q -- '--session-id $id' '$STUB_LOG'"
check claude_full_permissions "grep -q -- '--permission-mode bypassPermissions' '$STUB_LOG'"
check claude_runs_in_worktree "grep -q 'PWD=$work/wt' '$STUB_LOG' || grep -q 'PWD=/private$work/wt' '$STUB_LOG'"
check claude_result "[ \"\$(w result claude '$work/run/c1.jsonl')\" = '{\"status\":\"done\",\"repo\":\"r\"}' ]"
: > "$STUB_LOG"; w run claude "$work/wt" "$work/run/c.session" "$work/run/brief.md" "$work/run/c2.jsonl"
check claude_resumes "grep -q -- '--resume $id' '$STUB_LOG'"
check claude_no_new_session "! grep -q -- '--session-id' '$STUB_LOG'"

: > "$STUB_LOG"; w run omp "$work/wt" "$work/run/o.session" "$work/run/brief.md" "$work/run/o1.jsonl"; check omp_start_exit "[ $? = 0 ]"
check omp_session_saved "[ \"\$(cat '$work/run/o.session' 2>/dev/null)\" = omp-session-1 ]"
check omp_auto_approve "grep -q -- '--auto-approve' '$STUB_LOG'"
check omp_json_mode "grep -q -- '--mode json' '$STUB_LOG'"
check omp_stderr_separate "! grep -q 'Warning: mcp' '$work/run/o1.jsonl'"
check omp_result "[ \"\$(w result omp '$work/run/o1.jsonl')\" = '{\"status\":\"done\",\"repo\":\"o\"}' ]"
: > "$STUB_LOG"; w run omp "$work/wt" "$work/run/o.session" "$work/run/brief.md" "$work/run/o2.jsonl"
check omp_resumes "grep -q -- '--resume omp-session-1' '$STUB_LOG'"

: > "$STUB_LOG"; NEO_WORKER_ARGS='--model sonnet' w run claude "$work/wt" "$work/run/x.session" "$work/run/brief.md" "$work/run/x.jsonl"
check extra_args "grep -q -- '--model sonnet' '$STUB_LOG'"
echo 'not json' > "$work/run/bad.jsonl"; w result claude "$work/run/bad.jsonl" >/dev/null 2>&1; check empty_result_fails "[ $? != 0 ]"
w run codex "$work/wt" "$work/run/z.session" "$work/run/brief.md" "$work/run/z.jsonl" >/dev/null 2>&1; check unknown_harness_rejected "[ $? != 0 ]"
rm -rf "$work"; echo "failures=$fails"; [ "$fails" = 0 ]
