---
inclusion: fileMatch
fileMatchPattern: "**/bruno/**"
---

# API Request Collection (Bruno OpenCollection)

`bruno/` is a runnable **OpenCollection 1.0** for exercising the HTTP API. Requests are
grouped by resource, mirroring the handler packages.

```
bruno/
    opencollection.yml         collection root
    environments/<env>.yml     variables per environment (baseUrl, IDs, sentinels)
    <resource>/<operation>.yml one request per usecase endpoint (e.g. order/get-order.yml)
    README.md
    openapi.yaml               OpenAPI spec (separate artifact, not part of the runnable collection)
```

## Collection root — `opencollection.yml`

```yaml
opencollection: 1.0.0
info:
  name: <Service> API
bundled: false
extensions:
  bruno:
    ignore: [node_modules, .git]
```

## Environment — `environments/<env>.yml`

Variables only: the base URL plus the IDs/sentinels requests reference as `{{var}}`.
Some are seeded at runtime by an earlier request's after-response script (chaining).

```yaml
name: local
variables:
  - name: baseUrl
    value: http://localhost:8080
  - name: orderId
    value: 00000000-0000-0000-0000-000000000001   # sentinel — deterministic against the stub
  - name: createdOrderId
    value: ""                                       # filled at runtime by a prior request
```

## Request — `<resource>/<operation>.yml`

```yaml
info:
  name: Get Order
  type: http
  seq: 10                       # ordering within the folder (and for chained runs)

http:
  method: GET
  url: "{{baseUrl}}/orders/{{orderId}}"
  # body: { mode: json, json: "..." }   # for POST/PUT

runtime:
  scripts:
    - type: tests               # assertions run after the response
      code: |-
        test("status is 200", function () { expect(res.status).to.equal(200); });
        test("has status", function () { expect(res.body.data.status).to.be.a("string"); });
    # - type: after-response     # capture an id into an env var to chain later requests

settings:
  encodeUrl: true
  timeout: 0
  followRedirects: true
  maxRedirects: 5

docs: |
  ## Purpose
  ...
  ## Request
  `GET /orders/{orderId}`
  ## Response
  `200` — `{ orderId, status }`; `404` — unknown order ID.
```

## Conventions

- **One request file per endpoint**, in a folder named after the resource — same grouping as `internal/delivery/http/handler/<resource>`.
- Reference everything mutable through **env variables**; bake nothing host- or data-specific into the request.
- Use **sentinel IDs** that match the stub/seed data so requests are deterministic.
- Chain dependent requests with an **after-response** script that writes an id into an env var, and order with `seq`.
- Put a short **`docs`** block (purpose + request + response/error summary) in every request — it is the human-facing contract.
- Keep `openapi.yaml` (the spec) and the runnable collection consistent, but they are separate artifacts.
