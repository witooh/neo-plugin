# Go conventions

- Domain errors are sentinel values in the domain package (`account.ErrNotFound`); map them to HTTP status in the handler with `errors.Is`.
- Handler tests use `httptest` and assert status code plus decoded body — never internal state.
- Run `make test` for the package suite and `make cover` for the coverage number.
