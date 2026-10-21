// Composition root: start the HTTP server, then best-effort dial infrastructure.
// A freshly scaffolded service serves GET /health with no dependencies, while
// Postgres is wired and ready for the first domain neo adds.
package main

import (
	"context"
	"database/sql"
	"fmt"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"

	"example.com/neo/service/config"
	"example.com/neo/service/internal/core/domain"
	"example.com/neo/service/internal/core/domain/errorcatalog"
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/logger"
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/stderr"
)

// Run is the composition root. It starts the HTTP server immediately (so /health
// is available without infrastructure) and connects to Postgres on a best-effort
// basis: a freshly scaffolded service must run with `go run ./cmd/api` alone.
// neo replaces the best-effort wiring with real repositories, usecases and
// handlers as it builds the first domain (see .kiro/steering/app.md). An invalid
// error catalog fails startup.
func Run(ctx context.Context, cfg *config.Config) error {
	catalog, err := loadErrorCatalog(errorcatalog.JSON())
	if err != nil {
		logger.Error("error.catalog.invalid", logger.Err(err))
		return err
	}
	if db := tryOpenDB(ctx, cfg.PostgresConfig); db != nil {
		defer db.Close()
	}

	h := buildHandlers()
	return runHTTPServer(ctx, cfg.ServiceConfig, h, catalog)
}

// loadErrorCatalog validates the Appendix-E catalog. An invalid catalog fails startup: a service
// that cannot resolve its own codes would answer every error as NZQ-9001.
func loadErrorCatalog(data []byte) (*stderr.Catalog, error) {
	catalog, err := stderr.LoadCatalog(data)
	if err != nil {
		return nil, fmt.Errorf("load error catalog: %w", err)
	}
	if err := catalog.Require(domain.ErrorRefs()...); err != nil {
		return nil, fmt.Errorf("load error catalog: %w", err)
	}
	return catalog, nil
}

// tryOpenDB connects to Postgres when it is reachable, returning nil (after a
// warning) when it is not: the empty skeleton never panics on a missing
// database. neo swaps this for the real connection + sqlc.New(db) wiring.
func tryOpenDB(ctx context.Context, pg config.PostgresConfig) *sql.DB {
	db, err := sql.Open("pgx", pg.ConnectionString())
	if err != nil {
		logger.Warn("postgres not configured; serving without it", logger.Err(err, logger.CategoryDatabase))
		return nil
	}
	pingCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()
	if err := db.PingContext(pingCtx); err != nil {
		logger.Warn("postgres unreachable; serving without it", logger.Err(err, logger.CategoryDatabase))
		_ = db.Close()
		return nil
	}
	return db
}
