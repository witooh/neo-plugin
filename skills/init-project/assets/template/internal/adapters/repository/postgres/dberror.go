package postgres

import (
	"errors"

	"github.com/jackc/pgx/v5/pgconn"

	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/stderr"
)

func NewDBError(err error) error {
	return stderr.NewServiceError(
		"An unexpected error has occurred on physical resource.",
		stderr.NewSubError(err, stderr.WithCode("err_database"), stderr.WithMessage(err.Error())),
	)
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
