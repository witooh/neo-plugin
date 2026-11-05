---
name: neo-aux-sit
description: "Inspects Auxiliary SIT logs, ArgoCD status, workloads and Postgres settings read-only. Use when debugging Auxiliary SIT services such as sms, email, portal, ekyc, consent or special-list; not for UAT or Core SIT."
metadata:
  version: "7"
  created: "2026-07-24"
  updated: "2026-11-05"
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
OS_VERSION=3.7.0
OS_CLUSTER=auxiliary-systems-dev
SECRET_PREFIX=sit/aux
```

Values were measured on 2026-11-04 (region `ap-southeast-7`) and the `OS_*` bindings on 2026-11-05;
re-check them each session.
RDS is `rds-aux-ckrztgxi8f-sit`, database `sit_auxiliary`.
Workspace repos use their directory name in Secrets Manager, such as `sit/aux/consent-service`. This
covers consent, e-document, fraud, mobile-setting, payroll, qr and tc. Payroll deploys from this
domain's gateway repo, so use this skill for it, not `neo-core-sit`.
`ARGO_URL` comes from `aws eks describe-capability`; its `/api/v1/applications` returned 200 in the
browser session.
`AuxiliaryEsignatureAccess` has no EKS access entry on this cluster, so kubectl and Kubernetes secrets
stay blocked until one exists (`aws eks list-access-entries`). Use these paths instead:

| Need | Path |
|---|---|
| Postgres | Secrets Manager recipe in the shared procedure §6 |
| Logs, live pods | Argo REST `/logs` in the browser session ([recipe](../neo-core-uat/references/uat-access.md)) |
| Logs, older window or rotated pods, counts | [OpenSearch recipe](../neo-core-sit/references/opensearch.md) |
| Argo status, images, pods, ExternalSecrets | Argo REST in the browser session (same recipe) |

Add `appNamespace=argocd-app` to every Argo GET. Applications sync `overlays/sit` from `main` of
`libero-engineering/api-gateway/kong-gateway-auxiliarysystems`; the repo has no `overlays/dev` any more.

This cluster's logs reach `OS_HOST` from 2026-11-04T08:08Z; nothing older is there. Its node group stops
at 23:00 and starts at 08:00 Bangkok time (`daily-stop-cluster`, `daily-start-cluster`), so expect no logs
in that window.

`auxiliary.sit.awesome-poc-th.com` did not resolve from the laptop on 2026-11-04, and its target was not
measured, so a response from that hostname is not evidence about this cluster.

### Old SIT

Old SIT no longer exists: `aux-eks-goqmac0w` returns `ResourceNotFoundException` and `rds-aux-goqmac0w` is
no longer listed (2026-11-04). When the user names it, say so and offer the bindings above.
`sit/aux-systems/*` belongs to old SIT despite its name and remains in Secrets Manager, so do not use it;
the `kong-gateway-auxiliarysystems` steering still documents it as current.

For a local profile template, use `sit.env.example`; missing `NEO_SIT_AUX_AWS_PROFILE` stops access.
Core SIT uses `neo-core-sit`; Auxiliary UAT uses `neo-aux-uat`.
