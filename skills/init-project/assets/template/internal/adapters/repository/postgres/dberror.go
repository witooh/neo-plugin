package postgres

import (
	"errors"

	"github.com/jackc/pgx/v5/pgconn"

	"example.com/neo/service/internal/core/domain"
)

// NewDBError wraps a driver failure as NZQ-8001 (database unavailable). The driver's text is the
// cause: logged, never rendered.
func NewDBError(err error) error {
	return domain.NewDatabaseUnavailableError(err)
}

func IsDuplicateEntryError(err error) bool {
	var pgErr *pgconn.PgError
	if errors.As(err, &pgErr) {
		switch pgErr.Code {
		case "23505":
			return true
		}
	}
	return false
}
