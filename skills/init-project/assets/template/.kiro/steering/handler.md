---
inclusion: fileMatch
fileMatchPattern: "**/internal/delivery/http/**"
---

# HTTP Delivery Layer (inbound adapter)

The HTTP delivery layer translates HTTP ↔ usecase calls (gin). It depends on usecase
**interfaces** (`<Op>Usecase`) and owns only transport concerns: bind/validate the request,
map to/from DTOs, delegate to `Exec`, shape the response. **No business logic.**

```
internal/delivery/http/
    handler/<resource>/
        handler.go        # Handler struct + New() ONLY — no methods
        <operation>.go    # ONE file per operation: the gin method only (DTOs + mappers live in dto/)
        shared/error.go   # cross-handler edge helpers (validation-error translation)
    dto/
        <resource>.go     # request + response DTOs (resource-prefixed) + their mappers (To*/New<Resource>Response)
        shared.go         # response-mapper helpers (e.g. decimalToFloat)
    middleware/
        middleware.go     # Setup(r, serviceID): the standard chain, wrapping common-lib
    router/
        router.go         # Handlers struct + New(h, serviceID) *gin.Engine — gin + middleware + health + groups
        <resource>.go     # register<Resource>(r gin.IRoutes, h *<resource>.Handler)
```

**One operation = one file.** A handler with N endpoints is N+1 files (`handler.go` + one
per op), so two people adding different endpoints never touch the same file. The operation
file holds only the gin method; its request/response DTOs and its request→domain mapper live
together in `dto/<resource>.go`.

## `handler.go` — struct + constructor only

```go
// Package <resource> contains the HTTP handlers for the <Resource> endpoints.
package <resource>

// Handler holds one usecase-interface field per endpoint it fronts.
type Handler struct {
	GetUC  get_order.GetOrderUsecase
	ListUC list_orders.ListOrdersUsecase
}

// New builds the <resource> handler.
func New(getUC get_order.GetOrderUsecase, listUC list_orders.ListOrdersUsecase) *Handler {
	return &Handler{GetUC: getUC, ListUC: listUC}
}
```

### ⚠️ Field name vs method name collision

A struct field and a method with the **same name** is a compile error. The endpoint method
is `<Op>` (`Get`, `List`), so the usecase field takes a **`UC` suffix** (`GetUC`, `ListUC`,
`BatchReserveUC`). A single-usecase handler whose method name differs from the field may
keep `Usecase`.

## `<operation>.go` — one endpoint per file

Holds the gin method. The request DTO (`dto.<Resource><Op>Request`, with `binding` tags) and
its request→domain mapper both live in `dto/`; the method binds the request, delegates, then
shapes the response via `dto.New<Resource>Response`.

> **Domain imports.** The per-layer domain packages (`entity`, `repository`, `event`, `service`,
> root `domain`) have distinct names, so a handler/dto package imports them plain — no alias
> needed. Only integration packages (`integration/<sys>`, `package <sys>`) can still collide with a
> handler name; alias those (e.g. `dm<sys>`) where the clash is real. (This repo's actual
> aliases: `repo-instance.md`.)

```go
package <resource>

// <Op> reads the path/query, binds the request DTO, delegates to the usecase (passing c as
// ctx), pushes any typed error for the middleware to map to a status, then wraps the success
// payload in the standard envelope.
func (h *Handler) <Op>(c *gin.Context) {
	id := c.Param("id")
	var req dto.<Resource><Op>Request
	if err := c.ShouldBindJSON(&req); err != nil {
		c.Error(shared.HandleValidationError(err))
		return
	}
	result, err := h.<Op>UC.Exec(c, id, req.ToDomain())
	if err != nil {
		c.Error(err)
		return
	}
	serviceID, _ := ctxutils.GetServiceId(c)
	c.JSON(http.StatusOK, stdresp.StandardResponse[dto.<Resource>Response]{
		Status: stdresp.SUCCESS_STATUS, ServiceID: serviceID,
		Message: "<op> successfully", Data: dto.New<Resource>Response(result),
	})
}
```

## `dto/` — request + response DTOs (centralised, resource-prefixed)

Both request and response DTOs live in the `dto` package, one file per resource, with the
request and response for the same operation kept together. Because the package is shared,
**type names are resource-prefixed** to avoid collisions (`AccountCreateRequest`,
`AccountResponse`, `AccountListResponse`).

