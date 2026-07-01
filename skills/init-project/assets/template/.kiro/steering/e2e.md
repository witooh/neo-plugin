---
inclusion: fileMatch
fileMatchPattern: "**/tests/**,**/mockoon/**"
---

# E2E & Upstream Stubs

Black-box tests that prove the **wired** service end-to-end: it runs in a container with its
**real** adapters (only each `base_url` changes), reached over HTTP. External upstreams are
served by a **stub server**; infra the service owns (DB, cache, broker) are **real**
containers. Unit tests prove logic in isolation (`testing.md`); e2e proves the wiring,
routing, serialization, and error→status mapping that fakes can't.

> This guide is the **generic pattern**. The concrete stub tool, ports, per-upstream file map,
> sentinels, and edit gotchas for a given repo are its **repo instance** — kept in the stub
> directory's own `README.md` (the directory matched by `fileMatchPattern` above). Read that
> alongside this guide.

## Upstream stubs — one file per upstream

Each external HTTP upstream is replaced by canned responses from a **stub server**, with stubs
**split one mapping/environment file per upstream** (never one monolith): a stub edit then
loads only that upstream's small file, and different features touch different files — small
diffs, no merge conflicts. Point each adapter's `base_url` at its upstream's stub.

- **Determinism via sentinel IDs:** requests use fixed sentinel identifiers, each chosen to
  trigger exactly one path (eligible / not-found / blocked / unavailable) so assertions stay
  single-cause. Keep sentinels in sync with the seed data.
- **Templating** only where a canned body won't do (echo the request, mint a fresh id per
  call); plain JSON otherwise.
- **One stub may wrap another:** a derived stub can reuse another upstream's `base_url` rather
  than take its own file/port.
- **Tool-specific gotchas** — route ordering, how a multi-response route is selected, how a body
  is stored, any route index the tool keeps — live with the repo instance; read its `README.md`
  before hand-editing a stub file.

## Editing a stub

Edit the **one file for the upstream you're changing**, through the stub tool's GUI/editor so
you work with real JSON — not an escaped string. Keep responses deterministic (sentinel IDs)
and follow the tool's matching rules (exact paths before parameterised ones; a `default`
fallback for multi-response routes). Per-tool specifics and gotchas: the repo instance
`README.md`.

## Adding an upstream stub

1. Add a stub file for the upstream (its own port if the tool is one-environment-per-port).
2. Wire it into the stub server's run config (file + port) and expose the port.
3. Point the adapter's `base_url` at it in config (`app.md`).
4. Rebuild the image and restart the stack (`tooling.md`).

Exact files/ports/commands for the repo: its stub `README.md`.

## Writing a spec

```
tests/e2e/
    specs/*            one spec per feature; arrange stub → call endpoint → assert envelope + side effects
    helpers/           request client, fixtures, sentinel IDs
    <global-setup>     bring up / wait for the stack (+ setup / teardown / config)
```

Arrange the stub (pick the sentinel) → call the endpoint → assert the **full envelope** (HTTP
status, `status`, `data` / error code) **and** side effects (persisted rows, emitted events).
E2e is the contract guard; reaching a real upstream from a test = never (stub it).

## ⚠️ Rebuild before e2e

E2e runs against the **built image** — if the stack is already up, the run target may skip
rebuilding and silently test stale code. Always rebuild **then** run e2e. Note the full
"test everything" target may include integration that needs Docker; use the unit-only /
`-short` target for fast no-Docker runs, and don't run it against a live stack (they contend
for Docker → false failures). E2e is also the tier that catches the serialization
**JSON-`{}` gotcha** (`domain.md`) that unit stubs miss. Exact targets: `tooling.md` / the
repo's stub `README.md`.

For the unit/property tier and the full "what to test where" split, see `testing.md`.
