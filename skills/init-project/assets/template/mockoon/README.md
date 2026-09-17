# Mockoon: external dependency stubs

This is the **repo instance** of the e2e stub setup described generically in
`.kiro/steering/e2e.md`. Every external HTTP upstream the service calls in
non-production environments (local, CI, SIT smoke) is stubbed by
[Mockoon](https://mockoon.com/): each upstream is its **own environment file on its own
port**, one Mockoon process serving them all.

The compose service is already wired (`mockoon/cli:9.7.0`, port `8500`). There are
**no upstreams yet**, so `placeholder.json` is an empty environment that lets the
container start. neo replaces it when the first integration lands:

1. Create `<name>.json` (unique env `uuid`, next free port, e.g. `8500` then `8501`).
2. Point `docker-compose.yaml` `mockoon.command` at the file: append it to both
   `--data` and `--port` in the same order, and expose the port. Image tag is pinned in
   `.kiro/steering/tooling.md` (Standard images). Delete
   `placeholder.json` once a real stub occupies `8500`.
3. Point the adapter's `base_url` in `config/config.yaml` at it (e.g. `http://mockoon:8500`).

See `.kiro/steering/e2e.md` for the stub conventions: one route per `method + path`,
response rules, the `rootChildren` discipline (a route missing from it won't be served), and
Mockoon templating (`{{faker …}}`, `{{body …}}`, `{{queryParam …}}`).
