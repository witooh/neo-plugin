---
inclusion: fileMatch
fileMatchPattern: "**/bruno/**"
---

# API Request Collection (Bruno OpenCollection)

`bruno/` is a runnable **OpenCollection 1.0** and the **API source of truth**: each request's
`docs:` block is the contract for its endpoint. Author it with the `bruno` skill. Requests are
grouped by resource, mirroring the handler packages.

```
bruno/
    opencollection.yml         collection root
    environments/<env>.yml     variables per environment (baseUrl, IDs, sentinels)
    <resource>/<operation>.yml one request per usecase endpoint (e.g. order/get-order.yml)
    <resource>/folder.yml      folder info + auth/headers (every folder that holds requests)
    README.md
```

## Collection root: `opencollection.yml`

```yaml
opencollection: 1.0.0
info:
  name: <Service> API
bundled: false
docs: |-                        # must hold ## Overview, ## Error Response Body, ## Common Error Responses
  ...
extensions:
  bruno:
    ignore: [node_modules, .git]
```

## Environment: `environments/<env>.yml`

Variables only: the base URL plus the IDs/sentinels requests reference as `{{var}}`.
Some are seeded at runtime by an earlier request's after-response script (chaining).

```yaml
name: local
variables:
  - name: baseUrl
    value: http://localhost:8080
  - name: orderId
    value: 00000000-0000-0000-0000-000000000001   # sentinel: deterministic against the stub
  - name: createdOrderId
    value: ""                                       # filled at runtime by a prior request
```

## Request: `<resource>/<operation>.yml`

Top-level order is `info → http → runtime → settings → docs`.

```yaml
info:
  name: Get Order
  type: http
  seq: 10                       # unique within the folder (and for chained runs)

http:
  method: GET
  url: "{{baseUrl}}/orders/{{orderId}}"
  # body: { type: json, data: "..." }   # for POST/PUT

runtime:
  scripts:
    - type: tests               # assertions run after the response
      code: |-
        test("status is 200", function () { expect(res.status).to.equal(200); });
    # - type: after-response     # capture an id into an env var to chain later requests

settings:
  encodeUrl: true

docs: |-
  ## Purpose
  ...
  ## Request
  ### Endpoint
  `GET /orders/{orderId}`
  ### Auth
  `None`
  ### Path Parameters
  | Field Name | Type | Mandatory | Description | Possible Value |
  |---|---|---|---|---|
  | orderId | String | Yes | Order id | `"00000000-0000-0000-0000-000000000001"` |
  ## Response
  ### HTTP Status: 200
  | Field Name | Type | Mandatory | Description | Possible Value |
  ### Error Responses
  | Status | Response Code | Error Code | Error Messages | Description |
```

## `docs:` rules

- Required: `## Purpose`, `## Request` (`### Endpoint`, `### Auth`) and `## Response`. `### Endpoint` is one
  `METHOD /path` line that matches `http.method` and `http.url` (`{id}` is `:id`).
- Field tables use exactly `Field Name | Type | Mandatory | Description | Possible Value`.
  `Type` is `String`, `Number`, `Boolean`, `Object` or `Array`; `Mandatory` is `Yes` or `No`.
  Nest with dot-paths (`data.id`, `items[].code`) and give every nested row a parent row.
- A `### Body (JSON)` table is followed by a `### Example` that parses as JSON and covers every `Yes` row.
- `### Error Responses` lists endpoint-specific errors only, with columns
  `Status | Response Code | Error Code | Error Messages | Description`. The common-lib body
  (`responseCode`, `errorCode`, `errorMessage`) is documented once in the `opencollection.yml` `docs:`.
- `docs:` is read by the teams that call the API: no ticket or AC IDs, internal repo paths, or
  working notes.

## Conventions

- **One request file per endpoint**, in a folder named after the resource, same grouping as `internal/delivery/http/handler/<resource>`.
- Reference everything mutable through **env variables**; bake nothing host- or data-specific into the request.
- Use **sentinel IDs** that match the stub/seed data so requests are deterministic.
- Chain dependent requests with an **after-response** script that writes an id into an env var, and order with `seq`.
