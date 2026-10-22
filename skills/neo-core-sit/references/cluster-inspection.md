# Core / Auxiliary cluster inspection — SIT and UAT

One procedure for `neo-core-sit`, `neo-aux-sit`, `neo-core-uat` and `neo-aux-uat`.
The active skill supplies environment bindings; never take bindings from another skill.
This file and `opensearch.md` belong to `neo-core-sit` and are reused by all four skills.
Resolve `CORE_SKILL_DIR` to the directory containing `neo-core-sit/SKILL.md`;
shared assets are relative to that directory, not to the invoking UAT/Aux skill.

## Permission: READ by default

Default is **inspect-only**. Do not mutate cluster / ArgoCD / DB unless the user explicitly asks
for that action in the current turn. Invoking a skill is not authorization to write.

Allowed: `kubectl get/describe/logs/top/auth can-i`, secret reads for diagnosis, Application
get/history/diff via kubectl, `psql` SELECT / `\d` / `\dt` / `\di` with LIMIT, AWS identity and
EKS list/describe, local `eks update-kubeconfig` / `sso login`, and OpenSearch read/search.
An optional local port-forward may be used to view Argo UI/API.

Only on an explicit current-turn request: `kubectl apply|create|delete|patch|replace|rollout|scale|exec`,
`argocd app sync|rollback|delete|prune`, Secret/ConfigMap edits, SQL write/DDL and pod restarts.
Otherwise refuse those actions and continue read-only. Never persist decoded credentials in
repo files, skills or durable memory.

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

Use `--profile "$PROFILE" --region "$REGION"` on every subsequent AWS call.
Run `aws sts get-caller-identity --profile "$PROFILE" --region "$REGION"` each session.
On expired SSO credentials, use `aws sso login --profile "$PROFILE" --region "$REGION"`;
the user approves browser authentication. An identity mismatch is not an expired-session error:
stop rather than logging into or querying the wrong account.

For SIT, compare Account and ARN role against the active wrapper's `EXPECTED_ACCOUNT` and
`EXPECTED_ROLE`. For UAT, inspect the selected profile's account/role configuration and compare
it with STS; do not import SIT account IDs or role expectations. A missing region stops the flow.

## 2. Resolve and verify the EKS target

SIT supplies a known `CLUSTER`. UAT deliberately supplies none: discover it with the selected
profile, not by replacing `sit` in a name or reusing the current kubeconfig context.

```bash
aws eks list-clusters --profile "$PROFILE" --region "$REGION"
aws eks describe-cluster --name "$CLUSTER" --profile "$PROFILE" --region "$REGION"
```

For UAT, assign `CLUSTER` only after inspecting candidates. Check name, ARN account/region and
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
For SIT, smoke `get applications -n "$ARGO_NS"`. For UAT, discover Application namespaces with
`kubectl --context "$CTX" get applications -A`; assign `ARGO_NS` from the matching Application's
metadata namespace. Read its `spec.destination.namespace` for workload `NS` before deployments,
logs or secrets. Namespace hints below are not proof of a UAT destination.

## 3. Resolve service names live

List deployments in the destination namespace; Argo Application and deployment names can differ.
Find secrets by service fragment and inspect the matching name (`-secret` and `-secrets` both occur).
Use the **grep tool** on command output/artifacts, never `kubectl ... | rg` or `... | grep` in bash.

### Core mapping hints (measured on SIT)

Spoken name → deployment → Argo Application → secret. SIT namespace is `core-systems`.
Verify these hints live in UAT and always prefer the Application destination:

- payment / payment-gateway → payment → payment-service → payment-secret
- account → account → account-service → account-secret
- transaction → transaction → transaction-service → transaction-secret
- transaction-consumer → transaction-consumer → transaction-consumer-service → transaction-consumer-secret
- product → product → product-service → product-secret
- authentication → authentication → authentication-service → authentication-secret
- customer / customer-api → customer-api → customer-service → customer-api-secret (+ customer-consumer-secret)
- customer-profiling → customer-profiling → customer-profiling-service → customer-profiling-secret
- customer-settings → customer-settings → customer-settings-service → customer-settings-secret
- bff / backend-for-frontend → backend-for-frontend → backend-for-frontend-service → backend-for-frontend-secret
- bot → bot → bot-service → bot-secret
- wai-adapter → wai-adapter → wai-adapter-service → wai-adapter-secret
- as400adapter → as400adapter → as400adapter-service → inspect secrets list

