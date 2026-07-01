package postgres

import (
	"context"
	"database/sql"
	"errors"

	"gitlab.awesome-poc-th.com/libero-engineering/core/common-lib.git/v2/stderr"
)

type postgresTxKey struct{}

type transactor struct {
	db *sql.DB
}

type Transactor interface {
	Execute(ctx context.Context, executeFunc func(ctx context.Context) error) error
}

func NewTransactor(db *sql.DB) *transactor {
	return &transactor{
		db: db,
	}
}

func (t *transactor) Execute(ctx context.Context, executeFunc func(ctx context.Context) error) (err error) {
	txnCtx, err := t.begin(ctx)
	if err != nil {
		return err
	}
	defer func() {
		if err != nil {
			if rollbackErr := t.rollback(txnCtx); rollbackErr != nil {
				err = stderr.NewInternalServerError("rollback error", err, rollbackErr)
			}
		}
	}()
	if err := executeFunc(txnCtx); err != nil {
		return err
	}
	if err := t.commit(txnCtx); err != nil {
		return err
	}
	return nil
}

func (t *transactor) begin(ctx context.Context) (context.Context, error) {
	tx, err := t.db.BeginTx(ctx, nil)
	if err != nil {
		return nil, err
	}
	newCtx := context.WithValue(ctx, postgresTxKey{}, tx)
	return newCtx, nil
}

func (t *transactor) commit(ctx context.Context) error {
	tx, ok := ctx.Value(postgresTxKey{}).(*sql.Tx)
	if !ok {
		return errors.New("no transaction in context")
	}
	if tx == nil {
		return errors.New("no transaction in context")
	}
	return tx.Commit()
}

func (t *transactor) rollback(ctx context.Context) error {
	tx, ok := ctx.Value(postgresTxKey{}).(*sql.Tx)
	if !ok {
		return errors.New("no transaction in context")
	}
	if tx == nil {
		return errors.New("no transaction in context")
	}
	return tx.Rollback()
}
