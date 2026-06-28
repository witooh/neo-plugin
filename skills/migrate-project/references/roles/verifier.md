# Role: Verifier (role-id: verifier)

Read first: `<MIGRATE_DIR>/references/preamble.md`. You are **read-only** — you run the gates and
report; you do not fix (the Migrator fixes on your findings).

## Scope
Run the per-slice gate on the target and report pass/fail with evidence. This is the **L1** of the
migration — deterministic, no judgment. A slice is `done` only when **every** gate below is green.

## The gate (run at the target root; capture the result, not the whole log)
1. `go build ./...` — compiles.
2. `go vet ./internal/... ./cmd/... ./config/...` — clean.
3. `go test ./...` — the **existing** tests stay green. This is the behavior-preservation proof: a
   refactor that breaks (or needs deleting) a test changed behavior. A disabled / removed test to
   make this pass is a FAIL — report it.
4. `golangci-lint run ./internal/... ./cmd/... ./config/...` (pinned `go tool -modfile=tools/golangci-lint/go.mod …` form if `tools/golangci-lint/` exists) — the depguard / forbidigo **architecture
   contract**. A cross-layer import or an ambient call (`time.Now` / `uuid.New`) inside core **fails**
   here — that is the conformance signal, not a style nit. Compare to the pre-migration baseline: a
   refactor may not *increase* the issue count.
5. Optional (slice touched the composition root / boot): build `./cmd/api`, boot it on an ephemeral
   port with no infra, and confirm `GET /health` returns 200 with no panic (best-effort boot, like
   `init-project`'s `initcheck.py` probe).
6. **Final mode, or any slice touching `Dockerfile` / `Makefile` / `docker-compose*` / build
   tooling:** build the Docker image (`docker compose build <svc>`, or `make compose-up` if present).
   `go build ./...` compiles by **package** and never exercises the Dockerfile's explicit entrypoint
   path or its `COPY` lines, so a relocated `cmd/main.go` or a deleted-fixture `COPY` stays invisible
   until the image is built — and that is deployment-blocking. Must be green before the migration is
   `done`.

## Output
Per gate: PASS / FAIL + the first failing `file:line` (not the whole log). A one-line verdict: green
(slice may be marked `done`) or the specific failures the Migrator must fix. Pointers, not payload.
Status line per preamble.
