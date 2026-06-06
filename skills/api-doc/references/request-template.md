# Open Collection — Templates

Templates for every file this skill writes. Section ordering, indentation, and the markdown structure inside `docs:` are part of the contract — follow them exactly so output is byte-stable across runs.

For schema-level details on each key, see [`yaml-reference.md`](yaml-reference.md). For Go-side scanning and field/error rules referenced from the `docs:` markdown, read [`go-scan-patterns.md`](go-scan-patterns.md) and [`api-doc-template.md`](api-doc-template.md).

---

## 1. `opencollection.yml`

```yaml
opencollection: 1.0.0

info:
  name: <Service Name>

docs: |-
  # <Service Name> API

  <Overview — "<Service Name> provides APIs for <domain>. <one sentence on capabilities>.">

  ## Common Error Responses

  | Status | Error Message | Description |
  | ------ | ------------- | ----------- |
  | 400 | invalid request | Request body or query param invalid |
  | 401 | unauthorized | Missing or invalid authentication |
  | 403 | forbidden | Insufficient permissions |
  | 404 | not found | Resource does not exist |
  | 500 | internal server error | Unexpected server-side failure |

bundled: false

extensions:
  bruno:
    ignore:
      - node_modules
      - .git
```

**Variables in the template:**

| Placeholder | Source |
|-------------|--------|
| `<Service Name>` | CLAUDE.md project name, or `info.title` from go.mod if available. |
| `docs:` overview | CLAUDE.md/README project description → the `<Service> provides APIs for <domain>.` formula (see [`api-doc-template.md`](api-doc-template.md) § Index Template). |
| `docs:` Common Error Responses | The cross-cutting errors every endpoint can return (401/403/500 + generic 400/404). Per-endpoint error tables must NOT repeat these. |

> **Collection-root `docs:` is the service overview.** It replaces the old markdown `index.md`. The `publish` command syncs this block to the Confluence **parent page**. Keep it to overview + common errors — per-endpoint detail lives in each request's `docs:`.

---

## 2. `environments/<NAME>.yml`

One file per environment. Names are uppercase per steering convention.

```yaml
name: <ENV_NAME>
variables:
  - name: baseUrl
    value: <base-url-for-this-env>
  - name: <var-from-routes-or-middleware>
    value: ""
    secret: true
```

**Default environments to emit** (unless project config says otherwise):
- `LOCAL.yml` — `baseUrl: http://localhost:<port>` (read port from main.go / config; fallback `8080`)
- `SIT.yml` — `baseUrl: ""` (leave empty for the user)

**Variable discovery:**
1. Scan all route paths for `{{varName}}` placeholders — emit one variable per unique name.
2. Scan middleware headers and auth blocks for `{{varName}}` references — same.
3. Always emit `baseUrl`.
4. Mark as `secret: true` (and set `value: ""`) when the variable name matches: `token`, `auth_token`, `bearer`, `pin`, `otp`, `password`, `key`, `api_key`, `secret`, `biometric`, `national_id`, `cif`.

---

## 3. `folder.yml` (CoreTeam2 full style)

```yaml
info:
  name: <Group Display Name>
  type: folder
  seq: <N>

request:
  headers:
    - name: <header-name>
      value: <header-value-or-{{var}}>
  auth: <inherit | none | {type, ...}>
```

**Discovery rules:**

1. **`info.name`** — handler subdirectory name → Title Case (`consent` → `Consent`, `account_service` → `Account Service`).
2. **`info.seq`** — sequential order (10, 20, 30…) based on first appearance in the route registration file.
3. **`request.headers`** — dedup pass: any header sent by **every** request in this group goes here. Per-request headers stay in the request file. Common shared headers in this codebase: `Accept-Language`, `X-Device-ID`, `X-Device-Model`, `X-Platform`, `X-Client-Version`. If middleware always sets them, they live here.
4. **`request.auth`** — match the middleware applied to the route group:
   - JWT/Bearer middleware → `auth: { type: bearer, token: "{{auth_token}}" }`
   - API key middleware → `auth: { type: apikey, key: <header-name>, value: "{{api_key}}", placement: header }`
   - No auth middleware → `auth: none`
   - If the parent already declares the same auth → `auth: inherit`

Omit `request.headers` or `request.auth` entirely if there is nothing to lift — keep folder files minimal.

