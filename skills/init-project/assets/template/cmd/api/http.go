// HTTP driving-adapter wiring: build the (initially empty) handler set, then run
// the server with graceful shutdown. Routing and the middleware chain live in the
// delivery layer (internal/delivery/http/router + middleware).
package main

import (
	"context"
	"errors"
	"net/http"

	"example.com/neo/service/config"
	"example.com/neo/service/internal/delivery/http/router"
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/logger"
)

// buildHandlers returns the handler set wired into the router. A freshly
// scaffolded service has none; neo adds a field per handler as it builds the
// usecase chain for each resource (see .kiro/steering/handler.md).
func buildHandlers() *router.Handlers {
	return &router.Handlers{}
}

func runHTTPServer(ctx context.Context, h *router.Handlers) error {
	engine := router.New(*h, config.Conf.ServiceConfig.ServiceId)

	addr := config.Conf.ServiceConfig.Host + ":" + config.Conf.ServiceConfig.Port
	srv := &http.Server{Addr: addr, Handler: engine.Handler()}
	logger.Info("server started", logger.String("url", addr))

	go func() {
		<-ctx.Done()
		logger.Info("server is terminating...")
		shutdownCtx, cancel := context.WithTimeout(context.Background(), config.Conf.ServiceConfig.ShutdownTimeout)
		defer cancel()
		if err := srv.Shutdown(shutdownCtx); err != nil {
			logger.Error("server shutdown error", logger.Err(err))
		}
	}()

	if err := srv.ListenAndServe(); err != nil && !errors.Is(err, http.ErrServerClosed) {
		return err
	}
	logger.Info("server is closed")
	return nil
}
