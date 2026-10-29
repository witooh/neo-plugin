# UAT access surface (measured 2026-10-29)

Shared by `neo-core-uat` and `neo-aux-uat`; owned by `neo-core-uat`. The shared
[inspection procedure](../../neo-core-sit/references/cluster-inspection.md) still governs every step.
This file records where UAT measurably differs from SIT. Re-check a value before relying on it;
SIT measurements are not UAT evidence.

## Access paths (Core and Aux UAT)

| Need | Path | Status |
|---|---|---|
| STS, EKS describe, capabilities | AWS CLI with the wrapper's profile env | works |
| Pods, logs, secrets, Application CRDs | `kubectl --context core-neo-uat` / `aux-neo-uat` | **blocked**: role has no access entry |
| Logs, any window (recent included), counts | OpenSearch Dashboards in the browser session | **primary** |
| Argo status, images, pods | Argo REST API in the browser session | works |
| Logs for a namespace OpenSearch does not hold | Argo pod logs (live pods only) | fallback |
| Postgres | RDS IAM token + `psql` with the wrapper's `PG_*` bindings | works |

Browser calls run as the user's SSO session in Chrome, not the CLI role; which user it is was not
verified. UAT is read-only with no exception (shared procedure, Permission): browser calls are GET
or search only, even when the user asks for an action.

## kubectl is blocked for `UserAcceptanceTestingAccess`

Both UAT clusters use `authenticationMode: API`. Their access entries cover the SSO roles
`AdministratorAccess` and `PowerUserAccess` plus service/node roles, not
`UserAcceptanceTestingAccess`. After a fresh `update-kubeconfig`, kubectl fails with:

```text
error: You must be logged in to the server (the server has asked for the client to provide credentials)
```

`aws eks get-token` still succeeds, so this is not expired SSO: do not log in again or retry.
Check whether it still applies:

```bash
aws eks list-access-entries --cluster-name "$CLUSTER" --profile "$PROFILE" --region "$REGION"
```

If `…/AWSReservedSSO_UserAcceptanceTestingAccess_*` is listed, use kubectl per the shared procedure.
If not, use the browser paths below; adding an access entry is a platform change, never attempted.

## Postgres (RDS IAM auth, not Kubernetes secrets)

UAT databases take a 15-minute IAM token as the password; the secret helper is not used. Generate
the token inline for each command so it is never printed or stored:

```bash
PGPASSWORD="$(aws rds generate-db-auth-token --hostname "$PG_HOST" --port "$PG_PORT" \
  --username "$PG_USER" --profile "$PROFILE" --region "$REGION")" \
psql "host=$PG_HOST port=$PG_PORT dbname=$PG_DB user=$PG_USER sslmode=require options='-c default_transaction_read_only=on'" \
  -X -c 'SELECT current_user, current_database();'
```

- `default_transaction_read_only=on` makes the session reject writes; `SHOW transaction_read_only`
  returned `on` on both clusters (2026-10-29). Keep it in every connection you open; never turn it
  off (`SET … off`, `BEGIN READ WRITE`).

- Measured from this laptop on 2026-10-29: both clusters accepted the token (Aurora PostgreSQL
  18.6 Core, 18.4 Aux). `sslmode=require` is mandatory.
- Users are `developer` and `qa`. `developer` is not a superuser and is a member of
  `pg_read_all_data` and `rds_iam`; other grants were not checked. The SELECT-only rule still holds.
- `describe-db-clusters` reports Core `DatabaseName: sit_core`, but no such database exists; use
  `uat_core`. The `cluster-ro-…` reader endpoints were not tested.
- One schema per service, e.g. `product-service` → `product` in `uat_core`. List schemas live with
  `SELECT nspname FROM pg_namespace`.
- For a person using DBeaver: pipe the token to `pbcopy`, paste it as the password, set SSL mode
  `require`, and leave "Save password" off.

## Managed ArgoCD (EKS capability)

Re-check the URL and namespace read-only:

```bash
aws eks describe-capability --cluster-name "$CLUSTER" --capability-name argocd \
  --profile "$PROFILE" --region "$REGION"
```

`configuration.argoCd.serverUrl` is `ARGO_URL`; `configuration.argoCd.namespace` is `ARGO_NS`.
Login is AWS IdC in the browser (`/auth/login` redirects to `signin.aws`). Without a session the API
returns `no session information`. If the tab shows the IdC sign-in, ask the user to log in.
Core and Aux Argo are separate origins; each needs its own login.

In an authenticated Argo tab, run same-origin GETs; add `appNamespace=<ARGO_NS>` to each
(`argocd-app` on both UAT clusters; join with `&` when the path already has `?`):

