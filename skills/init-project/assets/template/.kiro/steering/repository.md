---
inclusion: fileMatch
fileMatchPattern: "**/internal/adapters/repository/**,**/*.sql,sqlc.yaml"
---

# Repository Layer (outbound persistence adapter)

Implements the driven persistence **interfaces** centralized in the domain `repository` package
(e.g. `repository.<Aggregate>Repository`, speaking `entity` aggregates) against PostgreSQL via
**sqlc**-generated queries. The interfaces are domain-owned (see `domain.md`); only the
implementation lives here.

```
internal/adapters/repository/postgres/
    <aggregate>.go     # repo impl: struct + New<Agg>Repository + methods + mapper
    transactor.go      # tx boundary helper
    dberror.go         # NewDBError — wraps driver errors into typed domain errors
    utilities.go       # null helpers (sql.NullString ↔ *string, etc.)
    sqlc/              # GENERATED — never hand-edit (models, querier, *.sql.go)
    queries/           # *.sql query sources (sqlc input)
    migrations/        # ordered schema migrations
    seed/              # seed data conventions

internal/adapters/repository/redis/   # low-level Redis client
internal/adapters/repository/cache/   # cache adapter → repository.Cache (wraps redis; see integration.md)

sqlc.yaml              # at the REPO ROOT — points queries/schema/out at the postgres dirs above
```

## Repository implementation

```go
// Package postgres implements the <Aggregate>Repository port (from internal/core/domain/repository)
// against PostgreSQL via sqlc.
package postgres

import (
	"{{MODULE_PATH}}/internal/core/domain/entity"     // the aggregate it speaks
	"{{MODULE_PATH}}/internal/core/domain/repository" // the port it implements
)

type <aggregate>Repository struct {  // unexported
	Queries *sqlc.Queries
}

// New<Agg>Repository returns the domain interface, not the concrete struct.
func New<Aggregate>Repository(q *sqlc.Queries) repository.<Aggregate>Repository {
	return &<aggregate>Repository{Queries: q}
}

func (r *<aggregate>Repository) GetById(ctx context.Context, id uuid.UUID) (*entity.<Aggregate>, error) {
	row, err := r.Queries.Get<Aggregate>ById(ctx, id)
	if err != nil {
		if errors.Is(err, sql.ErrNoRows) {
			return nil, nil
		}
		return nil, NewDBError(err)
	}
	return mapSqlc<Aggregate>ToDomain(row), nil
}
```

- Constructor returns the **interface** so the composition root depends on the contract.
- One repo type satisfying two interfaces returns the **concrete** instead (can't return
  two interfaces); that is the only allowed exception.

## Mapper — row → aggregate via Restore

Never construct an aggregate with a struct literal here; reconstitute through its
`Restore<Aggregate>` factory (see `domain.md`).

```go
func mapSqlc<Aggregate>ToDomain(r sqlc.<Aggregate>) *entity.<Aggregate> {
	return entity.Restore<Aggregate>(entity.Restore<Aggregate>Param{
		Id:        r.Id,
		Status:    r.Status,
		CreatedAt: r.CreatedAt,
		// ...
	})
}
```

> Per-TYPE-per-file aliasing: a file mapping `sqlc.<Aggregate>` → `entity.<Aggregate>` cannot have
> both unqualified, so the domain side is imported as `entity` while `sqlc`
> keeps its package name — name the local consistently within the file.

When a row maps to a sub-value-object too, extract a small `mapSqlc<X>ToDomain` helper
per type rather than inlining.

## Errors

`dberror.go` exposes `NewDBError(err)` which wraps any driver error into a typed service
error (a generic "database" error the edge mapper renders as 5xx). Repositories return
`NewDBError(...)`; they never return a raw `pgconn`/`pq` error upward. A separate helper
(`IsDuplicateEntryError`, checking pg code `23505`) classifies a specific constraint
violation where a caller must branch on it. `sql.ErrNoRows` for an **optional** read
becomes `(nil, nil)`; for a **required** read it becomes a typed not-found.

## Transactions

`transactor.go` provides the tx boundary; a multi-write operation runs its steps inside
one transaction and commits/rolls back atomically. Keep the tx scope inside the
repository method (or a transactor passed in) — usecases stay persistence-agnostic.

## sqlc workflow

- **`queries/*.sql`** are the source of truth for queries; **`sqlc/`** is generated —
  regenerate with `make db-gen`, never hand-edit.
- Name queries `<Verb><Aggregate>[By<Key>]`; annotate with `-- name: ... :one|:many|:exec`.
- **`migrations/`** are ordered and append-only; a schema change = a new migration
  (`make create-migration NAME=…`, applied with `make migration-up`), never an edit to a
  shipped one.
- **Per-service postgres schema** — services share one database; this service owns exactly one
  schema in it, created by the compose `postgres-init` one-shot and pinned via `search_path` in
  every connection string (runtime DSN `config.PostgresConfig.ConnectionString`, Makefile
  `PG_SCHEMA`). All objects, including `schema_migrations`, live there — never in `public`.
- **`seed/`** holds idempotent seed SQL (e.g. `ON CONFLICT DO NOTHING`) for reference
  data — safe to re-run.
- `sqlc.yaml` configures the input/output dirs, the engine, and type overrides (uuid,
  decimal, timestamps).

## Don'ts

- ✗ Business logic in a repository — it persists and reconstitutes, nothing more.
- ✗ Aggregate struct literals — use `Restore<Aggregate>`.
- ✗ Hand-editing generated `sqlc/` code.
- ✗ Returning raw driver errors — wrap with `NewDBError`.
