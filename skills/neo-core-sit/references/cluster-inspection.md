# Core / Auxiliary cluster inspection — SIT and UAT

One procedure for `neo-core-sit`, `neo-aux-sit`, `neo-core-uat` and `neo-aux-uat`.
The active skill supplies environment bindings; never take bindings from another skill.
This file, `opensearch.md`, `kafka.md` and `tracing.md` belong to `neo-core-sit` and are reused by all
four skills.
Resolve `CORE_SKILL_DIR` to the `neo-core-sit` skill directory itself (the one whose `SKILL.md`
has `name: neo-core-sit`, i.e. `<skills>/neo-core-sit`); shared assets are relative to that
directory, not to the invoking UAT/Aux skill.

## Permission: READ by default, READ only on UAT

Default is **inspect-only**. Invoking a skill is not authorization to write.

Allowed: `kubectl get/describe/logs/top/auth can-i`, secret reads for diagnosis, Application
get/history/diff via kubectl, `psql` SELECT / `\d` / `\dt` / `\di` with LIMIT, AWS identity and
EKS/RDS list/describe, MSK `list-clusters-v2` / `get-bootstrap-brokers`, local
`eks update-kubeconfig` / `eks get-token` /
`rds generate-db-auth-token` / `sso login`, OpenSearch
read/search, Kafbat REST GETs on the wrapper's `KAFBAT_URL`, and Argo REST GETs in an authenticated
browser session on the wrapper's verified URL.
An optional local port-forward may be used to view Argo UI/API.

Only when `ENVIRONMENT=SIT` and on an explicit current-turn request:
`kubectl apply|create|delete|patch|replace|rollout|scale|exec`,
`argocd app sync|rollback|delete|prune`, Secret/ConfigMap edits, SQL write/DDL and pod restarts.
Otherwise refuse those actions and continue read-only. Never persist decoded credentials in
repo files, skills or durable memory. Kafka has no write exception: `kafka.md` allows GET only.

`ENVIRONMENT=UAT` has no write exception. Refuse every change to UAT, even when the user asks for
it in the current turn: the actions above, any Argo UI or API action other than a GET, any Kafbat
request other than a GET, OpenSearch requests other than `_search` / `_count` / GETs, mutating AWS
calls (for example
`create-access-entry`) and any SQL write or DDL. Tell the user what change is needed and give the
command or UI step for them to run themselves; never run it for them. Local writes that only
enable reads (`update-kubeconfig`, `sso login`) are allowed.

## 1. Authenticate with the active environment's profile

Set the bindings from the active skill first. `PROFILE_ENV` names the **only** accepted profile
env variable. Do not fall back to `AWS_PROFILE`, a different environment/domain, or a guessed
profile name. Run this gate before any AWS call:

```bash
if ! PROFILE="$(printenv "$PROFILE_ENV")" || [ -z "$PROFILE" ]; then
  printf 'Set %s to your local AWS profile name.\n' "$PROFILE_ENV" >&2
  exit 2
fi
if ! REGION="$(aws configure get region --profile "$PROFILE")" || [ -z "$REGION" ]; then
  printf 'Set region on the selected AWS profile in ~/.aws/config.\n' >&2
  exit 2
fi
```

The gate reads the agent's process environment: a value changed in a shell rc after the session
started stays invisible until the session restarts. Use the user's stated value for that run only.
Use `--profile "$PROFILE" --region "$REGION"` on every subsequent AWS call.
Run `aws sts get-caller-identity --profile "$PROFILE" --region "$REGION"` each session.
On expired SSO credentials, use `aws sso login --profile "$PROFILE" --region "$REGION"`;
the user approves browser authentication. An identity mismatch is not an expired-session error:
stop rather than logging into or querying the wrong account.

When the active wrapper sets `EXPECTED_ACCOUNT` and `EXPECTED_ROLE`, compare Account and ARN role
against them. When they are empty, inspect the selected profile's account/role configuration and
compare it with STS; never import another environment's account IDs or role expectations.
A missing region stops the flow.

## 2. Resolve and verify the EKS target

When the wrapper supplies `CLUSTER`, describe it and confirm its ARN account/region. When `CLUSTER`
is empty, discover it with the selected profile, not by replacing `sit` in a name or reusing the
current kubeconfig context.

```bash
aws eks list-clusters --profile "$PROFILE" --region "$REGION"
aws eks describe-cluster --name "$CLUSTER" --profile "$PROFILE" --region "$REGION"
```

