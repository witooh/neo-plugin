---
name: "neo-aux-sit"
description: "Connect to Auxiliary SIT (kubectl + self-hosted ArgoCD) to inspect logs (kubectl + OpenSearch), deploy status, and locate Postgres connection settings inside service K8s secrets for debugging."
version: 3
created: "2026-07-24"
updated: "2026-08-06"
---
## Permission: READ by default

Default is **inspect-only**. Do not mutate cluster / ArgoCD / DB unless the user **explicitly** asks for that action in the current turn.

**Default allowed:** `kubectl get/describe/logs/top/auth can-i`, read secrets for diagnosis, Application get/history/diff via kubectl, `psql` SELECT / \\d / \\dt / \\di with LIMIT, `aws sts` / `eks update-kubeconfig` / `sso login` for local auth, optional port-forward to view Argo UI/API, OpenSearch Discover **read/search** via browser session (shared SIT recipe).

**Mutating (only if user explicitly asks):** `kubectl apply|create|delete|patch|replace|rollout|scale|exec`, `argocd app sync|rollback|delete|prune`, Secret/ConfigMap edits, SQL write/DDL, pod restarts. If not explicitly requested — refuse and stay read-only.

## When to Use
Use when the user asks to inspect Auxiliary SIT / aux-eks live state: pod logs, OpenSearch historical logs, restarts, ArgoCD app sync/health/history, deployment image/tag, ExternalSecret status, or Postgres connection settings for an Aux service (sms, email, portal, ekyc, special-list, los-credit-card, consent, datamart). Triggers: ดู log aux sit, aux-neo, aux-eks, argocd-auxiliary, หา postgres บน aux, debug auxiliary, opensearch aux, search log sit. Not for Core cluster — use `neo-core-sit`. Not for mutating cluster state unless the user explicitly asks.

## Local auth (required env)

**No AWS profile name is baked into this skill.** Before any `aws` / `eks` call:

1. Read env `NEO_AUX_AWS_PROFILE`.
2. If unset/empty → **stop**. Tell the user to export it to their local profile name, e.g.  
   `export NEO_AUX_AWS_PROFILE=<profile-in-aws-config>`  
   Optional helper: copy `sit.env.example` → keep outside git / shell rc.  
   Do **not** invent a default profile name.
3. Resolve region from that profile:  
   `REGION=$(aws configure get region --profile "$NEO_AUX_AWS_PROFILE")`  
   If empty → stop and ask user to set `region` on that profile in `~/.aws/config`.
4. Optional: `aws configure get sso_role_name --profile "$NEO_AUX_AWS_PROFILE"` — expect org role **AuxiliaryEsignatureAccess**.

Use `"$NEO_AUX_AWS_PROFILE"` and `"$REGION"` in every aws command below. Shorthand: `$PROFILE` / `$REGION`.

## Procedure
1. Identity map (org SIT — shared team defaults):
- Env: Auxiliary SIT
- AWS account (expect): 290768402609 — confirm live via sts
- EKS cluster: `aux-eks-goqmac0w`
- Preferred kubectl context alias: `aux-neo` (full ARN context may also exist)
- Argo Application namespace: `argocd-app` (majority); rare apps may sit in `argocd`
- Workloads: multi-namespace by domain
- Argo flavor: self-hosted in-cluster (`argocd-server` present). UI: `https://argocd-auxiliary.sit.awesome-poc-th.com`
- Typical RDS cluster id fragment: `rds-aux-goqmac0w`; typical db name: `sit_auxiliary`
2. Connect / heal access (every session):
1) Require `$PROFILE` / `$REGION` per **Local auth** above.
2) `aws sts get-caller-identity --profile "$PROFILE"`. Expect account **290768402609** and role **AuxiliaryEsignatureAccess**. On Forbidden or expired session: `aws sso login --profile "$PROFILE"` (user approves browser).
3) If context missing or API unreachable:  
   `aws eks update-kubeconfig --name aux-eks-goqmac0w --region "$REGION" --profile "$PROFILE" --alias aux-neo`
4) Smoke: `kubectl --context aux-neo get ns` AND `kubectl --context aux-neo get applications -n argocd-app`.  
Always pass `--context aux-neo`.
3. Namespace map (resolve live first via Application destination):
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
Fuzzy search: `kubectl --context aux-neo get deploy,secrets -A` then use the **grep tool** on the output for FRAGMENT (do not `… | rg` in bash).
4. Inspect logs / health (read-only):

**Choose path:**
| Need | Path |
|---|---|
| Last ~15–30m, pod still running | **A. kubectl** |
| Older window / pod rotated / count by `msg` / multi-pod history | **B. OpenSearch** |

