#!/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
repo_root="$(cd "$SCRIPT_DIR/.." && pwd)"
helper="$repo_root/skills/neo-core-sit/scripts/pg-from-secret"
tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

# The scrape fallback only runs without PyYAML, so block it even on machines that have it.
mkdir -p "$tmp_dir/bin" "$tmp_dir/no-yaml"
printf '%s\n' 'raise ImportError("blocked by pg-from-secret-test")' > "$tmp_dir/no-yaml/yaml.py"
cat > "$tmp_dir/bin/kubectl" <<'EOF'
#!/bin/bash
cat "$FAKE_SECRET_JSON"
EOF
chmod +x "$tmp_dir/bin/kubectl"

run_helper() {
  local config="$1"
  python3 -c 'import base64, json, sys
print(json.dumps({"data": {"config.yaml": base64.b64encode(sys.argv[1].encode()).decode()}}))' \
    "$config" > "$tmp_dir/secret.json"
  FAKE_SECRET_JSON="$tmp_dir/secret.json" PYTHONPATH="$tmp_dir/no-yaml" PATH="$tmp_dir/bin:$PATH" \
    bash "$helper" --context test --namespace test --secret test --json
}

assert_postgres() {
  local name="$1" config="$2" expected_user="$3" actual
  actual="$(run_helper "$config" | jq -r '[.host, .port, .user, .database, .schema] | join(" ")')"
  if [ "$actual" != "pg.example 5432 $expected_user sit_core payment" ]; then
    echo "FAIL: $name: got '$actual'" >&2
    exit 1
  fi
}

postgres_block='postgres:
  host: pg.example
  port: 5432
  user: payment_service
  password: pg-pass
  database: sit_core
  sslmode: require
  schema: payment'
redis_block='redis:
  host: valkey.example
  port: 6379
  username: valkey_user
  password: valkey-pass
  database: 1'

assert_postgres "postgres before redis" "$postgres_block
$redis_block" payment_service
assert_postgres "redis before postgres" "$redis_block
$postgres_block" payment_service
assert_postgres "postgres nested under database" "database:
  postgres:
    host: pg.example
    port: 5432
    username: auth_service
    password: pg-pass
    database: sit_core
    schema: payment
$redis_block" auth_service
assert_postgres "flat top-level keys" "host: pg.example
port: 5432
user: flat_user
password: pg-pass
database: sit_core
schema: payment" flat_user

if run_helper "$redis_block" >/dev/null 2>&1; then
  echo "FAIL: a config with no postgres block must not resolve to the redis host" >&2
  exit 1
fi

echo "PASS: pg-from-secret reads only the postgres settings"