With an empty `CLUSTER`, assign it only after inspecting candidates. Check name, ARN account/region and
tags against **both** the requested environment and domain. One listed cluster is not, by itself,
proof that it is the UAT target. If discovery is forbidden, empty or ambiguous, use existing
verified infrastructure/configuration evidence; if still unresolved, ask the user for the target
and stop before kubeconfig/kubectl. Never select the first result or fall back to SIT.

Before **any** kubectl query each session, refresh the active wrapper's context from the verified
cluster and selected profile. This prevents an existing alias from retaining a different profile
or cluster after the environment/profile changes. This writes local kubeconfig only:

```bash
aws eks update-kubeconfig --name "$CLUSTER" --region "$REGION" --profile "$PROFILE" --alias "$CTX"
kubectl --context "$CTX" get ns
```

Always pass `--context "$CTX"`; never trust current-context. UAT aliases are separate from SIT.
If kubectl then fails with `the server has asked for the client to provide credentials` while
`aws eks get-token` succeeds, the role has no EKS access entry: do not retry or log in again.
Follow the active wrapper's non-kubectl path if it names one; otherwise stop and report.
When `ARGO_NS` is set, smoke `get applications -n "$ARGO_NS"`. When it is empty, discover
Application namespaces with `kubectl --context "$CTX" get applications -A`; assign `ARGO_NS` from the matching Application's
metadata namespace. Read its `spec.destination.namespace` for workload `NS` before deployments,
logs or secrets. Namespace hints below are not proof of a UAT destination.

## 3. Resolve service names live

List deployments in the destination namespace; Argo Application and deployment names can differ.
Find secrets by service fragment and inspect the matching name (`-secret` and `-secrets` both occur).
Use the **grep tool** on command output/artifacts, never `kubectl ... | rg` or `... | grep` in bash.

### Core mapping hints (measured on `core-eks-ckrztgxi8f-sit`, 2026-11-04)

Spoken name → deployment → Argo Application → secret. SIT namespace is `core-systems`.
Verify these hints live in UAT and always prefer the Application destination:

- payment / payment-gateway → payment, payment-pcc → payment-service → payment-secret
- account → account → account-service → account-secret
- transaction → transaction → transaction-service → transaction-secret (+ CronJob transaction-cron → transaction-cron-secret)
- transaction-consumer → transaction-consumer → transaction-consumer-service → transaction-consumer-secret
- product → product → product-service → product-secret
- authentication → authentication → authentication-service → authentication-secret
- customer / customer-api → customer-api → customer-service → customer-api-secret
- customer-profiling → customer-profiling → customer-profiling-service → customer-profiling-secret
- customer-settings → customer-settings → customer-settings-service → customer-settings-secret
- bff / backend-for-frontend → backend-for-frontend → backend-for-frontend-service → backend-for-frontend-secret
- bot → bot → bot-service → bot-secret
- wai-adapter → wai-adapter → wai-adapter-service → wai-adapter-secret
- credit-card-authorization → credit-card-authorization → credit-card-authorization-service → credit-card-authorization-secret
- gl-mapping → gl-mapping → gl-mapping-service → gl-mapping-secret
- manual-posting → manual-posting → manual-posting-service → manual-posting-secret
- statement → statement → statement-service → statement-secret
- as400adapter, mock, mock-bff → same name → `<name>-service` → no secret mounted

Fuzzy lookup: `kubectl --context "$CTX" get secrets,deploy -n "$NS"`.
Core SIT uses managed ArgoCD with no in-cluster `argocd-server`; prefer Application CRDs.

### Auxiliary namespace hints (from `argocd/sit`, 2026-11-04)

- consent / tc-service → consent
- datamart-api, datamart-notification → datamart
- e-document → e-signature
- ekyc-*, common-api, face-verification-service, qr-service, transaction-api, transaction-service → ekyc
- email-* → email
- los-credit-card family, datamart-external, special-list-external, statement → los-credit-card
- as-app / as-service / crypto-service / example-* → ndid-interface
- branch-device-bff → branch-device
- push-notification → notification
- portal-* → portal
- sms → sms
- special-list-config, special-list-notification, special-list-service → special-list
- kafbat-ui → kafbat-ui
- kong → kong
- common-service → auxiliary-systems
- fraud-* → fraud
- mobile-setting → mobile-setting
- payroll → payroll
- qr → qr
- keda-helm → keda
- demo-keda → demo-keda

