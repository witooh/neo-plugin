---
name: neo-aux-sit
description: "Inspects Auxiliary SIT logs, ArgoCD status, workloads and Postgres settings read-only. Use when debugging Auxiliary SIT services such as sms, email, portal, ekyc, consent or special-list; not for UAT or Core SIT."
metadata:
  version: "6"
  created: "2026-07-24"
  updated: "2026-11-03"
---
## Auxiliary SIT

Read and follow [the shared inspection procedure](../neo-core-sit/references/cluster-inspection.md)
before any AWS, Kubernetes, ArgoCD or DB action. Apply these bindings only:

```bash
ENVIRONMENT=SIT
DOMAIN=aux
PROFILE_ENV=NEO_SIT_AUX_AWS_PROFILE
CTX=aux-neo
EXPECTED_ACCOUNT=290768402609
EXPECTED_ROLE=AuxiliaryEsignatureAccess
CLUSTER=aux-eks-ckrztgxi8f-sit
ARGO_NS=argocd-app
ARGO_URL=https://argocd-b7117fac-290768402609.eks-capabilities.ap-southeast-7.amazonaws.com
OS_HOST=https://opensearch.sit.awesome-poc-th.com
OS_INDEX=console-sit-log
OS_VERSION=3.5.0
OS_CLUSTER=auxiliary-systems-dev
SECRET_PREFIX=sit/aux
```

Values were measured on 2026-11-03 (region `ap-southeast-7`); re-check them each session.
RDS is `rds-aux-ckrztgxi8f-sit`, database `sit_auxiliary`.
Workspace repos use their directory name in Secrets Manager, such as `sit/aux/consent-service`. This
covers consent, e-document, fraud, mobile-setting, payroll, qr and tc. Payroll deploys from this
domain's gateway repo, so use this skill for it, not `neo-core-sit`.
`ARGO_URL` comes from `aws eks describe-capability` and its login was not tried.
`AuxiliaryEsignatureAccess` has no EKS access entry on this cluster, so kubectl and Kubernetes secrets
stay blocked until one exists (`aws eks list-access-entries`). Use these paths instead:

| Need | Path |
|---|---|
| Postgres | Secrets Manager recipe in the shared procedure §6 |
| Logs, any window | [OpenSearch recipe](../neo-core-sit/references/opensearch.md), with the caveat below |
| Argo status, images, pods | Argo REST in the browser session ([recipe](../neo-core-uat/references/uat-access.md)) |

The `sit` fluent-bit overlay ships to `opensearch.sit` with the same `cluster.name` as old SIT, so
`cluster_name` cannot separate the two, and whether this cluster's logs arrive was not measured.
Treat a hit as possibly old SIT and zero hits as unproven.

`auxiliary.sit.awesome-poc-th.com` and `argocd-auxiliary.sit.awesome-poc-th.com` still resolved to old
SIT's VPC on 2026-11-03, so a response from those hostnames is not evidence about this cluster.

### Old SIT

A plain "SIT" request means the bindings above. Apply these overrides only when the user names old SIT:

```bash
CTX=aux-neo-old-sit
CLUSTER=aux-eks-goqmac0w
ARGO_URL=https://argocd-auxiliary.sit.awesome-poc-th.com
SECRET_PREFIX=
```

kubectl works there, and Postgres comes from the Kubernetes secret. Its ExternalSecrets read
`sit/aux-systems/<service>` and its database is `rds-aux-goqmac0w`. `sit/aux-systems/*` belongs to old
SIT despite its name; the `kong-gateway-auxiliarysystems` steering still documents it as current.

For a local profile template, use `sit.env.example`; missing `NEO_SIT_AUX_AWS_PROFILE` stops access.
Core SIT uses `neo-core-sit`; Auxiliary UAT uses `neo-aux-uat`.
