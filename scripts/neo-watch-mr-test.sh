#!/usr/bin/env bash
# Exercises watch-mr.sh against a stub glab that replays canned MR JSON.
script="$(cd "$(dirname "$0")/.." && pwd)/skills/neo/scripts/watch-mr.sh"
work=$(mktemp -d); mkdir -p "$work/bin"; fails=0
cat > "$work/bin/glab" <<'STUB'
#!/usr/bin/env bash
n=$(cat "$STUB_DIR/count" 2>/dev/null || echo 0); n=$((n+1)); echo "$n" > "$STUB_DIR/count"
f="$STUB_DIR/$n.json"; [ -f "$f" ] || f=$(ls "$STUB_DIR"/*.json | sort -n | tail -1)
cat "$f"
STUB
chmod +x "$work/bin/glab"
run() { # name expected_exit expected_text approved_sha json...
  local name=$1 want=$2 text=$3 sha=$4; shift 4
  local d="$work/$name"; mkdir -p "$d"; local i=1
  for j in "$@"; do echo "$j" > "$d/$i.json"; i=$((i+1)); done
  out=$(cd "$work" && PATH="$work/bin:$PATH" STUB_DIR="$d" POLL_SECONDS=0 NO_PIPELINE_SECONDS=1 STALL_SECONDS=2 bash "$script" "$work" 42 "$sha" 2>&1); got=$?
  if [ "$got" = "$want" ] && grep -q "$text" <<<"$out"; then echo "ok   $name"; else echo "FAIL $name exit=$got want=$want out=[$out]"; fails=$((fails+1)); fi
}
ok='{"sha":"aaa","head_pipeline":{"id":1,"status":"success","sha":"aaa"}}'
run success 0 'RESULT success' aaa "$ok"
run stale_then_success 0 'RESULT success' aaa '{"sha":"aaa","head_pipeline":{"id":1,"status":"success","sha":"old"}}' "$ok"
run failed 1 'RESULT failed' aaa '{"sha":"aaa","head_pipeline":{"id":2,"status":"failed","sha":"aaa"}}'
run canceled 2 'RESULT canceled' aaa '{"sha":"aaa","head_pipeline":{"id":3,"status":"canceled","sha":"aaa"}}'
run manual 2 'RESULT manual' aaa '{"sha":"aaa","head_pipeline":{"id":4,"status":"manual","sha":"aaa"}}'
run wrong_head 3 'RESULT sha_mismatch' bbb "$ok"
run no_pipeline 3 'RESULT no_pipeline' aaa '{"sha":"aaa","head_pipeline":null}'
run stalled 3 'RESULT stalled' aaa '{"sha":"aaa","head_pipeline":{"id":5,"status":"running","sha":"aaa"}}'
rm -rf "$work"; echo "failures=$fails"; [ "$fails" = 0 ]