Fuzzy lookup: `kubectl --context "$CTX" get deploy,secrets -A`.
Auxiliary SIT uses managed Argo with every Application in `argocd-app`.
Do not assume the SIT Argo setup in UAT; inspect the live services/Applications first.

## 4. Inspect logs and workload health

Last ~15–30 minutes while the pod exists: kubectl first. Older windows, rotated pods, multi-pod
history or counts by `msg`: read `references/opensearch.md` in `CORE_SKILL_DIR`.
On UAT, OpenSearch comes first for every window; follow the UAT wrapper's access notes.
Use only the active environment's verified OpenSearch host/index; UAT has no SIT fallback.

After resolving `DEPLOY` and `NS` live:

```bash
kubectl --context "$CTX" get pods -n "$NS" -o wide
kubectl --context "$CTX" logs -n "$NS" "deploy/$DEPLOY" --since=15m --tail=500
kubectl --context "$CTX" get events -n "$NS" --sort-by=.lastTimestamp
kubectl --context "$CTX" get deploy "$DEPLOY" -n "$NS" -o jsonpath='{.spec.template.spec.containers[0].image}'
```

For a restarted container, read the selected pod/container's `logs --previous --tail=200`.
Optional `top pods` and `describe` are read-only. Record pod READY/restarts and timestamps.
Filter logs with the grep tool; never pipe kubectl to shell grep/rg.

## 5. Inspect ArgoCD

Prefer Application CRDs for both managed and self-hosted ArgoCD:

```bash
kubectl --context "$CTX" get applications -n "$ARGO_NS" -o custom-columns=NAME:.metadata.name,DEST:.spec.destination.namespace,SYNC:.status.sync.status,HEALTH:.status.health.status,REV:.status.sync.revision
kubectl --context "$CTX" get application "$ARGO_APP" -n "$ARGO_NS" -o json
```

For one app, inspect sync/revision/health, destination, summary images, conditions and sources.
History: `.status.history[-5:]` with id/deployedAt/revision/initiatedBy. Never sync/prune/delete
without a current-turn request. Use only a verified environment-specific UI URL from the active
wrapper's `ARGO_URL`. When it is empty, discover it (managed Argo: `aws eks describe-capability
--capability-name argocd` → `serverUrl`), never derive it from another environment's hostname.

## 6. Inspect Postgres settings

When the active wrapper sets `PG_HOST`, connect with an RDS IAM token as its access notes describe
and skip the secret helper below. When it sets `SECRET_PREFIX`, use the Secrets Manager recipe below.
Use the helper there only when the wrapper says kubectl reads secrets and you need the secret a pod
actually mounts; set `PGOPTIONS='-c default_transaction_read_only=on'` for `--psql` so the session
rejects writes. Otherwise resolve settings from the service secret:

List secrets in `NS`, then grep the output for the service fragment. Core SIT typically stores
`config.yaml`: top-level `postgres`, or `database.postgres` with `username` in authentication-service.
The shared helper also accepts YAML blobs such as `secrets.yaml`, discrete `POSTGRES_*` and `DB_*`.
Do not assume the same secret layout in another environment; inspect keys and use the existing helper.

```bash
PG="$CORE_SKILL_DIR/scripts/pg-from-secret"
"$PG" --context "$CTX" --namespace "$NS" --secret "$SECRET"
"$PG" --context "$CTX" --namespace "$NS" --secret "$SECRET" --psql -- \
  -c 'SELECT current_user, current_database();'
```

Always supply the resolved namespace/secret explicitly; do not inherit
the helper's `--service` shortcut namespace. Manual decoding is a fallback only if the helper fails.
Use `--export` / `--with-password` only when the user asks to connect or reveal credentials.
Report host/database/user/schema by default; passwords remain hidden. Extracted settings do not
prove laptop connectivity to private RDS. SELECT/describe with LIMIT only; never SQL write/DDL.

### Secrets Manager recipe (`SECRET_PREFIX` set)

Secret names differ from the Kubernetes ones (`payment-secret` → `sit/core/payment-gateway`), so list
them first. The service's schema is `.rds.schema`. Keep `default_transaction_read_only=on`: it makes
the session reject writes.

```bash
aws secretsmanager list-secrets --profile "$PROFILE" --region "$REGION" \
  --query "SecretList[?starts_with(Name, '$SECRET_PREFIX/')].Name" --output text
