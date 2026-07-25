---
source_url: https://eval.atlassian.net/browse/ACC-1
fetched_at: 2026-07-20T09:12:00Z
version: card as of 2026-07-20
---

# ACC-1 — Create account endpoint (verbatim capture)

As a client I want to create an account so that I can hold a balance.

## Requirements from the card

- `POST /accounts` accepts `name` and `balance`.
- `name` is **required**, between 1 and 100 characters. An empty name is rejected.
- `balance` is **required** and must be zero or greater.
- On success respond `201` with the created account, including a server-generated UUID v4 `id`.
- On a validation failure respond `400` with body `{"error": "<message>"}`.

## Notes captured from the card comments

- No authentication on this endpoint for the first release.
- Account limits per customer are **out of scope** for this card.
