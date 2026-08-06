# Mockoon — external dependency stubs

This is the **repo instance** of the e2e stub setup described generically in
`.kiro/steering/e2e.md`. Every external HTTP upstream the service calls in
non-production environments (local, CI, SIT smoke) is stubbed by
[Mockoon](https://mockoon.com/) — each upstream is its **own environment file on its own
port**, one Mockoon process serving them all.

A freshly scaffolded service has **no upstreams yet**. neo adds one stub file per
integration it introduces:

1. Create `<name>.json` (unique env `uuid`, next free port, e.g. `8500`).
2. Add a `mockoon` service to `docker-compose.yaml` (or extend it) using
   **`mockoon/cli:9.7.0`** that loads the file — append it to both `--data` and
   `--port` in the same order — and expose the port. Image tag is pinned in
   `.kiro/steering/tooling.md` (Docker Compose — standard images).
3. Point the adapter's `base_url` in `config/config.yaml` at it (e.g. `http://mockoon:8500`).

See `.kiro/steering/e2e.md` for the stub conventions — one route per `method + path`,
response rules, the `rootChildren` discipline (a route missing from it won't be served), and
Mockoon templating (`{{faker …}}`, `{{body …}}`, `{{queryParam …}}`).
