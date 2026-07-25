# API Spec Changelog

## v1.0 — 2026-07-25

- **Endpoint(s):** account/create
- **Change:** Initial draft of POST /accounts — create account with required `name` (1–100 chars) and `balance` (>= 0); 201 returns created account with server-generated UUID v4 `id`; 400 returns `{"error": "..."}` on validation failure
