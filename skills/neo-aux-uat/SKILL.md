---
name: neo-aux-uat
description: "Inspects Auxiliary UAT logs, ArgoCD status, workloads and Postgres settings read-only. Use when debugging Auxiliary UAT services such as sms, email, portal, ekyc, consent or special-list; not for SIT or Core UAT."
metadata:
  version: "2"
  created: "2026-10-22"
  updated: "2026-10-29"
---
## Auxiliary UAT

Read and follow [the shared inspection procedure](../neo-core-sit/references/cluster-inspection.md)
before any AWS, Kubernetes, ArgoCD or DB action, then [the UAT access notes](../neo-core-uat/references/uat-access.md)
for where UAT differs from SIT. Apply these bindings only:

```bash
ENVIRONMENT=UAT
DOMAIN=aux
PROFILE_ENV=NEO_UAT_AUX_AWS_PROFILE
CTX=aux-neo-uat
EXPECTED_ACCOUNT=359005010511
EXPECTED_ROLE=UserAcceptanceTestingAccess
CLUSTER=aux-eks-yblzrf0dwv-uat
ARGO_NS=argocd-app
ARGO_URL=https://argocd-47121cbe-359005010511.eks-capabilities.ap-southeast-7.amazonaws.com
OS_HOST=https://opensearch.uat.awesome-poc-th.com
OS_INDEX=console-uat-log
OS_VERSION=3.7.0
OS_CLUSTER=auxiliary-systems-uat
PG_HOST=rds-aux-yblzrf0dwv-uat.cluster-crymwug4o207.ap-southeast-7.rds.amazonaws.com
PG_PORT=5432
PG_DB=uat_auxiliary
PG_USER=developer
```

`CTX` is the local alias to create for the verified UAT cluster, not a claim that it already exists.
Values were measured on 2026-10-29 (region `ap-southeast-7`; OpenSearch is shared with Core UAT);
re-check them each session. As on Core UAT, `UserAcceptanceTestingAccess` has no EKS access entry,
so kubectl and secrets stay blocked until one exists; Postgres uses an RDS IAM token instead.
Search logs in OpenSearch first, any window; use Argo for status, images and pods, and for logs
only as the UAT access notes' fallback.
Never substitute Auxiliary SIT or Core UAT values.
For a local profile template, use this skill's `uat.env.example`; missing `NEO_UAT_AUX_AWS_PROFILE`
stops AWS, kubectl and DB access. Logs via OpenSearch need only the browser session, but the index
holds only some Aux namespaces; check coverage in the UAT access notes before trusting zero hits.
Core UAT uses `neo-core-uat`; Auxiliary SIT uses `neo-aux-sit`.