---

## 4. Request File (`<group>/<endpoint>.yml`)

Section order is fixed: **`info` → `http` → `settings` → `docs`**. No `runtime`, no `examples`.

```yaml
info:
  name: <Display Name>
  type: http
  seq: <N>

http:
  method: <METHOD>
  url: "{{baseUrl}}<path-with-:params>"
  params:
    - name: <param>
      value: <example-value-as-string>
      type: <path|query>
  headers:
    - name: <header-name>
      value: <value-or-{{var}}>
  body:
    type: json
    data: |-
      {
        "<field>": <example>
      }
  auth: inherit

settings:
  encodeUrl: true

docs: |-
  # <Display Name>

  <One-line description>

  - **Method:** `<METHOD>`
  - **Path:** `<path-with-{param}>`
  - **Auth:** `Bearer token` | `API Key` | `None`

  ## Path Parameters

  | Field Name | Description | Type | Mandatory | Example | Remark |
  | ---------- | ----------- | ---- | --------- | ------- | ------ |
  | `id` | Unique identifier of the consent | String | M | `"uuid-v4"` | |

  ## Query Parameters

  | Field Name | Description | Type | Mandatory | Example | Remark |
  | ---------- | ----------- | ---- | --------- | ------- | ------ |
  | `page` | Page number (1-based) | Number | O | `1` | Default: `1` |

  ## Request Body

  | Field Name | Description | Type | Mandatory | Example | Remark |
  | ---------- | ----------- | ---- | --------- | ------- | ------ |
  | `purpose_code` | Reference to purpose | String | M | `"MARKETING"` | |

  ## Request Example

  ```json
  {
    "purpose_code": "MARKETING"
  }
  ```

  ## Response (<HTTP Status> <Status Text>)

  | Field Name | Description | Type | Mandatory | Example | Remark |
  | ---------- | ----------- | ---- | --------- | ------- | ------ |
  | `id` | Unique identifier of the consent | String | M | `"uuid-v4"` | |
  | `status` | Current status | String | M | `"active"` | `"active"`, `"revoked"`, `"expired"` |
  | `created_at` | Timestamp when created | String | M | `"2024-01-01T10:00:00+07:00"` | |

  ## Response Example

  ```json
  {
    "id": "uuid-v4",
    "status": "active",
    "created_at": "2024-01-01T10:00:00+07:00"
  }
  ```

  ## Business Logic

  1. Validate that referenced Purpose exists and is active
  2. Check for existing consent for this Citizen + Purpose combination
  3. Create new Consent record with status `active`
  4. Create audit log entry for consent creation
  5. Send notification to data subject via notification service

  ## Error Responses

  | Status | Error Message | Description |
  | ------ | ------------- | ----------- |
  | 400 | invalid request | Request body validation failed |
  | 404 | purpose not found | Referenced purpose does not exist |
  | 422 | purpose is not active | Business rule violation |
  | 500 | internal server error | Server-side failure |
```

---

## 5. `docs:` Markdown — Section Rules

The `docs:` block inside each request file is a faithful copy of the per-endpoint template in [`api-doc-template.md`](api-doc-template.md) — **without** the breadcrumb line. Use H1 for the endpoint name (it is the top-level heading of an embedded doc).

All field/error rules below come from [`api-doc-template.md`](api-doc-template.md). Do **not** redefine them here; pull from there. Below is the short version for cross-reference.

### 5.1 Header bullets

```
- **Method:** `<METHOD>`
- **Path:** `<path-with-{param}>`     ← documented path uses {param}, not :param
- **Auth:** `Bearer token` | `API Key` | `None`
```

The documented path always uses `{param}` braces (the human-readable doc convention), even though the YAML URL uses `:param` for Bruno. Two different audiences: humans read `{}`, Bruno's runner reads `:`.

### 5.2 Field tables

Columns are always exactly:

```
| Field Name | Description | Type | Mandatory | Example | Remark |
```

