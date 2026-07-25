# create-account — Create a new account

## Objective

Expose `POST /accounts` so a client can create an account with a starting balance.

## Acceptance criteria

- **AC-001** — POST /accounts with a valid body returns 201 and the created account, including a server-generated UUID v4 `id`.
- **AC-002** — POST /accounts with `name` empty or longer than 100 characters returns 400 with body `{"error": "..."}`.
- **AC-003** — POST /accounts with a negative `balance` returns 400 with body `{"error": "..."}`.

## Non-goals

- Authentication and authorization on the endpoint.
- Updating or deleting an account.
