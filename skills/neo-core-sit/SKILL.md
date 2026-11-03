---
name: neo-core-sit
description: "Inspects Core SIT logs, managed ArgoCD status, workloads and Postgres settings read-only. Use when debugging Core SIT services such as payment, account, transaction or customer; not for UAT or Auxiliary SIT."
metadata:
  version: "6"
  created: "2026-07-24"
  updated: "2026-11-03"
---
## Core SIT

Read and follow [the shared inspection procedure](references/cluster-inspection.md)
before any AWS, Kubernetes, ArgoCD or DB action. Apply these bindings only:

```bash
ENVIRONMENT=SIT
DOMAIN=core
PROFILE_ENV=NEO_SIT_CORE_AWS_PROFILE
CTX=core-neo
EXPECTED_ACCOUNT=986629373331
EXPECTED_ROLE=CoreIntegrationAccess
CLUSTER=core-eks-ckrztgxi8f-sit
ARGO_NS=argocd-app
ARGO_URL=https://argocd-8e7fb933-986629373331.eks-capabilities.ap-southeast-7.amazonaws.com
OS_HOST=https://os.sit.awesome-poc-th.com
OS_INDEX=console-sit-log
OS_VERSION=3.7.0
OS_CLUSTER=core-systems-dev
SECRET_PREFIX=sit/core
```

Values were measured on 2026-11-03 (region `ap-southeast-7`); re-check them each session.
RDS is `rds-core-ckrztgxi8f-sit`, database `sit_core`. Payroll deploys from the Auxiliary gateway repo,
so use `neo-aux-sit` for it; `sit/core/payroll-service` still names old `rds-core-hbq5y8`.
`OS_INDEX` and `OS_CLUSTER` come from the `sit` fluent-bit overlay and were not searched on this host;
`ARGO_URL` comes from `aws eks describe-capability` and its login was not tried.
`CoreIntegrationAccess` has no EKS access entry on this cluster, so kubectl and Kubernetes secrets stay
blocked until one exists (`aws eks list-access-entries`). Use these paths instead:

| Need | Path |
|---|---|
| Postgres | Secrets Manager recipe in the shared procedure §6 |
| Logs, any window | [OpenSearch recipe](references/opensearch.md) |
| Argo status, images, pods | Argo REST in the browser session ([recipe](../neo-core-uat/references/uat-access.md)) |

`core.sit.awesome-poc-th.com` still resolved to the old SIT's Kong on 2026-11-03, so a response from
that hostname is not evidence about this cluster.

### Old SIT

A plain "SIT" request means the bindings above. Apply these overrides only when the user names old SIT:

```bash
CTX=core-neo-old-sit
CLUSTER=core-eks-hbq5y8
ARGO_NS=argocd
ARGO_URL=
OS_HOST=https://opensearch.sit.awesome-poc-th.com
OS_VERSION=3.5.0
SECRET_PREFIX=
```

kubectl works there, and Postgres comes from the Kubernetes secret. Its ExternalSecrets read
`old-sit/neocore/<service>` and its database is `rds-core-hbq5y8`. Re-check `OS_VERSION` before a
historical search.

For a local profile template, use `sit.env.example`; missing `NEO_SIT_CORE_AWS_PROFILE` stops access.
Auxiliary SIT uses `neo-aux-sit`; Core UAT uses `neo-core-uat`.
