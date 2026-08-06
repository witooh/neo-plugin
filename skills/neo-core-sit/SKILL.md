---
name: "neo-core-sit"
description: "Connect to Core SIT (kubectl + managed ArgoCD) to inspect logs (kubectl + OpenSearch), deploy status, and locate Postgres connection settings inside service K8s secrets for debugging."
version: 3
created: "2026-07-24"
updated: "2026-08-06"
---
## Permission: READ by default

Default is **inspect-only**. Do not mutate cluster / ArgoCD / DB unless the user **explicitly** asks for that action in the current turn.

**Default allowed:** `kubectl get/describe/logs/top/auth can-i`, read secrets for diagnosis, Application get/history/diff via kubectl, `psql` SELECT / \\d / \\dt / \\di with LIMIT, `aws sts` / `eks update-kubeconfig` / `sso login` for local auth, OpenSearch Discover **read/search** via browser session (see logs section).

**Mutating (only if user explicitly asks):** `kubectl apply|create|delete|patch|replace|rollout|scale|exec`, `argocd app sync|rollback|delete|prune`, Secret/ConfigMap edits, SQL write/DDL, pod restarts. If not explicitly requested — refuse and stay read-only.

## When to Use
Use when the user asks to inspect Core SIT / core-neo live state: pod logs, OpenSearch historical logs, restarts, ArgoCD app sync/health/history, deployment image/tag, ExternalSecret status, or Postgres connection settings for a Neo core service (payment, account, transaction, …). Triggers: ดู log core sit, core-neo, argocd payment, หา postgres, debug บน SIT, ดู secret payment, opensearch payment, search log sit. Not for Auxiliary cluster — use `neo-aux-sit`. Not for mutating cluster state unless the user explicitly asks.

## Local auth (required env)

**No AWS profile name is baked into this skill.** Before any `aws` / `eks` call:

1. Read env `NEO_CORE_AWS_PROFILE`.
2. If unset/empty → **stop**. Tell the user to export it to their local profile name, e.g.  
   `export NEO_CORE_AWS_PROFILE=<profile-in-aws-config>`  
   Optional helper file: copy `sit.env.example` → keep outside git / shell rc.  
   Do **not** invent a default profile name.
3. Resolve region from that profile (do not hardcode region in commands when config has it):  
   `REGION=$(aws configure get region --profile "$NEO_CORE_AWS_PROFILE")`  
   If empty → stop and ask user to set `region` (or `sso_region` workflow) on that profile in `~/.aws/config`.
4. Optional checks from the same profile (informational):  
   `aws configure get sso_role_name --profile "$NEO_CORE_AWS_PROFILE"`  
   Expect org role **CoreIntegrationAccess** (not SystemsManagerAccess).

Use `"$NEO_CORE_AWS_PROFILE"` and `"$REGION"` in every aws command below. Shorthand in this doc: `$PROFILE` / `$REGION`.

## Procedure
1. Identity map (org SIT — shared team defaults):
- Env: Core SIT (Neo core)
- AWS account (expect): 986629373331 — confirm live via sts, do not assume
- EKS cluster: `core-eks-hbq5y8` (legacy name `eks-cluster-hbq5y8` is dead)
- kubectl context alias: `core-neo`
- Workload namespace: `core-systems`
- Argo Application namespace: `argocd`
- Argo flavor: AWS EKS Capability for Argo CD (managed). No in-cluster argocd-server. Prefer kubectl Application CRDs over the argocd CLI.
2. Connect / heal access (every session, before queries):
1) Require `$PROFILE` / `$REGION` per **Local auth** above.
2) `aws sts get-caller-identity --profile "$PROFILE"` — expect account **986629373331** and ARN role **CoreIntegrationAccess**. On Forbidden/expired: `aws sso login --profile "$PROFILE"` (user approves browser).
3) If context missing / NXDOMAIN / ResourceNotFound:  
   `aws eks update-kubeconfig --name core-eks-hbq5y8 --region "$REGION" --profile "$PROFILE" --alias core-neo`
4) Smoke: `kubectl --context core-neo get ns` && `kubectl --context core-neo get applications -n argocd`  
Always pass `--context core-neo`. Never assume current-context is core.
3. Name mapping (spoken → deploy → Argo app → secret in core-systems):
- payment / payment-gateway → deploy payment → Application payment-service → secret payment-secret
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
- as400adapter → as400adapter → as400adapter-service → check secrets list
Fuzzy when unsure: `kubectl --context core-neo get secrets,deploy -n core-systems` then use the **grep tool** on the output for FRAGMENT; also `get applications -n argocd`.
4. Inspect logs / health (read-only). Set `CTX=core-neo` `NS=core-systems` `APP=payment` (change APP):

**Choose path:**
| Need | Path |
|---|---|
| Last ~15–30m, pod still running | **A. kubectl** |
| Older window / pod rotated / count by `msg` / multi-pod history | **B. OpenSearch** — read `references/opensearch-sit.md` (same dir as this skill) and follow it |

**A. kubectl (recent)**
- `kubectl --context $CTX get pods -n $NS -l app=$APP -o wide`
- `kubectl --context $CTX logs -n $NS deploy/$APP --since=15m --tail=500`
- `kubectl --context $CTX logs -n $NS deploy/$APP --tail=200`
- previous crash: `logs --previous --tail=200`
- events: `kubectl --context $CTX get events -n $NS --sort-by=.lastTimestamp` (filter with grep tool on output)
- running image/tag: `kubectl --context $CTX get deploy $APP -n $NS -o jsonpath='{.spec.template.spec.containers[0].image}'`
- **Filter:** use the **grep tool** on the command output or a temp file. **Never** `kubectl … | rg` or `… | grep` in bash (interceptor blocks them).

