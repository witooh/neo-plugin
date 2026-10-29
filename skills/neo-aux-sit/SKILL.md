---
name: neo-aux-sit
description: "Inspects Auxiliary SIT logs, self-hosted ArgoCD status, workloads and Postgres settings read-only. Use when debugging Auxiliary SIT services such as sms, email, portal, ekyc, consent or special-list; not for UAT or Core SIT."
metadata:
  version: "5"
  created: "2026-07-24"
  updated: "2026-10-29"
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
CLUSTER=aux-eks-goqmac0w
ARGO_NS=argocd-app
ARGO_URL=https://argocd-auxiliary.sit.awesome-poc-th.com
OS_HOST=https://opensearch.sit.awesome-poc-th.com
OS_INDEX=console-sit-log
OS_VERSION=3.5.0
OS_CLUSTER=auxiliary-systems-dev
```

SIT RDS hints: cluster fragment `rds-aux-goqmac0w`, database `sit_auxiliary`; resolve actual
settings from the service secret. The OpenSearch version is a measured baseline; re-check it.
For a local profile template, use `sit.env.example`; missing `NEO_SIT_AUX_AWS_PROFILE` stops access.
Core SIT uses `neo-core-sit`; Auxiliary UAT uses `neo-aux-uat`.
