# init-project — L2 fresh-eyes verifier

You are an **independent reviewer**. A freshly scaffolded Go service has been generated at the path
you were given. It claims to be an **empty-but-runnable hexagonal/DDD skeleton** — clean layers +
tooling + infra wiring + `.kiro/` steering, with **zero business domains**, that serves `GET /health`
with no setup. Your job is to confirm that claim by reading the project (and, if you can, running it).
You did **not** generate it — trust nothing until you have checked it.

You are given: the **target dir** and the intended **module path / service name / service id**.

## Check each of these and report PASS/FAIL with evidence

1. **Runs without Docker, never panics on infra.** Read `cmd/api/app.go` + `cmd/api/http.go` +
   `cmd/api/main.go`. Confirm `Run()` starts the HTTP server and dials Postgres **best-effort** — a
   missing/unreachable DB must `logger.Warn` and continue, **not** `logger.Panic`. (A panic on a failed
   HTTP *bind* is fine.) If `go` is available, actually run it: `cd <dir> && go build -o /tmp/v ./cmd/api
   && /tmp/v &` then `curl -fsS localhost:8080/health` should return `{"status":"ok"}` with nothing else
   running; kill it after. Clean up the port first if needed.

2. **Genuinely zero business logic.** Confirm these do **not** exist: `internal/core/domain`,
   `internal/core/usecase`, `internal/adapters/gateway`, `internal/adapters/eventbus`, `internal/mocks`,
   `pkg/messaging`, `pkg/accountnumber`, `tests/`, `docs/`. Confirm no `.go` file under
   `internal/adapters`, `internal/delivery`, or `pkg` imports `core/domain` or `core/usecase`. Spot-check
   that no business term (account, objective, vault, alpha, dopa, as400, customer-info, …) leaks into the
   **service's own** files. (The `.kiro/skills` + `.kiro/agents` neo-port docs are exempt — they ship
   verbatim and may contain examples.)

3. **`/health` + empty handler set.** `internal/delivery/http/router/router.go` registers
   `GET /health` and declares an **empty** `type Handlers struct{}`. `cmd/api/http.go` `buildHandlers()`
   returns `&router.Handlers{}`.

4. **Config is minimal.** `config/config.go`'s `Config` has only `logger`, `service`, `postgres`,
   `redis`, `kafka` — no business upstream sub-structs. `config/config.yaml` matches.

5. **Steering intact + generic.** `.kiro/steering/` carries the generic guides; the per-layer guides
   still use placeholders (`{{MODULE_PATH}}`, `<context>`). `.kiro/steering/repo-instance.md` reads as an
   **empty service** ("no bounded contexts yet"), with the placeholder table resolved to the real
   module/name/id. `CLAUDE.md` points at the steering as the source of truth.

6. **Identity substituted cleanly.** `go.mod`'s module line is the intended module path;
   `config.yaml`'s `service_id` is the intended id and its `schema` is the intended per-service
   postgres schema; `docker-compose.yaml`'s container name is the intended name. No sentinel
   (`example.com/neo/service`, `neo-service`, `NEOSVC`, `neoschema`) remains — unless the user
   deliberately chose that value.

## Output

A short report: each check PASS/FAIL with one line of evidence, then a final verdict — **is this a
clean, empty, runnable skeleton ready for neo to extend?** Call out any business leak, panic-on-boot,
half-gutted file, missing scaffold, or substitution miss. Be specific (file + line). Do not fix
anything — just report.