**A. kubectl (recent)**
- List pods in NS, then `kubectl --context aux-neo logs -n NS deploy/DEPLOY --since=15m --tail=500`
- Also useful: `--tail=200`, `--previous` on crash
- Recent events in NS; optional top pods
- Running image via deploy jsonpath `containers[0].image`
- Deploy names can differ from Argo app names — list deploy -n NS first.
- **Filter:** use the **grep tool** on command output/temp file. **Never** `kubectl … | rg` or `… | grep` in bash.

**B. OpenSearch (historical)** — shared SIT store; **do not fork the recipe**:
1. Read `skill://neo-core-sit/references/opensearch-sit.md` (canonical measured recipe).
2. Same host/index as Core: `opensearch.sit.awesome-poc-th.com` / `console-sit-log`.
3. Filter `kubernetes_container_name` to the **Aux** container/deploy name (not Core’s `payment` unless that is the target).
4. Sync XHR in browser only; SSO cold-start → ask user to log in; no cookie→curl path unless newly proven.
5. Aux containers are expected on the same index; if zero hits, confirm container name via a live pod before concluding “no logs”.

5. ArgoCD status:
Path A (preferred for agents): kubectl Application CRDs in ns argocd-app. Columns name, destination.namespace, sync, health, revision. One-app jq for sync/rev/health/dest/images/conditions. History via status.history last entries.
Path B (optional CLI/UI): UI at argocd-auxiliary.sit.awesome-poc-th.com with SSO. argocd-server is ClusterIP — port-forward svc/argocd-server -n argocd if CLI needed. Local admin account disabled.
Default read-only. No sync/prune/delete unless user explicitly requests mutate.
6. Postgres settings from K8s secrets (principle: fuzzy-find secret by service name, then read connection fields):
1) `kubectl get secrets -n NS` then grep tool for FRAGMENT. Names may end with -secret or -secrets.
2) Three common layouts (helper handles all): yaml blob (config.yaml/secrets.yaml), discrete POSTGRES_*, discrete DB_*.
3) **Reuse helper (do NOT rewrite ad-hoc Python each time):** resolve relative to this skill dir (parent of `SKILL.md`):
   `scripts/pg-from-secret`
   ```bash
   # SKILL_DIR = directory containing this SKILL.md
   PG="$SKILL_DIR/scripts/pg-from-secret"
   # Aux needs explicit ns + secret (multi-namespace)
   "$PG" --context aux-neo --namespace sms --secret sms-service-secret
   "$PG" --context aux-neo --namespace portal --secret portal-backend-secrets --psql -- \
     -c 'SELECT current_user, current_database();'
   eval "$("$PG" --context aux-neo --namespace sms --secret sms-service-secret --export)"
   ```
4) Manual fallback only if the helper fails.
5) In chat report host/database/user/schema by default; auth field only when user asked to connect.
6) SELECT/describe + LIMIT only; never write/DDL.
7. ExternalSecret drift: get externalsecret -A filtered by FRAGMENT; inspect clustersecretstore/secretstore.
8. Report in Thai, terminal-friendly: identity (account/role from sts; profile from env only); Argo sync/health + image; pod ready/restarts; log snippets with timestamps (and OpenSearch msg counts when used); DB host/db/user/schema by default. Never write decoded credentials into repo files, skill bodies, or durable memory.

## Pitfalls
- Core SIT is a different AWS account/cluster — use `neo-core-sit` + `NEO_CORE_AWS_PROFILE`.
- Missing `NEO_AUX_AWS_PROFILE` → fail fast; never guess a profile name.
- Argo apps mainly in argocd-app; argocd namespace is the control plane.
- Wrong namespace is the top miss — resolve Application destination first.
- Secret name suffix is inconsistent (-secret vs -secrets).
- Three credential layouts (yaml blob / POSTGRES_* / DB_*) — do not assume Core-style config.yaml only.
- argocd-server is ClusterIP; CLI needs port-forward or use UI SSO. Local admin disabled.
- Private RDS — extracted settings do not imply laptop connectivity.
- Read-only by default: no apply/delete/sync/edits unless user asks.
- Never persist decoded credentials into git, skills, or memory.
- OpenSearch: shared recipe under `neo-core-sit`; do not pipe kubectl to `rg`; sync XHR only; ask user on SSO cold start.

## Verification
1. `NEO_AUX_AWS_PROFILE` set; `aws configure get region --profile "$PROFILE"` non-empty.
2. sts get-caller-identity with that profile shows account 290768402609 and AuxiliaryEsignatureAccess.
3. kubectl --context aux-neo get ns lists argocd, argocd-app, and domain namespaces.
4. kubectl --context aux-neo get applications -n argocd-app lists Aux apps.
5. For a named service: destination NS resolved, deploy/logs readable, matching secret yields one of the three Postgres layouts.
6. When using OpenSearch: follow `skill://neo-core-sit/references/opensearch-sit.md`; XHR 200; counts sum to total when aggregating.