Fuzzy lookup: `kubectl --context "$CTX" get secrets,deploy -n "$NS"`.
Core SIT uses managed ArgoCD with no in-cluster `argocd-server`; prefer Application CRDs.
The retired SIT cluster `eks-cluster-hbq5y8` is not a fallback for `core-eks-hbq5y8`.

### Auxiliary namespace hints (measured on SIT)

- consent / tc-service → consent
- datamart-* → datamart
- e-document → e-signature
- ekyc-* → ekyc
- email-* → email
- los-credit-card family → los-credit-card
- as-app / as-service / example-* → ndid-interface
- push-notification → notification
- portal-* → portal
- sms → sms
- special-list-* → special-list
- kafbat-ui → kafbat-ui
- kong → kong
- common-service → auxiliary-systems

Fuzzy lookup: `kubectl --context "$CTX" get deploy,secrets -A`.
Auxiliary SIT Applications mostly live in `argocd-app`, occasionally `argocd`; the control plane
is in `argocd`. Its self-hosted `argocd-server` is ClusterIP and local admin is disabled.
Do not assume either SIT Argo flavor in UAT; inspect the live services/Applications first.

## 4. Inspect logs and workload health

Last ~15–30 minutes while the pod exists: kubectl first. Older windows, rotated pods, multi-pod
history or counts by `msg`: read `references/opensearch.md` in `CORE_SKILL_DIR`.
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
without a current-turn request. Use only a verified environment-specific UI URL. Auxiliary SIT's
UI is supplied by its wrapper; UAT URLs must be discovered, not derived from SIT hostnames.

## 6. Inspect Postgres settings

List secrets in `NS`, then grep the output for the service fragment. Core SIT typically stores
`config.yaml`: top-level `postgres`, or `database.postgres` with `username` in authentication-service.
The shared helper also accepts YAML blobs such as `secrets.yaml`, discrete `POSTGRES_*` and `DB_*`.
Do not assume the same secret layout in UAT; inspect keys and use the existing helper.

```bash
PG="$CORE_SKILL_DIR/scripts/pg-from-secret"
"$PG" --context "$CTX" --namespace "$NS" --secret "$SECRET"
"$PG" --context "$CTX" --namespace "$NS" --secret "$SECRET" --psql -- \
  -c 'SELECT current_user, current_database();'
```

Always supply the resolved namespace/secret explicitly, including for Core UAT; do not inherit
the helper's `--service` shortcut namespace. Manual decoding is a fallback only if the helper fails.
Use `--export` / `--with-password` only when the user asks to connect or reveal credentials.
Report host/database/user/schema by default; passwords remain hidden. Extracted settings do not
prove laptop connectivity to private RDS. SELECT/describe with LIMIT only; never SQL write/DDL.

## 7. Inspect ExternalSecret drift and report

Get/describe matching ExternalSecrets in `NS`; inspect their SecretStore/ClusterSecretStore when
not Ready. Do not patch a secret, store or workload to resolve drift without explicit authorization.

Report in Thai, terminal-friendly: environment/domain; identity (STS account/role, profile only as
“from env”); verified cluster/context; Argo sync/health/revision/image; pod ready/restarts;
timestamped log snippets and complete OpenSearch msg counts when used; DB host/db/user/schema.

## Verification

1. The active wrapper's profile env is non-empty; its configured region is non-empty.
2. STS identity and EKS ARN/tags establish the intended environment/domain before kubectl.
3. `CTX` is refreshed with that profile/cluster; namespace and Applications are readable.
4. The named service's Application destination, deployment, logs and secret resolve live.
5. Postgres decoding uses the shared helper without exposing credentials by default.
6. Historical searches use the correct environment's host/index; XHR returns 200 and complete
   aggregation counts sum to `hits.total`. Never label a capped sample as a full total.
