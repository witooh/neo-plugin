---
name: neo-core-sit
description: "Inspects Core SIT logs, managed ArgoCD status, workloads and Postgres settings read-only. Use when debugging Core SIT services such as payment, account, transaction or customer; not for UAT or Auxiliary SIT."
metadata:
  version: "5"
  created: "2026-07-24"
  updated: "2026-10-29"
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
CLUSTER=core-eks-hbq5y8
ARGO_NS=argocd
ARGO_URL=
OS_HOST=https://opensearch.sit.awesome-poc-th.com
OS_INDEX=console-sit-log
OS_VERSION=3.5.0
OS_CLUSTER=core-systems-dev
```

The OpenSearch version is a measured baseline; re-check it when using historical logs.
For a local profile template, use `sit.env.example`; missing `NEO_SIT_CORE_AWS_PROFILE` stops access.
Auxiliary SIT uses `neo-aux-sit`; Core UAT uses `neo-core-uat`.