Apply [`api-doc-template.md`](api-doc-template.md) § Field Table Conventions for:
- **M/O classification** — `binding:"required"` → M, pointer → O, `omitempty` → O, **`bool` without required → O**, non-pointer non-bool without required → M
- **Field descriptions** — apply the 9-rule table top-down, first match wins
- **Example values** — UUID → `"uuid-v4"`, enum → first value, timestamp → `"2024-01-01T10:00:00+07:00"`, boolean → `true`, names → fixed realistic value from the lookup table
- **Remark column** — enum values listed, defaults noted, length/range constraints noted, empty otherwise
- **Row ordering** — Go struct field order, embedded struct fields first
- **Nested objects** — emit a sub-table titled `**<GoTypeName> Object:**`

**Table formatting rule:** single space between `|` and content. Don't pad columns. This makes the output byte-identical across runs.

### 5.3 Examples (Request Example / Response Example)

Fenced JSON code block with the same example values used in the field-table `Example` column. Include all mandatory fields and at least one optional field. JSON must be valid (no trailing commas, correct types).

### 5.4 Business Logic

Numbered list, one step per distinct action.

- **Priority 1 — header comments:** if the usecase function has a `### Logical` comment with `Step N:` lines, transcribe verbatim. Sub-steps (`Step 4.1:`) become nested list items.
- **Priority 2 — code-derived:** apply the counting rules from [`go-scan-patterns.md`](go-scan-patterns.md) § Step Classification Examples — repo/service/external calls, sentinel-returning `if`/`switch` (even inside loops), state-changing side effects count as 1 step each. Error propagation, stdlib calls, struct construction, entity mutation without I/O, logging, metrics, context enrichment, early success returns, and final returns do **not** count.

### 5.5 Error Responses

Columns:

```
| Status | Error Message | Description |
```

Row ordering:
1. Handler-level errors (400 bind, 400 param parse, 422 validation) — ascending status
2. Usecase typed errors — in handler `errors.Is` switch order, or code order if no switch
3. Domain service typed errors — placed immediately after the usecase error that triggers the service call
4. Catch-all 500 — always last

**Error Message column** uses the exact format string from `errs.UseCasef("…")` / `errors.New("…")` etc., with `%s/%d/%.1f` replaced by `{placeholder}` named after the variable. Never invent generic placeholders.

---

## 6. Path Parameter Handling

This is the part most people get wrong. The same path parameter appears in **three** places:

| Place | Form | Why |
|-------|------|-----|
| `http.url` (YAML string) | `:id` | Bruno's runner reads this to identify path params for substitution. |
| `http.params` (YAML list) | `name: id, type: path` | Required so Bruno's UI shows an editable param field. |
| `docs:` markdown (Path Parameters table + Path bullet) | `{id}` | Human-readable doc convention. |

Regardless of the framework's syntax in source code (`/:id` for Gin/Chi/Echo, `/{id}` for Gorilla, `/:id` for Fiber), the generator always normalizes:
- `:id` in the YAML URL string
- `name: id, type: path` in the params block
- `{id}` in the documented path inside `docs:`

---

## 7. `seq` Assignment

- **Folders** — assigned in route-registration order. First group declared → `seq: 10`, second → `seq: 20`, etc.
- **Requests inside a folder** — assigned in handler-file order (which usually matches route declaration order). First request → `seq: 10`, second → `seq: 20`, etc.
- **Gaps of 10** let the user (or a later update) insert a new entry without renumbering siblings.
- **Update mode:** when adding a new request to an existing folder, find the highest `seq` and assign `seq + 10`. Don't try to slot it between existing ones — that creates noisy diffs.
- `seq` is **per-folder** and per-collection-level. Don't try to make it globally unique.

---

## 8. Display Names

| Where | Rule | Example |
|-------|------|---------|
| `info.name` in request | PascalCase → space-separated, no articles | `AcceptConsent` → `Accept Consent` |
| `info.name` in folder | Subdirectory name → Title Case | `consent` → `Consent`; `account_service` → `Account Service` |
| Filename | PascalCase → kebab-case, strip trailing `Handler` | `AcceptConsentHandler` → `accept-consent.yml` |
| `docs:` H1 | Same as `info.name` of the request | `Accept Consent` |
| `docs:` description line | `<Verb> <resource>[ by/for <qualifier>]`, no articles, max 10 words | `Create consent`, `Retrieve consent by ID`, `List channels` |

Verb mapping from HTTP method (for the description line): POST → Create, GET (single) → Retrieve, GET (list) → List, PUT → Update, PATCH → Partially update, DELETE → Delete.