JSON="$(aws secretsmanager get-secret-value --secret-id "$SECRET_PREFIX/$SERVICE" \
  --profile "$PROFILE" --region "$REGION" --query SecretString --output text)"
PGHOST="$(jq -r .rds.host <<<"$JSON")" PGPORT="$(jq -r .rds.port <<<"$JSON")" PGUSER="$(jq -r .rds.username <<<"$JSON")" \
PGDATABASE="$(jq -r .rds.database <<<"$JSON")" PGPASSWORD="$(jq -r .rds.password <<<"$JSON")" PGSSLMODE=require \
PGOPTIONS='-c default_transaction_read_only=on' psql -X -c 'SELECT current_user, current_database();'
```

Check what the secret returned before trusting it:

- `.rds.host` must be on the wrapper's RDS. A stale secret can point elsewhere:
  `sit/core/payroll-service` still names deleted `rds-core-hbq5y8`.
- `.rds.host` can be the `cluster-ro` endpoint (`sit/aux/qr-service`, `sit/aux/email-gateway`). Both
  clusters have one instance, so it reached the writer on 2026-11-03. Run
  `SELECT pg_is_in_recovery()` before relying on write access.
- The layout can differ: `rds.specialist_config_db.*` in `sit/aux/specialist`, `datamart_db` in
  `sit/aux/datamart`, and no `rds` at all in some others. Read the `property:` names in the service's
  `overlays/sit` ExternalSecret.
- `jq` exits 5 on secrets that are not strict JSON (`sit/aux/sms-service`,
  `sit/aux/los-credit-card/api`, `sit/aux/portal/portal-superset`, `sit/core/wai-adapter`). Report it
  and ask; do not print the secret to inspect it.

### Migration state

`information_schema.tables` hides tables the role cannot access, so an empty result proves nothing.
Find the table through `pg_catalog`, then compare `version` with the service repo's highest migration:

```sql
SELECT schemaname, tableowner FROM pg_catalog.pg_tables WHERE tablename = 'schema_migrations';
SELECT version, dirty FROM <schema>.schema_migrations;
```

## 7. Inspect ExternalSecret drift and report

Get/describe matching ExternalSecrets in `NS`; inspect their SecretStore/ClusterSecretStore when
not Ready. Where kubectl is blocked, read one with the Argo `/resource` GET using `kind=ExternalSecret`,
`group=external-secrets.io` and `version=v1` (returned `SecretSynced` on Auxiliary SIT, 2026-11-04).
Do not patch a secret, store or workload to resolve drift without explicit authorization.

Report in Thai, terminal-friendly: environment/domain; identity (STS account/role, profile only as
“from env”); verified cluster/context; Argo sync/health/revision/image; pod ready/restarts;
timestamped log snippets and complete OpenSearch msg counts when used; DB host/db/user/schema; Kafka
broker hosts, offsets and whether a scan was complete when used.

## 8. Inspect Kafka

Read `references/kafka.md` in `CORE_SKILL_DIR` and use the active wrapper's `KAFBAT_URL`, `KAFKA_CLUSTER`
and `KAFKA_BROKER`; never another environment's.

## 9. Trace a symptom to its root cause

When a report starts from a Mobile or Portal symptom, or names a correlation id, read
`references/tracing.md` in `CORE_SKILL_DIR` and use its report shape in place of the one in §7. A trace may
read the same environment's skill for the other domain and apply that skill's bindings, `PROFILE_ENV` included,
to reads in that domain. That is the only case where a second profile is accepted.

## Verification

1. The active wrapper's profile env is non-empty; its configured region is non-empty.
2. STS identity and EKS ARN/tags establish the intended environment/domain before kubectl.
3. `CTX` is refreshed with that profile/cluster; namespace and Applications are readable through
   kubectl or the wrapper's non-kubectl path.
4. The named service's Application destination, deployment, logs and secret resolve live by that path.
5. Postgres settings come from the wrapper's path (`PG_HOST`, `SECRET_PREFIX`) or the shared helper,
   without exposing credentials by default.
6. Historical searches use the correct environment's host/index; XHR returns 200 and complete
   aggregation counts sum to `hits.total`. Never label a capped sample as a full total.
7. Kafka reads use GET only, Kafbat's broker hosts contain the wrapper's `KAFKA_BROKER`, and a miss is
   reported as complete only when the scan's `cursor` is null.
8. A trace's `complete` is true, every hop in its diagram comes from a row or is marked as not logged, and
   its cause is proven from the service's own data or labelled inferred.
