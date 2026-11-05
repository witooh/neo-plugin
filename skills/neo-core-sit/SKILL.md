---
name: neo-core-sit
description: "Inspects Core SIT logs, managed ArgoCD status, workloads, Postgres settings and Kafka topics, offsets and payloads read-only, and traces a correlation id across Mobile, Portal, BFF and integration services to a proven root cause. Use when debugging Core SIT services such as payment, account, transaction or customer, when a Mobile or Portal API failure needs diagnosing, or checking whether an event reached Kafka; not for UAT or Auxiliary SIT."
metadata:
  version: "8"
  created: "2026-07-24"
  updated: "2026-11-05"
---
## Core SIT

Read and follow [the shared inspection procedure](references/cluster-inspection.md)
before any AWS, Kubernetes, ArgoCD, DB or Kafka action. Apply these bindings only:

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
OS_HOST=https://opensearch.sit.awesome-poc-th.com
OS_INDEX=console-sit-log
OS_ACCESS_INDEX=access-sit-log
OS_VERSION=3.7.0
OS_CLUSTER=core-systems-dev
SECRET_PREFIX=sit/core
KAFBAT_URL=https://core.sit.awesome-poc-th.com/kafbat-ui
KAFKA_CLUSTER=kafka-sit
KAFKA_BROKER=kafkacoreckrztgxi
```

Values were measured on 2026-11-04 (region `ap-southeast-7`) and the `OS_*` and Kafka bindings on
2026-11-05; re-check them each session.
RDS is `rds-core-ckrztgxi8f-sit`, database `sit_core`. Payroll deploys from the Auxiliary gateway repo,
so use `neo-aux-sit` for it; `sit/core/payroll-service` still names deleted `rds-core-hbq5y8`.

`CoreIntegrationAccess` has an EKS access entry on this cluster, so kubectl reads pods, logs,
Applications and secrets. Its RBAC also allows `create pods`, `delete pods`, `patch deployments` and
`pods/exec`, so only the shared procedure's permission rule keeps a session read-only.

| Need | Path |
|---|---|
| Recent logs, workloads, Argo status | kubectl, shared procedure §4 and §5 |
| Older logs, counts by `msg` | [OpenSearch recipe](references/opensearch.md) |
| Postgres | Secrets Manager recipe in the shared procedure §6; its session rejects writes |
| Kafka topics, offsets, payloads, consumer groups | [Kafka recipe](references/kafka.md); GET only |
| A Mobile or Portal symptom, or a correlation id | [Tracing recipe](references/tracing.md) |

The Postgres helper also works here with `--namespace core-systems --secret <name>`, for the secret a
pod actually mounts. `ARGO_URL` comes from `aws eks describe-capability`; its `/api/v1/applications`
returned 200 in the browser session. Fluent-bit writes to `os.sit`, but search only through `OS_HOST`:
the OpenSearch recipe explains why.

Applications sync `overlays/sit` from `main` of `libero-engineering/api-gateway/kong-gateway-coresystems`.
The repo's root `argocd/*-dev.yaml` and `overlays/dev` belong to the deleted old cluster, so ignore them.

`core.sit.awesome-poc-th.com` resolves on the laptop only through the system resolver
(`dscacheutil -q host -a name`; `dig` returned nothing), and its addresses matched `kong-kong-proxy` on
2026-11-05. Before treating a response from it as evidence about this cluster, compare its address with
`kubectl --context "$CTX" get svc kong-kong-proxy -n kong`, which gives an NLB hostname to resolve the same way.

### Old SIT

Old SIT no longer exists: `core-eks-hbq5y8` returns `ResourceNotFoundException` and `rds-core-hbq5y8` is
no longer listed (2026-11-04). When the user names it, say so and offer the bindings above. Its
`old-sit/*` secrets remain in Secrets Manager; do not use them.

For a local profile template, use `sit.env.example`; missing `NEO_SIT_CORE_AWS_PROFILE` stops access.
Auxiliary SIT uses `neo-aux-sit`; Core UAT uses `neo-core-uat`.
