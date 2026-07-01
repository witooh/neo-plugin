# neo-service — Bruno Collection

Git-native API collection for driving the neo-service HTTP API locally. Open this folder in
[Bruno](https://www.usebruno.com/) (File → Open Collection) and select the **local** environment.

This collection is **generated from the api-spec** at `docs/api/*.yaml` by the `open-collection`
skill — regenerate rather than hand-edit (see `.kiro/steering/bruno.md`). A freshly scaffolded
service has no endpoints yet; neo's Architect authors the api-spec as it adds the first domain,
then regenerate to populate the resource folders below.

## Layout

```
bruno/
├── opencollection.yml          # collection root
├── environments/local.yml      # baseUrl (point at your running service)
└── <resource>/                 # one folder per resource — open-collection generates these
```

## Prerequisites

Start the service first — `go run ./cmd/api` (or `make compose-up` for the full stack) — then
the collection's requests run against `http://localhost:8080`.
