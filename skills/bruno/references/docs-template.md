# Bruno `docs:` template: the contract layout

Every request's `docs:` block is its endpoint's contract, generated from code. This file fixes its layout,
the table rules and the Audience rules. `assets/docsparse.py` parses exactly this shape and
`assets/brunocheck.py` enforces it (rule IDs K1-K14 in brackets). YAML keys outside `docs:` are in
[`yaml-reference.md`](yaml-reference.md).

---

## Collection layout

```
bruno/
├── opencollection.yml       info.name + docs: (service level)
├── environments/            local.yml · sit.yml (init-project template naming)
└── <domain>/
    ├── folder.yml           info{name, type: folder, seq} + request.auth/headers + optional docs:
    └── <endpoint>.yml       one endpoint = its contract, generated from code
```

- Request top-level order: `info → http → runtime → settings → docs` [K1]. `examples` is never emitted.
  An extra request (no `docs:`, same method and path as a request that has one) is skipped with a NOTE [K1].
- Every directory that holds requests has a `folder.yml`; `info.seq` is unique within a folder [K9].
- Domain prose goes in that folder's `folder.yml` `docs:` (optional, free prose).

---

## Collection-root `docs:` (`opencollection.yml`)

```markdown
## Overview
<service purpose>

## Field Information          ← optional; shared enums
### <Enum Name>
| Code | Description |

## Error Response Body        ← required [K11]; the common-lib body, documented once
| Field Name | Type | Mandatory | Description | Possible Value |
| responseCode | String | Yes | ... | `"001"` |
| errorCode    | String | Yes | ... | `"<PREFIX>-1002"` |
| errorMessage | String | Yes | ... | `"Invalid field format: customerId"` |

## Common Error Responses     ← required [K11]; may hold zero rows
| Status | Response Code | Error Code | Error Messages | Description |
```

A passing root: `assets/testdata/good/opencollection.yml`.

- The common-lib error body is exactly `{responseCode, errorCode, errorMessage}`, all required
  Strings, separate from the success envelope. `errorMessage` is for logs and support, not customer
  wording. Keep leading zeroes in `responseCode`. The shared contract is
  [`errors.md`](../../init-project/assets/template/.kiro/steering/errors.md).
- `## Error Response Body` documents the error body the code renders (the common-lib body for a
  common-lib service). K11 NOTEs the sentence `Not documented in the source spec.`, left by older
  collections; Generate replaces it with that body.

---

## Request `docs:` (`<domain>/<endpoint>.yml`)

```markdown
## Purpose
<prose>

## Request
### Endpoint
`POST /v1/accounts/{accountId}/suspend`
### Auth
`None`
### Headers                  ← optional, field table
### Path Parameters          ← required when the path has {param}
### Query Parameters         ← optional
### Body (JSON)              ← optional, field table
### Example                  ← JSON block; required when Body (JSON) is present

## Response
### HTTP Status: 200         ← one per success status; prose allowed before the table
| Field Name | Type | Mandatory | Description | Possible Value |
### Example
### Error Responses          ← endpoint-specific errors only
| Status | Response Code | Error Code | Error Messages | Description |

## <free section>            ← e.g. Business Logic, Notes, SIT; ignored by the parser
```

- `## Purpose`, `## Request`, `### Endpoint`, `### Auth` and `## Response` are required [K2].
- At least one success `### HTTP Status: N` (N < 400) is required [K2].
- Each status has one `### HTTP Status: N` section; a duplicate is an ERROR [K2].
- A request that sends `http.body.data` needs a `### Body (JSON)` table followed by its `### Example` [K5].
- `### Endpoint` holds one `METHOD /path` line in the native `{param}` form. It must match
  `http.method` and `http.url` (`{id}` ↔ `:id`, `{{baseUrl}}` stripped) [K2].
- Path params agree across the Endpoint path, the `### Path Parameters` table and the
  `http.params` rows with `type: path` [K3].
- Every `http.params` row with `type: query` is also in the `http.url` query string [K13].
- A literal UUID in `http.url`, `http.params` or `http.body.data` is NOTEd for fresh-eyes: a record id is a `{{var}}` [K14].
- A request whose `### Auth` is `None` has no `http.auth` key, or `auth: inherit` while no enclosing `folder.yml` sets an auth; no file writes `auth: none` [K12].
- The parser reads only `##` and `###` headings. A request `### Example` counts only when it comes
  directly after `### Body (JSON)`; a response `### Example` belongs to the `### HTTP Status: N`
  above it. Each section's first table is the one parsed.
- A non-common-lib error body (a partner contract) gets its own `### HTTP Status: <4xx/5xx>`
  section with a field table. The common-lib body is never repeated per endpoint.
- `## Business Logic` is written from the usecase: only the steps it performs, in order.
- Every `docs:` statement traces to code. Where the code says nothing, the docs say nothing: a field
  without a comment gets a short neutral description, and no business meaning is guessed.

---

## Table rules

- Every field table (Headers, Path, Query, Body, Response) has exactly the columns
  `Field Name | Type | Mandatory | Description | Possible Value` [K4].
