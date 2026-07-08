// neo-service entrypoint. Wiring, routing, configuration and lifecycle
// all live in this package (cmd/api); main only initialises the global
// logger before handing off control to Run.
package main

import (
	"context"
	"os/signal"
	"syscall"

	"example.com/neo/service/config"
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/logger"
)

func main() {
	cfg := config.MustLoad()
	logger.InitLogger(cfg.LoggerConfig)
	defer logger.Sync()
	defer logger.Info("server is gracefully terminated.")

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	if err := Run(ctx, cfg); err != nil {
		logger.Panic("service exited with error", logger.Err(err))
	}
}
