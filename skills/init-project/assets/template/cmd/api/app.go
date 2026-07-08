// Composition root: start the HTTP server, then best-effort dial infrastructure.
// A freshly scaffolded service serves GET /health with no dependencies, while
// Postgres is wired and ready for the first domain neo adds.
package main

import (
	"context"
	"database/sql"
	"time"

	_ "github.com/jackc/pgx/v5/stdlib"

	"example.com/neo/service/config"
	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/logger"
)

// Run is the composition root. It starts the HTTP server immediately (so /health
// is available without infrastructure) and connects to Postgres on a best-effort
// basis — a freshly scaffolded service must run with `go run ./cmd/api` alone.
// neo replaces the best-effort wiring with real repositories, usecases and
// handlers as it builds the first domain (see .kiro/steering/app.md).
func Run(ctx context.Context, cfg *config.Config) error {
	if db := tryOpenDB(ctx, cfg.PostgresConfig); db != nil {
		defer db.Close()
	}

	h := buildHandlers()
	return runHTTPServer(ctx, cfg.ServiceConfig, h)
}

// tryOpenDB connects to Postgres when it is reachable, returning nil (after a
// warning) when it is not — the empty skeleton never panics on a missing
// database. neo swaps this for the real connection + sqlc.New(db) wiring.
func tryOpenDB(ctx context.Context, pg config.PostgresConfig) *sql.DB {
	db, err := sql.Open("pgx", pg.ConnectionString())
	if err != nil {
		logger.Warn("postgres not configured; serving without it", logger.Err(err))
		return nil
	}
	pingCtx, cancel := context.WithTimeout(ctx, 2*time.Second)
	defer cancel()
	if err := db.PingContext(pingCtx); err != nil {
		logger.Warn("postgres unreachable; serving without it", logger.Err(err))
		_ = db.Close()
		return nil
	}
	return db
}
