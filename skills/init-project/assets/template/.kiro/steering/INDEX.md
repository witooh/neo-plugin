---
inclusion: always
---

# Steering Index

This index lists every steering guide and the `inclusion` declared in its YAML
frontmatter. Keep it in sync when adding, removing, or changing a guide.

## Required reading

At the start of every session, read every guide marked `always` in the table
below before doing any work. This index is already loaded; currently, read
`structure.md` next.

| Guide | `inclusion` | `fileMatchPattern` |
|---|---|---|
| `INDEX.md` | `always` | — |
| `structure.md` | `always` | — |
| `app.md` | `fileMatch` | `**/cmd/api/**,**/config/**` |
| `bruno.md` | `fileMatch` | `**/bruno/**` |
| `domain.md` | `fileMatch` | `**/internal/core/domain/**` |
| `e2e.md` | `fileMatch` | `**/tests/**,**/mockoon/**` |
| `handler.md` | `fileMatch` | `**/internal/delivery/http/**` |
| `integration.md` | `fileMatch` | `**/internal/core/domain/integration/**,**/internal/adapters/gateway/**,**/internal/adapters/repository/cache/**` |
| `messaging.md` | `fileMatch` | `**/internal/delivery/consumer/**,**/internal/adapters/eventbus/**,**/pkg/messaging/**` |
| `repository.md` | `fileMatch` | `**/internal/adapters/repository/**,**/*.sql,sqlc.yaml` |
| `testing.md` | `fileMatch` | `**/*_test.go` |
| `tooling.md` | `fileMatch` | `Makefile,tools/**,.mockery.yaml,.golangci.yaml,.golangci.yml,Dockerfile,docker-compose*.yaml` |
| `usecase.md` | `fileMatch` | `**/internal/core/usecase/**` |
| `new-feature-checklist.md` | `manual` | — |
| `repo-instance.md` | `manual` | — |
