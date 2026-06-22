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
        <operation>.go    # ONE file per operation: the gin method + its request DTO + request mapper/validator
        shared/error.go   # cross-handler edge helpers (validation-error translation)
    dto/
        <resource>.go     # response DTOs + New<Resource>Response mappers (reused across that resource's ops)
        shared.go         # response-mapper helpers (e.g. decimalToFloat)
    middleware/
        middleware.go     # Setup(r, serviceID): the standard chain, wrapping common-lib
    router/
        router.go         # Handlers struct + New(h, serviceID) *gin.Engine — gin + middleware + health + groups
        <resource>.go     # register<Resource>(r gin.IRoutes, h *<resource>.Handler)
```

**One operation = one file.** A handler with N endpoints is N+1 files (`handler.go` + one
per op), so two people adding different endpoints never touch the same file. The operation
file is self-contained: its request DTO, its request→domain mapper, and its input
validation all live beside the gin method.

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

Holds the gin method, **its** request DTO (with `binding` tags), and **its** request→domain
mapper / validator. Response shaping calls a `dto.New<Resource>Response` mapper.

> **Name-collision alias.** A handler package may share its name with the domain context it
> maps to (`delivery/http/handler/<context>` and `domain/<context>` are both `package
> <context>`). When the operation file imports that domain context, **alias the domain import**
> (e.g. `dm<context>`) so the two don't clash. The skeletons below show the plain name for
> brevity; alias it where the collision is real. (This repo's actual aliases: `repo-instance.md`.)

```go
package <resource>

type Request struct {                                   // request DTO stays here (package-scoped)
	Amount decimal.Decimal `json:"amount" binding:"required"`
}

// <Op> reads the path/query, binds+validates the request (→ edge mapper), delegates to the
// usecase (passing c as ctx), pushes any typed error for the middleware to map to a status,
// then wraps the success payload in the standard envelope.
func (h *Handler) <Op>(c *gin.Context) {
	id := c.Param("id")
	var req Request
	if err := c.ShouldBindJSON(&req); err != nil {
		c.Error(shared.HandleValidationError(err))
		return
	}
	result, err := h.<Op>UC.Exec(c, id, toDomain(req))
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

// toDomain maps the request DTO to the aliased domain aggregate.
func toDomain(req Request) *dm<context>.<Aggregate> { /* ... */ }
```

## `dto/` — response DTOs (centralised, resource-prefixed)

Response DTOs and their `New<Resource>Response` mappers live in the `dto` package, one file
per resource. Because the package is shared, **type names are resource-prefixed** to avoid
collisions (`AccountResponse`, `BalanceResponse`, `AccountListResponse`). Request DTOs do
**not** move here — they stay inline in their operation file (package-scoped, so no prefix
is needed). A handler that returns a port read-model directly needs no DTO file.

```go
package dto

import dm<context> "{{MODULE_PATH}}/internal/core/domain/<context>"   // aliased: dto is not package <context>

type <Resource>Response struct {
	Id string `json:"id"`
}

func New<Resource>Response(a *dm<context>.<Aggregate>) <Resource>Response {
	return <Resource>Response{Id: a.Id().String()}
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
- ✗ Request DTOs in `dto/` — keep them inline in the operation file.
- ✗ A handler importing another handler, the router, or a concrete adapter.
