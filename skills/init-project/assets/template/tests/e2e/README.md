# E2E: neo-service

Black-box HTTP tests against the **built image**, run by Jest with Playwright's `request` API as
the client. This file is the **repo instance** `.kiro/steering/e2e.md` points to: the generic
pattern is in that guide, the concrete values are here.

## Layout

```
tests/e2e/
  package.json          scripts.test = jest --runInBand --forceExit
  jest.config.ts         testMatch **/*.e2e.ts · maxWorkers 1
  jest.global-setup.ts   polls GET /health (30 × 2s) before the suite runs
  jest.setup.ts          globalThis.apiContext = request.newContext({ baseURL })
  .env.test              API_BASE_URL (CI overrides it: see below)
  helpers/
    api-client.ts        ApiClient: HTTP wrapper only until the first domain
    index.ts             barrel: import from "@helpers/index"
  specs/
    health.e2e.ts        GET /health: no-AC mode
```

## No upstream stubs, no fixtures: and why

`e2e.md` describes per-upstream stub files and seed fixtures. **This service has neither yet**,
deliberately:

- **No upstream.** The skeleton serves `GET /health` only. Compose already runs
  `mockoon/cli:9.7.0` with `mockoon/placeholder.json` (empty env on `:8500`) so the
  container starts; neo replaces that file when a domain calls an external system.
- **No seed data.** There are no tables. The `neoschema` schema is created by the compose
  `postgres-init` one-shot, so there is no `fixtures/*.sql` and no `DbHelper`.

Add real stubs and fixtures when the first domain talks to an upstream or persists a row.

## Run it

```bash
# Local: brings the stack up if /health is not already answering, then runs jest.
make test-e2e

# Explicitly, when you want to control the rebuild:
make compose-up            # docker compose up -d --build
cd tests/e2e && npm install && npm test
```

**Rebuild before you run.** E2e proves the *built image*; if the stack is already up from an
earlier commit, `make compose-up` is what re-builds it. Running the suite against a stale
container tests code you are not looking at.

Do not run `make test` and `make test-e2e` at the same time: they contend for Docker
(`compose-up` does `rm -rf vendor`).

## CI

The `e2e-test` stage in `.gitlab-ci.yml` runs on every merge request and branch:

1. `docker compose up -d --build --wait` inside Docker-in-Docker (needed on `linux` runners;
   there is no host docker socket).
2. Detects the compose network name.
3. Runs `npm ci && npm test` in a `node:22-alpine` container joined to that network, with
   `API_BASE_URL=http://neo-service:8080`: the service name, not localhost, because
   the runner is a sibling container.
4. `after_script` dumps `neo-service` logs and tears the stack down even on failure.

No migration step: this service owns no tables yet. The `neoschema` schema is created by the
compose `postgres-init` one-shot.

`dotenv` does not override variables already in the environment, so the CI `API_BASE_URL` wins
over `.env.test`.

`package-lock.json` is committed because CI uses `npm ci`, which requires it.
