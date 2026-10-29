---
name: neo-core-uat
description: "Inspects Core UAT logs, ArgoCD status, workloads and Postgres settings read-only. Use when debugging Core UAT services such as payment, account, transaction or customer; not for SIT or Auxiliary UAT."
metadata:
  version: "2"
  created: "2026-10-22"
  updated: "2026-10-29"
---
## Core UAT

Read and follow [the shared inspection procedure](../neo-core-sit/references/cluster-inspection.md)
before any AWS, Kubernetes, ArgoCD or DB action, then [the UAT access notes](references/uat-access.md)
for where UAT differs from SIT. Apply these bindings only:

```bash
ENVIRONMENT=UAT
DOMAIN=core
PROFILE_ENV=NEO_UAT_CORE_AWS_PROFILE
CTX=core-neo-uat
EXPECTED_ACCOUNT=915848750617
EXPECTED_ROLE=UserAcceptanceTestingAccess
CLUSTER=core-eks-yblzrf0dwv-uat
ARGO_NS=argocd-app
ARGO_URL=https://argocd-fcfc3742-915848750617.eks-capabilities.ap-southeast-7.amazonaws.com
OS_HOST=https://opensearch.uat.awesome-poc-th.com
OS_INDEX=console-uat-log
OS_VERSION=3.7.0
OS_CLUSTER=core-systems-uat
PG_HOST=rds-core-yblzrf0dwv-uat.cluster-cfwam2uocaxb.ap-southeast-7.rds.amazonaws.com
PG_PORT=5432
PG_DB=uat_core
PG_USER=developer
```

`CTX` is the local alias to create for the verified UAT cluster, not a claim that it already exists.
Values were measured on 2026-10-29 (region `ap-southeast-7`); re-check them each session.
`UserAcceptanceTestingAccess` has no EKS access entry on this cluster, so kubectl and secrets stay
blocked until one exists; Postgres uses an RDS IAM token instead (UAT access notes).
Search logs in OpenSearch first, any window; use Argo for
status, images and pods, and for logs only as the UAT access notes' fallback.
Never substitute Core SIT values.
For a local profile template, use `uat.env.example`; missing `NEO_UAT_CORE_AWS_PROFILE` stops access.
Auxiliary UAT uses `neo-aux-uat`; Core SIT uses `neo-core-sit`.
