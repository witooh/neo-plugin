---
inclusion: fileMatch
fileMatchPattern: "**/cmd/api/**,**/config/**"
---

# Composition Root (`cmd/api`) + Configuration (`config`)

`cmd/api` (`package main`) is the **only** package allowed to import concrete adapters
and usecases and wire them. This is where interfaces meet implementations; every other
package programs to interfaces. `main.go` is a thin entry point. Runtime configuration
lives in its own top-level **`config`** package (`config/config.go`), beside
`config/config.yaml`; `cmd/api` imports it and reads `config.Conf`.

```
cmd/api/               package main — composition root + entry point
    main.go            tiny: build context, call Run(ctx)
    app.go             Run(ctx): open infra (DB, cache), build adapters, start HTTP + consumer
    adapters.go        construct the gateway / producer / number-generator adapters (each returns its port)
    http.go            buildHandlers + runHTTPServer (router lives in delivery/http/router)
    consumer.go        startKafkaConsumer (wires the processor)
config/                package config — runtime configuration (imported by cmd/api)
    config.go          typed Config struct + Conf global + env/file loader
    config.yaml        runtime config values (mounted into the container)
```

## ⚠️ Domain-port imports + name-collision aliases

The wiring imports the **centralized domain ports** (the parameter types of
`buildHandlers`): the `repository` package's port(s) — repositories plus any `NumberGenerator` /
`Cache` — the `event` package's `EventPublisher`, and the `integration/<sys>` gateway ports — plus the concrete
adapter types it constructs (e.g. `eventbus.ProducerAdapter`, `cache.Cache`).

The concrete repository / gateway ports for this service are in `repo-instance.md`.

The **per-layer domain packages** (`entity`, `repository`, `event`, root `domain`) have distinct
names from the handler packages, so `cmd/api/http.go` imports them plain. Only integration packages
(`integration/<upstream>`, `package <upstream>`) can still share a name with a handler; alias those:

```go
import (
    "{{MODULE_PATH}}/internal/core/domain/repository"                          // domain ports (plain)
    "{{MODULE_PATH}}/internal/core/domain/entity"                             // domain data types (plain)
    dm<upstream> "{{MODULE_PATH}}/internal/core/domain/integration/<upstream>" // aliased if it clashes with a handler
    // …
    "{{MODULE_PATH}}/internal/delivery/http/handler/<context>"             // handler (bare name)
    "{{MODULE_PATH}}/internal/delivery/http/handler/<other>"
)

func buildHandlers(<aggregate>Repo repository.<Aggregate>Repository, <upstream>Adapter dm<upstream>.<Upstream> /* … */) *router.Handlers
```

(The integration-package aliasing convention also applies inside the handler packages — see
`handler.md`.)

## `main.go` — thin

```go
func main() {
	ctx, stop := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer stop()
	if err := Run(ctx); err != nil {
		logger.Fatal("service exited", logger.Err(err))
	}
}
```

## Building adapters (`app.go` opens infra; `adapters.go` builds the rest)

Infra handles (DB, cache) are opened in `app.go`'s `Run`; the gateway / producer /
number-generator adapters are constructed in `adapters.go`. Each `New...` returns a
**port interface** owned by its domain context (see `integration.md` / `repository.md`) — the
only place concrete adapter types are named.

```go
db := openDB(config.Conf.DB)
queries := sqlc.New(db)
<aggregate>Repo := postgres.New<Aggregate>Repository(queries)            // → repository.<Aggregate>Repository
<upstream>Adapter := <upstream>http.NewHTTPAdapter(<upstream>http.Config{}) // → <sys>.<Upstream>
appCache := cache.NewCache(redisClient)                                 // → repository.Cache
```

## `http.go` — wire usecases into handlers, then serve

`buildHandlers` takes the **domain-owned port interfaces** as parameters (not concretes — the
abstraction boundary), constructs each usecase via `New(Params{...})`, injects them into each
handler's `New`, and returns a filled **`router.Handlers`** (the handler set). Gin engine
construction, the middleware chain, `/health`, and route groups now live in the delivery layer
(`internal/delivery/http/router` + `middleware`, see `handler.md`) — `cmd/api` only **fills**
`router.Handlers` and hands it to `router.New`.

```go
func buildHandlers(<aggregate>Repo repository.<Aggregate>Repository, <upstream>Adapter dm<upstream>.<Upstream> /* …interfaces… */) *router.Handlers {
	<op>UC := <operation>.New(<operation>.Params{Repo: <aggregate>Repo})
	// ... build every usecase ...
	return &router.Handlers{
		<Resource>: <resource>.New(<op>UC),
		<Multi>:    <multi>.New(uc1, uc2, uc3), // a handler fronting several usecases
	}
}

func runHTTPServer(ctx context.Context, h *router.Handlers) error {
	engine := router.New(*h, config.Conf.ServiceConfig.ServiceId) // gin + middleware + /health + groups (delivery)
	srv := &http.Server{Addr: addr, Handler: engine.Handler()}
	go func() { <-ctx.Done(); srv.Shutdown(shutdownCtx) }() // graceful shutdown on ctx cancel
	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	return nil
}
```

The split is fixed: `cmd/api` builds the usecases + handler set; `router.New` (in delivery)
owns middleware → `/health` → groups → `Register`; `runHTTPServer` runs `ListenAndServe` with a
`ctx`-driven `Shutdown`.

## `consumer.go` — start the Kafka consumer

Wire the processor (its inbound port satisfied by a usecase) to the consume loop; run it
under the same `ctx` so shutdown is coordinated with the HTTP server.

```go
proc := consumer.New(<op>UC)   // usecase satisfies the processor's inbound port
return startConsumeLoop(ctx, kafkaClient, proc.Process)
```

## The `config` package (`config/config.go`)

A typed `Config` struct loaded once into a package-level `config.Conf` — its own
top-level **`package config`**, beside `config/config.yaml`. Group by concern
(service, DB, kafka, each upstream). The loader reads the YAML file then overlays
env-var overrides (upper-snake dotted path, e.g. `VAULT_BASE_URL`) — SIT/prod inject
the full config this way. Secrets come from the environment / secret store — never
commit them. `cmd/api` reads `config.Conf` and hands each adapter its slice via the
adapter's own `Config` struct; adapters/usecases never read `config.Conf` directly.

## Don'ts

- ✗ Business logic or HTTP/DTO shaping here — wiring only.
- ✗ Passing concrete adapter types into `buildHandlers` — pass interfaces.
- ✗ Reading `config.Conf` from inside a usecase/adapter — inject the needed values.