| Need | GET |
|---|---|
| Apps, destination, sync/health | `/api/v1/applications` |
| Source, sync revision, history, summary images | `/api/v1/applications/<app>` |
| Deployments / ReplicaSets / Pods with images and restarts | `/api/v1/applications/<app>/resource-tree` |
| Pod `containerStatuses` / `lastState` | `/api/v1/applications/<app>/resource?namespace=<ns>&resourceName=<pod>&version=v1&kind=Pod&group=` |
| Live pod logs | `/api/v1/applications/<app>/logs?namespace=<ns>&podName=<pod>&container=<c>&follow=false&tailLines=<n>` |

Logs accept `sinceSeconds=<s>` and `previous=true`. The body is NDJSON of `{"result":{…}}`; the last
line has `last: true` and empty `content`. On UAT, search logs in OpenSearch first, for recent
windows too: it is faster and also holds rotated ReplicaSets and `previous` crashes. Use Argo logs
only when the namespace is missing from the index (see coverage below); they cover only pods that
still exist (plus `previous`).

Measured mapping: every Core service Application targets `core-systems`. `payment-service` owns
Deployments `payment` and `payment-pcc`, both running the same `…/core/payment-gateway:<tag>`
image (same digest when measured).
The Core UAT Argo lists no Auxiliary service Applications.

## OpenSearch (Core and Aux UAT share one index)

Follow [the OpenSearch recipe](../../neo-core-sit/references/opensearch.md) with these values:

| | |
|---|---|
| Host | `https://opensearch.uat.awesome-poc-th.com` |
| Dashboards | `3.7.0` (`GET /_dashboards/api/status`) |
| Index | alias `console-uat-log` over `console-uat-log.YYYY.MM.DD-NNNNNN`; earliest 2026.10.15 when measured |
| Index-pattern id | `a0ec61a0-c3e1-11f1-bd92-bf9c10c36336` (time field `@timestamp`) |
| Environment filter | `cluster_name.keyword`: `core-systems-uat` or `auxiliary-systems-uat` |
| Other patterns | `access-uat-log`, `audit-uat-log` (contents not inspected); Dashboards `defaultIndex` is `console-uat-log` |

- Always filter on `cluster_name.keyword` (`OS_CLUSTER`): namespace `kong` exists in both clusters.
- Core coverage: `core-systems` and `kong` only. Aux coverage is partial (see Auxiliary UAT below).
- The mapping matches SIT (`.keyword` metadata fields), so the recipe's exact `term` filters and
  name-resolving aggregation apply unchanged. On UAT, `match_phrase` `payment` also matched
  `payment-pcc` (460 vs 416 exact).
- `search_after` paging with the recipe's `_id` tiebreaker was checked on UAT: 5 pages returned
  416 unique hits, equal to `hits.total`.

Core `http.server.request.completed` lines carry the full `requestBody`, including account numbers;
keep `requestBody` out of reports.

## Browser note (Claude in Chrome)

The extension can mask values in tool output as `[BLOCKED: …]` (seen on git SHAs, paths and the
Dashboards version). The request itself succeeded; it is not an API error. Keep such a value in a
variable (for example the version for `osd-version`) instead of printing it.

## Auxiliary UAT

- Account `neo-n010` (`359005010511`) holds only `aux-eks-yblzrf0dwv-uat` (stack `UatAuxEksCluster`),
  with the same managed Argo capability shape as Core. Its SSO session uses start URL
  `https://identitycenter.amazonaws.com/ssoins-8210f485c132201c`.
- Account `915848750617` (Core UAT) holds only `core-eks-yblzrf0dwv-uat` and
  `data-hub-eks-yblzrf0dwv-uat`; a profile that resolves there is not an Aux UAT profile.
- Argo: 59 Applications in `argocd-app`. Destinations name the cluster ARN plus namespace, not
  `in-cluster`. The Auxiliary SIT namespace hints hold, except for these:
  - `datamart-external-service`, `special-list-external-service` and `statement-service` deploy
    to `los-credit-card`.
  - `crypto-service` deploys to `ndid-interface`.
  - Namespaces that SIT lacks: `branch-device`, `fraud`, `mobile-setting`, `qr`.
- OpenSearch covers only some Aux namespaces: `kong`, `portal`, `special-list`, `consent`, `ekyc`,
  `email` and `e-signature`, from 2026-10-20. `sms` had live pod logs in Argo yet 0 documents in the
  index. For any other namespace, zero hits does not mean no logs: read pod logs through Argo
  (live pods only). The cause was not investigated.
