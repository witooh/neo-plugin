---
inclusion: fileMatch
fileMatchPattern: "**/internal/core/domain/integration/**,**/internal/adapters/gateway/**,**/internal/adapters/repository/cache/**"
---

# Driven Ports & Outbound Gateways

The two halves of every outbound dependency:

- **Define the port** in the domain context that consumes it — for an external system that
  is `internal/core/domain/integration/<sys>/gateway.go` (the contract the core requires).
- **Implement it** in `internal/adapters/gateway/<sys>` (external HTTP services) or
  `internal/adapters/repository/cache` (cache) — the adapter that speaks to the real system.

The usecase depends on the port interface; the composition root injects the adapter.
Adapters never import each other.

## Driven port — `internal/core/domain/integration/<sys>/gateway.go`

Interface **plus its data contracts** (request/response structs + read-models). No wire
parsing, no business logic — contracts only. The package is the system name (`package <sys>`).
One `gateway.go` per upstream (read-models may move to a sibling
`readmodels.go`, see `domain.md`).

```go
// Package <sys> is the read-only integration context for the <Upstream> system: it holds the
// driven (outbound) port the core requires plus its data contracts. Interfaces + data only.
package <sys>   // e.g. product

type <Upstream>CreateInput struct  { /* exported fields, json tags for the adapter */ }
type <Upstream>CreateResponse struct { /* ... */ }

type <Upstream> interface {
	Create(ctx context.Context, input <Upstream>CreateInput) (*<Upstream>CreateResponse, error)
}
```

Keep ports **narrow**. If only one operation needs a method, prefer a narrow interface
declared at that usecase (see `usecase.md` ISP note) over widening the shared port.

## Gateway adapter — `internal/adapters/gateway/<sys>/http/`

```
adapters/gateway/<sys>/
    http/
        adapter.go        # Config + unexported adapter struct + NewHTTPAdapter → <sys>.<Upstream>
        <operation>.go    # one file per method body (request build → call → map)
        *_dto.go          # upstream wire DTOs + mapping to integration/domain types
    domain/
        errors.go         # sentinel-error translation for this upstream
```

```go
// Package http implements the <Upstream> port against the live <Upstream> REST API.
package http

import <sys> "{{MODULE_PATH}}/internal/core/domain/integration/<sys>"   // the port it implements

type Config struct {
	BaseURL   string
	AuthToken string
	Timeout   time.Duration
}

type httpAdapter struct {        // unexported — only the port interface escapes
	client    *stdhttp.Client
	baseURL   string
	authToken string
}

// NewHTTPAdapter returns the port interface, not the concrete adapter.
func NewHTTPAdapter(cfg Config) <sys>.<Upstream> {
	timeout := cfg.Timeout
	if timeout <= 0 {
		timeout = defaultTimeout
	}
	return &httpAdapter{client: &stdhttp.Client{Timeout: timeout}, baseURL: cfg.BaseURL, authToken: cfg.AuthToken}
}
```

Method bodies (in `<operation>.go`):
1. Build the upstream request from the port input.
2. Call; cap the response body (`io.LimitReader`, e.g. `1<<20`).
3. Decode the upstream DTO, **map it to the `integration/<sys>` type** — never leak the wire DTO outward.
4. Translate failures into **typed errors** (the adapter's own `domain` package,
   `adapters/gateway/<sys>/domain`): not-found → a swallow-able "no data" the caller maps to
   empty; transport / 5xx / malformed → unavailable; timeout → timeout. The edge mapper turns
   these into 503/504/etc.

## Cache adapter — `internal/adapters/repository/cache`

The `Cache` port lives in the centralized `repository` package —
`internal/core/domain/repository/cache.go` (`repository.Cache`). Same adapter shape: the constructor
returns that port. The cache adapter wraps the low-level Redis client in
`internal/adapters/repository/redis`.

```go
import "{{MODULE_PATH}}/internal/core/domain/repository"

func NewCache(client *redis.Client) repository.Cache { /* ... */ }
```

## Fakes for tests

Provide an in-memory / stub implementation of the same port for unit and e2e tests
(deterministic, sentinel IDs). It implements `<sys>.<Upstream>` structurally, so it drops
into `Params` wherever the real adapter does. See `testing.md`.

## Don'ts

- ✗ Business logic in an adapter — only protocol + mapping + error translation.
- ✗ Returning the concrete struct from the constructor — return the port (`<sys>.<Upstream>`).
- ✗ Leaking upstream wire DTOs past the adapter boundary.
- ✗ Importing a usecase, a handler, or another adapter.
