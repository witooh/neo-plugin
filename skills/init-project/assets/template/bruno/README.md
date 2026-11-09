# neo-service: Bruno Collection

Git-native API collection for driving the neo-service HTTP API locally. Open this folder in
[Bruno](https://www.usebruno.com/) (File → Open Collection) and select the **local** environment.

This collection is the **API source of truth**, authored with the `bruno` skill (see
`.kiro/steering/bruno.md`). Each request's `docs:` block holds its contract. A freshly scaffolded
service has no endpoints yet; add a request under `<resource>/` as each endpoint is built.

## Layout

```
bruno/
├── opencollection.yml          # collection root
├── environments/local.yml      # baseUrl (point at your running service)
└── <resource>/                 # one folder per resource, one request per endpoint
```

## Prerequisites

Start the service first: `go run ./cmd/api` (or `make compose-up` for the full stack), then
the collection's requests run against `http://localhost:8080`.