**B. OpenSearch (historical)** — full recipe in `references/opensearch-sit.md`:
- Host: `https://opensearch.sit.awesome-poc-th.com` (Dashboards 3.5.0)
- Index: `console-sit-log`; filter `kubernetes_container_name` = deploy/container name (e.g. `payment`)
- Call `POST /_dashboards/api/console/proxy?path=console-sit-log%2F_search&method=POST` via **sync XHR inside a browser tab** (session cookies; httpOnly)
- **Not proven:** export cookie → shell curl
- **Cold start:** if SSO/login page or XHR 401/HTML login → ask user to log in, then retry
- `tab.evaluate` must not `await fetch` — sync `XMLHttpRequest` only
- When reporting aggregates, ensure counts sum to `hits.total` (do not present a capped `size` sample as full totals)

5. ArgoCD status via kubectl (managed capability — no argocd CLI server):
- List: kubectl --context core-neo get applications -n argocd -o custom-columns=NAME:.metadata.name,SYNC:.status.sync.status,HEALTH:.status.health.status,REV:.status.sync.revision
- One app JSON summary: get application ARGO_APP -n argocd -o json | jq '{sync:.status.sync.status,rev:.status.sync.revision,health:.status.health.status,images:[.status.summary.images[]?],conditions:.status.conditions,source:.spec.source}'
- History last 5: jq '.status.history[-5:] | .[] | {id,deployedAt,revision,initiatedBy}'
Default read-only. Never sync/prune/delete unless user explicitly requests a mutate.
6. Postgres connection settings from service secrets:
- Secret name ≈ <service>-secret in core-systems
- Almost always a single key config.yaml (ExternalSecrets from ClusterSecretStore aws-secrets-store), mounted at /app/config
- Shape A (most services): top-level postgres with host, port, user, database, sslmode, optional schema
- Shape B (authentication-service): database.mode + database.postgres with username instead of user
- **Reuse helper (do NOT rewrite ad-hoc Python each time):** resolve relative to this skill dir (parent of `SKILL.md`):
  `scripts/pg-from-secret`
  ```bash
  # SKILL_DIR = directory containing this SKILL.md
  PG="$SKILL_DIR/scripts/pg-from-secret"
  # summary (password hidden)
  "$PG" --context core-neo --service payment
  # query
  "$PG" --context core-neo --service payment --psql -- \
    -c "SELECT id, route, status, created_at FROM payment.audit_log ORDER BY created_at DESC LIMIT 5;"
  # export env for a manual session
  eval "$("$PG" --context core-neo --service payment --export)"
  ```
- Manual fallback only if the helper fails: kubectl get secret + jq keys + decode config.yaml.
- DB safety: SELECT and describe only; LIMIT rows; never write/DDL. Prefer the helper's --psql one-shot.
7. ExternalSecret drift: kubectl --context core-neo get externalsecret -n core-systems; get clustersecretstore; describe the matching ExternalSecret if Ready!=True.
8. Report in Thai, terminal-friendly: identity used (account/role from sts, profile name only as “from env”); Argo SYNC/HEALTH + image tag; pod READY/restarts; log evidence with timestamps (and OpenSearch msg counts when used); for DB report host/db/user/schema by default and only reveal the secret value when the user asked to connect. Never write decoded secrets into repo files, skill body, or durable memory.

## Pitfalls
- Aux SIT is a different AWS account/cluster — use `neo-aux-sit` + `NEO_AUX_AWS_PROFILE`, not this skill’s profile.
- Stale kubeconfig cluster name `eks-cluster-hbq5y8` causes ResourceNotFound or NXDOMAIN — use `core-eks-hbq5y8`.
- SSO role **SystemsManagerAccess** yields ForbiddenException; need **CoreIntegrationAccess** on the profile.
- Missing `NEO_CORE_AWS_PROFILE` → fail fast; never guess a profile name.
- argocd CLI 'server address unspecified' is expected on Core; use kubectl Application CRDs.
- Secret stores settings inside config.yaml, not discrete DB_* keys — grepping only for bare keys misses it.
- authentication-service nests under database.postgres and uses username not user.
- Extracted RDS settings do not imply laptop connectivity — private network.
- Read-only by default: no apply/delete/sync/secret edits unless user explicitly asks.
- Never persist decoded credentials into git, skills, or memory stores.
- OpenSearch: do not pipe kubectl to `rg`; do not assume curl+cookie works; do not await fetch in `tab.evaluate`; ask user on SSO cold start.
- OpenSearch `log` field is a JSON **string** — parse client-side for `msg`/`level`.

## Verification
1. `NEO_CORE_AWS_PROFILE` set; `aws configure get region --profile "$PROFILE"` non-empty.
2. `aws sts get-caller-identity --profile "$PROFILE"` → account 986629373331 + CoreIntegrationAccess.
3. kubectl --context core-neo get ns lists core-systems and argocd.
4. kubectl --context core-neo get applications -n argocd lists core apps (e.g. payment-service).
5. For a named service: deploy in core-systems, logs readable, matching *-secret has config.yaml containing a postgres (or database.postgres) block.
6. When using OpenSearch: browser session authenticated; search XHR status 200; reported msg counts sum to `hits.total`.