- `Type` ∈ `String`, `Number`, `Boolean`, `Object`, `Array`. `Mandatory` ∈ `Yes`, `No` [K4].
- Nesting is a dot-path: `data.accountId`, `items[].citizenId`. Every nested row has a parent row
  whose Type is `Object` (for `.`) or `Array` (for `[].`) [K4].
- A top-level array body (its Example is a JSON list) uses `[].x` rows; they need no parent row [K4].
- Escaped pipes (`\|`) inside a cell are part of the cell text. List enum values that way:
  `` `SA` \| `FD` ``.
- Error table columns are exactly `Status | Response Code | Error Code | Error Messages | Description` [K6].
  A common-lib code (`<PREFIX>-NNNN`, 2-3 uppercase letters and four digits) requires a
  Response Code that maps to Status per the common-lib table:
  `001`→400, `002`→400, `003`→404, `004`→409, `005`→503, `006`→504, `999`→500.
  A partner contract may leave Response Code blank.
- `Mandatory: Yes` means the field is always required. "Required when X" is `No`, with the condition
  in Description. In a response table, `Yes` means the key is always present; a pointer or
  `omitempty` field is `No`.
- Possible Value is a JSON literal in backticks (`` `"SA"` ``, `` `100` ``); object and array parent
  rows may say `see below` or `` `[{…}]` ``.
- Error Messages is a column title; the wire field stays `errorMessage`. Keep absent values blank;
  never derive a Response Code from Status or from prose (`001` and `002` are both 400).

### Examples against tables [K5]

- Every Example parses as JSON; `{{var}}` placeholders are allowed.
- Every key path in an Example has a row in its table.
- Every `Yes` row is present in the Example whenever its parent is present; an array parent counts as
  present only when the Example holds an element of it.
- `http.body.data` has the same key-path set as the Body Example. Values may differ.

---

## Audience

`docs:` is read by the teams that call this API (BFF, mobile, partner). It carries the wire
contract and caller-visible behaviour, not the owning team's working notes.

| Keep | Drop |
| --- | --- |
| wire names, types, Mandatory, examples | ticket IDs (`GI-3467`), AC-IDs (`AC-001`), decision IDs (`D-07`) |
| public error codes and when they occur | a `## Contract source` section |
| business rules a caller can observe | repo-internal paths (`internal/…`, `docs/knowledge/…`, `handler.go:42`) |
| retry and idempotency behaviour | decision logs, rename history, "user-confirmed" notes |

- K10 ERRORs on internal paths, `*.go:NN`, `AC-NNN`, `D-NN` and a `## Contract source` heading, in
  request, folder and root `docs:`. An `internal/` segment inside an HTTP path (`/v1/internal/x`) is not a leak.
- K10 NOTEs any `XX-NNNN` token that is not declared in an Error Code column. Regex cannot tell a
  ticket key (`GI-3467`) from an error code (`ACC-1001`), so the L2 verifier decides.
- Requests in the central `bruno-api-documents` repo that carry ticket IDs or a `Contract source`
  section match this layout but are not a model for Audience.

---

## Full example

`assets/testdata/good/account/create-account.yml`, which `brunocheck.py` passes:

````yaml
info:
  name: Create Account
  type: http
  seq: 10

http:
  method: POST
  url: "{{baseUrl}}/v1/accounts"
  body:
    type: json
    data: |-
      {
        "customerId": "{{customerId}}",
        "accountType": "SA",
        "items": [{"code": "X1"}]
      }

runtime:
  scripts:
    - type: tests
      code: |-
        test("status is 201", function() { expect(res.status).to.equal(201); });

settings:
  encodeUrl: true

docs: |-
  ## Purpose

  Open an account. Values are `SA` \| `FD`.

  ## Request

  ### Endpoint

  `POST /v1/accounts`

  ### Auth

  `None`

  ### Body (JSON)

  | Field Name | Type | Mandatory | Description | Possible Value |
  |---|---|---|---|---|
  | customerId | String | Yes | Owner | `"uuid-v4"` |
  | accountType | String | Yes | `SA` \| `FD` | `"SA"` |
  | items | Array | No | Extra items | `[{…}]` |
  | items[].code | String | Yes | Item code | `"X1"` |

  ### Example

  ```json
  {"customerId": "uuid-v4", "accountType": "SA", "items": [{"code": "X1"}]}
  ```

  ## Response

  ### HTTP Status: 201

  Created.

  | Field Name | Type | Mandatory | Description | Possible Value |
  |---|---|---|---|---|
  | status | String | Yes | Envelope status | `"Success"` |
  | data | Object | Yes | Payload | see below |
  | data.accountId | String | Yes | New id | `"uuid-v4"` |

  All fields are always present.

  ### Example

  ```json
  {"status": "Success", "data": {"accountId": "uuid-v4"}}
  ```

  ### Error Responses

  | Status | Response Code | Error Code | Error Messages | Description |
  |---|---|---|---|---|
  | 400 | 001 | FIX-1002 | Invalid field format | Malformed field |

  ## Business Logic

  1. Validate, then create.
````

A request with a path parameter: `assets/testdata/good/account/get-account.yml`.
