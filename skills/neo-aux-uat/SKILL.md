---
name: neo-aux-uat
description: "Inspects Auxiliary UAT logs, ArgoCD status, workloads and Postgres settings read-only. Use when debugging Auxiliary UAT services such as sms, email, portal, ekyc, consent or special-list; not for SIT or Core UAT."
metadata:
  version: "1"
  created: "2026-10-22"
  updated: "2026-10-22"
---
## Auxiliary UAT

Read and follow [the shared inspection procedure](../neo-core-sit/references/cluster-inspection.md)
before any AWS, Kubernetes, ArgoCD or DB action. Apply these bindings only:

```bash
ENVIRONMENT=UAT
DOMAIN=aux
PROFILE_ENV=NEO_UAT_AUX_AWS_PROFILE
CTX=aux-neo-uat
EXPECTED_ACCOUNT=
EXPECTED_ROLE=
CLUSTER=
ARGO_NS=
ARGO_URL=
OS_HOST=
OS_INDEX=
OS_VERSION=
```

`CTX` is the local alias to create for the verified UAT cluster, not a claim that it already exists.
Resolve account/role/cluster, Application destination and OpenSearch settings through the shared
procedure. No UAT infrastructure values are assumed; never substitute Auxiliary SIT values.
For a local profile template, use `uat.env.example`; missing `NEO_UAT_AUX_AWS_PROFILE` stops access.
Core UAT uses `neo-core-uat`; Auxiliary SIT uses `neo-aux-sit`.