**DTO fields are primitive/wire types only** (`string`, `bool`, numbers) — never domain or
third-party custom types (`decimal.Decimal`, `uuid.UUID`, a domain enum). Plain types keep
`binding:"required"` working (the validator can't detect a zero `decimal.Decimal`) and keep
the wire contract independent of domain types. Convert at the edge in mapper funcs/methods:
the request DTO parses its strings into domain values (e.g. `AmountDecimal() (decimal.Decimal,
error)`, or a value-object `To<VO>()`); the `New<Resource>Response` mapper stringifies domain
values (`.String()`). A handler that returns a port read-model directly needs no DTO file.

```go
package dto

import "{{MODULE_PATH}}/internal/core/domain/entity"   // domain data types (plain import — distinct name)

type <Resource><Op>Request struct {
	Amount string `json:"amount" binding:"required"` // wire type, not decimal.Decimal
}

// AmountDecimal parses the request string into the domain value (convert at the edge).
func (r <Resource><Op>Request) AmountDecimal() (decimal.Decimal, error) {
	return decimal.NewFromString(r.Amount)
}

type <Resource>Response struct {
	Id string `json:"id"`
}

func New<Resource>Response(a *entity.<Aggregate>) <Resource>Response {
	return <Resource>Response{Id: a.Id().String()} // stringify domain values
}
```

DTOs are the wire shape; they never leak into `usecase`/`domain`. Map at the edge via getters.
(A handler that echoes a read-model directly returns the `integration/<sys>` type — an aliased
`*dm<upstream>.<ReadModel>` — and needs no `dto` mapper.)

## `middleware/` — the standard chain (wraps common-lib)

`Setup(r, serviceID)` applies the chain (service-id, correlation-id, error rendering, error
logging, recovery) by **calling common-lib** — it does not reimplement it.

```go
func Setup(r *gin.Engine, serviceID string) {
	r.Use(commonmw.ServiceIdMiddleware(serviceID))
	r.Use(commonmw.CorrelationIdMiddleware())
	r.Use(stdresp.GinErrorHandler(serviceID))
	r.Use(commonmw.ErrorLoggingMiddleware(logger.GetLogger()))
	r.Use(commonmw.Recovery())
}
```

## `router/` — routes split by resource + a main file

`router.New(h Handlers, serviceID)` builds the gin engine, applies `middleware.Setup`,
registers `/health`, creates the route groups, and calls each `register<Resource>`. Each
resource's routes live in their own file so adding/changing one resource's routes touches a
single file. The composition root (`app.md`) builds the concrete handlers, fills
`router.Handlers`, and passes it in — explicit wiring, no DI container.

```go
// router.go
type Handlers struct { Order *order.Handler; /* … one field per handler */ }

func New(h Handlers, serviceID string) *gin.Engine {
	gin.SetMode(gin.ReleaseMode)
	gin.EnableJsonDecoderDisallowUnknownFields()
	r := gin.New()
	middleware.Setup(r, serviceID)
	r.GET("/health", func(c *gin.Context) { c.JSON(http.StatusOK, gin.H{"status": "ok"}) })
	orders := r.Group("/orders")
	registerOrder(orders, h.Order)
	return r
}

// order.go — paths relative to the group
func registerOrder(r gin.IRoutes, h *order.Handler) {
	r.POST("", h.Create)
	r.GET("/:id", h.Get)
}
```

`router` is the **HTTP-composition sub-layer** — analogous to `cmd/api` but scoped to
routing — so it is the one inbound package permitted to import the handler packages.
Handlers still must never import each other.

## Error handling

Handlers **do not choose status codes**. They push errors with `c.Error(err)`; the single
`stdresp.GinErrorHandler` middleware (registered via `middleware.Setup`) maps each typed
domain error's category to its HTTP status and renders the standard envelope. Validation/bind
failures go through `shared.HandleValidationError` to become a typed 400 first.

## Don'ts

- ✗ Business rules, repository calls, or external calls in a handler — delegate to a usecase.
- ✗ Methods on the handler in `handler.go` — each endpoint goes in its own operation file.
- ✗ Returning the aggregate directly — always map to a response DTO via getters.
- ✗ DTOs inline in the operation file — request and response DTOs both live in `dto/<resource>.go`, resource-prefixed.
- ✗ Domain/custom types (`decimal.Decimal`, `uuid.UUID`, a domain enum) in a DTO field — use a primitive and convert in the mapper.
- ✗ A handler importing another handler, the router, or a concrete adapter.
