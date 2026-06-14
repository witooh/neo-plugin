# OpenAPI 3.2 Spec Templates

Templates for a **split OpenAPI 3.2.0 spec**. The output is a directory: a root document plus one Path Item file per URL path and one schema file per Go type, wired with `$ref`.

```
docs/openapi/
├── openapi.yaml                       ← Root: openapi/info/servers/tags/paths-$refs/components
├── paths/
│   └── <group>/<path>.yaml            ← one Path Item Object per URL path (all its methods)
└── components/
    ├── schemas/<GoTypeName>.yaml       ← one schema per Go type
    └── responses/<CommonError>.yaml    ← shared error responses (401/403/404/500/400)
```

**Target version:** `openapi: 3.2.0` (JSON-Schema 2020-12 dialect — union-type nullability, `examples` arrays). Do **NOT** use the OpenAPI 3.0 `nullable: true` keyword or the singular schema-level `example:` (both are wrong/deprecated for 3.1+).

**File granularity — one Path Item per distinct URL path.** OpenAPI keys a path to exactly one Path Item Object, so all HTTP methods on the same path live in **one** file (unlike api-doc's one-file-per-handler). Most resources have distinct paths per endpoint, so this usually collapses to one endpoint per file; when a path carries two methods (e.g. `GET` + `DELETE` on `/consents/{id}`), both operations share the file. Group folder = handler group, same as api-doc.

**File naming** — kebab of the path within the group, params rendered `by-<param>`, trailing action kept: `/channels` → `channels.yaml`, `/channels/{id}` → `channels-by-id.yaml`, `/consents/{id}/revoke` → `consents-by-id-revoke.yaml`.

**Path params** — native OpenAPI `{param}` form (no `:id` conversion).

---

## Root Template (`docs/openapi/openapi.yaml`)

```yaml
openapi: 3.2.0
info:
  title: <Service Name> API
  version: "<X.Y>"
  description: >
    <Service name> provides APIs for <domain>. <One sentence about main capabilities>.
servers:
  - url: /api/v1
tags:
  - name: Consent
    description: <one line on the group>
  - name: Channel
    description: <one line on the group>
paths:
  /consents:
    $ref: "./paths/consent/consents.yaml"
  /consents/{citizen_id}:
    $ref: "./paths/consent/consents-by-citizen.yaml"
  /consents/{id}:
    $ref: "./paths/consent/consents-by-id.yaml"
  /consents/{id}/revoke:
    $ref: "./paths/consent/consents-by-id-revoke.yaml"
  /channels:
    $ref: "./paths/channel/channels.yaml"
components:
  securitySchemes:
    bearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
    apiKey:
      type: apiKey
      in: header
      name: X-API-Key
  responses:
    Unauthorized:
      $ref: "./components/responses/Unauthorized.yaml"
    Forbidden:
      $ref: "./components/responses/Forbidden.yaml"
    NotFound:
      $ref: "./components/responses/NotFound.yaml"
    InternalServerError:
      $ref: "./components/responses/InternalServerError.yaml"
```

- `info.title` = `<Service> API`; `info.version` = the API version from `CLAUDE.md`/router; `info.description` = the overview paragraph (≤2 sentences, `<Service> provides APIs for <domain>.` pattern — same rule as api-doc's index overview).
- `servers[].url` = the versioned base (e.g. `/api/v1`); each `paths` key is the path **relative to that base** (so `/api/v1/consents` → key `/consents`).
- `tags[]` = one per handler group (Title Case), mirrors api-doc's group sections.
- `paths` maps each URL path to a `$ref` of its Path Item file.
- Common errors (the api-doc "Common Error Responses" that live in `index.md` only) → `components.responses`, each a `$ref` to a file under `components/responses/`. Per-endpoint operations reference these instead of redeclaring 401/403/etc.

---

## Path Item Template (`docs/openapi/paths/<group>/<path>.yaml`)

One file = one Path Item Object = all methods for that URL path.

```yaml
post:
  tags: [Consent]
  summary: Accept Consent
  description: Create consent for citizen.
  operationId: acceptConsent
  security:
    - bearerAuth: []
  x-business-logic:
    - step: 1
      text: Validate that referenced Purpose exists and is active
    - step: 2
      text: Check for existing consent for this Citizen + Purpose combination
    - step: 3
      text: Create new Consent record with status active
    - step: 4
      text: Create audit log entry for consent creation
    - step: 5
      text: Send notification to data subject via notification service
  requestBody:
    required: true
    content:
      application/json:
        schema:
          $ref: "../../components/schemas/AcceptConsentRequest.yaml"
        examples:
          default:
            value:
              field_name: example_value
              items:
                - code: CODE1
                - code: CODE2
                  value: abc
              flag: true
  responses:
    "201":
      description: Consent created
      content:
        application/json:
          schema:
            $ref: "../../components/schemas/ConsentResponse.yaml"
          examples:
            default:
              value:
                id: uuid-v4
                status: active
                created_at: "2024-01-01T10:00:00+07:00"
    "400":
      $ref: "../../components/responses/BadRequest.yaml"
    "422":
      description: Business rule violation
      content:
        application/json:
          schema:
            $ref: "../../components/schemas/Error.yaml"
      x-error-catalog:
        - status: 422
          message: purpose not found
          meaning: Referenced purpose does not exist or is inactive
        - status: 422
          message: consent already exists
          meaning: Duplicate consent for this citizen + purpose
    "401":
      $ref: "../../components/responses/Unauthorized.yaml"
    "500":
      $ref: "../../components/responses/InternalServerError.yaml"
```

- **`summary`** = endpoint display name, exact PascalCase split, no articles (`AcceptConsent` → `Accept Consent`).
- **`description`** = the `<Verb> <resource>[ by/for <qualifier>]` line (verb from HTTP method: POST→Create, GET-single→Retrieve, GET-list→List, PUT→Update, PATCH→Partially update, DELETE→Delete), ≤10 words, CommonMark.
- **`operationId`** = lowerCamelCase of the handler function name (stable, unique).
- **`tags`** = `[<Group>]`.
- **`security`** = `[{bearerAuth: []}]` (JWT/Bearer) | `[{apiKey: []}]` (API key) | `[]` (none — explicit empty array).
- **`x-business-logic`** — see § x-business-logic.
- **`requestBody`** — omit entirely when the endpoint takes no body. `required: true` unless the body is optional. Schema is a `$ref`; the whole runnable JSON body goes in `examples.default.value` **verbatim** (so `open-collection`/Bruno get an intact runnable body).
- **`responses`** — success status from the handler's actual return (`c.JSON(NNN,…)`, not guessed). `204 No Content` → a `"204": { description: No Content }` with no content block. Error statuses → see § Error Responses.

---

## Schema Component Template (`docs/openapi/components/schemas/<GoTypeName>.yaml`)

One file per Go type. File name = the Go type name **as-is** (`AcceptConsentRequest.yaml`, `ConsentItem.yaml`) — never abbreviate/rename.

```yaml
type: object
required: [field_name, items]
properties:
  field_name:
    type: string
    description: What this field does
    examples: [example_value]
  items:
    type: array
    description: List of item objects
    items:
      $ref: "./ConsentItem.yaml"
  flag:
    type: boolean
    description: Whether the flag is set
    examples: [true]
```

- **`required: [...]`** lists the json names of all **M** fields (see § M/O). Omit the key entirely if no field is mandatory.
- **`properties`** in **Go struct field order** (embedded fields first — see § Property Ordering).
- Each property carries `type`, `description`, and `examples` (array form); plus `enum`, `items`, `format`, `default` where applicable.

---

## Go → OpenAPI 3.2 mapping (master table)

| api-doc rule (markdown) | OpenAPI 3.2 target |
|---|---|
| `# <Name>` heading | operation `summary` (PascalCase split) |
| description line | operation `description` (CommonMark) |
| `- **Method:**` / `- **Path:**` | the `paths.<path>.<httpMethod>` location itself |
| `- **Auth:**` | operation `security` + a scheme in `components.securitySchemes` |
| Business Logic steps | operation **`x-business-logic`** |
| Path Parameters table | `parameters[]` with `in: path`, `required: true` |
| Query Parameters table | `parameters[]` with `in: query`, `required` from M/O, `schema.default` for defaults |
| Request Body table | `requestBody.content.application/json.schema` → `$ref` schema file |
| Request Example (json) | `requestBody.content.*.examples.default.value` (verbatim) |
| Response (NNN) field table | `responses.<NNN>.content.application/json.schema` → `$ref` schema file |
| Response Example (json) | `responses.<NNN>.content.*.examples.default.value` (verbatim) |
| Error Responses table | `responses.<NNN>` per status + **`x-error-catalog`** for per-sentinel detail |
| Field row → property | `properties.<json>` with `type`/`description`/`examples` |
| Mandatory (M/O) | membership in the schema's `required: [...]` array |
| Nested `**X Object:**` sub-table | separate `components/schemas/X.yaml` + `$ref` |
| Embedded struct (e.g. `BaseResponse`) | `allOf: [{$ref: Base}, {type: object, ...}]` |
| Wrapper envelope `{success,data,message}` | wrapper schema whose `data` `$ref`s the inner schema |
| `index.md` header/overview/common-errors | root `info` + `servers` + `tags` + `components.responses` |

---

## Type mapping (Go → OpenAPI `schema.type`)

| Go type | OpenAPI |
|---|---|
| `string` | `type: string` |
| `int`, `int8…int64`, `uint…` | `type: integer` (add `format: int64` for 64-bit) |
| `float32`, `float64` | `type: number` (`format: float`/`double`) |
| `bool` | `type: boolean` |
| `time.Time` | `type: string`, `format: date-time` |
| `[]T` | `type: array`, `items:` (`$ref` if `T` is a struct) |
| `map[string]T` | `type: object`, `additionalProperties:` |
| named struct `T` | `$ref: "./T.yaml"` |
| `*T` (pointer) | the `T` mapping, **excluded from `required[]`** (see Nullability) |
| custom `type X string` + const block | `type: string`, `enum: [...]` (all const values) |

### Nullability (3.2 — JSON-Schema union types, NOT `nullable:`)
- A field that may serialize JSON `null` → `type: ["<base>", "null"]`, e.g. `type: ["string", "null"]`.
- A pointer/`omitempty` field that is simply *absent* (not present-but-null) → keep the singular type and **leave it out of `required[]`**.
- Do **not** emit `nullable: true` (3.0-only) and do **not** use a singular schema-level `example:` — always `examples: [ ... ]`.

---

## M/O Classification → `required[]`

A field's Mandatory/Optional status (the rules live in [`go-scan-patterns.md`](go-scan-patterns.md) §Extracting Request/Response Structs) decides **only** one thing here: whether its json name appears in the schema's `required` array.

**Request schemas:**

| Condition | M/O | `required[]` |
|---|---|---|
| Has `binding:"required"` or `validate:"required"` | M | listed |
| Pointer type (`*string`, `*int`, …) | O | omitted |
| Has `json:",omitempty"` without required | O | omitted |
| `bool` WITHOUT `binding:"required"` | O | omitted |
| Non-pointer, non-bool, WITHOUT required | M | listed |

**Response schemas:** pointer → O (omitted); non-pointer → M (listed).

`bool` without `required` is O because Go's `json.Unmarshal` leaves it `false` when absent — the sender may omit it. Query params from inline `c.Query(...)`: `required: false` by default, `true` only if the handler returns an error when the param is empty (read the handler — this is a fresh-eyes judgment, flagged NOTE by L1).

---

## Property Ordering (mandatory)

Follow Go struct field order:
1. Embedded struct fields first — modeled via `allOf` (referenced base) OR expanded in declaration order if not separately modeled.
2. Then the struct's own fields in declaration order.
3. For `parameters[]`: path params (path order) before query params; struct-based query params (struct order) before inline `c.Query()` params (handler first-appearance order); a param extracted both ways appears once.

Within each schema file, `properties` keys are emitted in this order (YAML preserves it). Keep key order **byte-stable** across runs.

---

## x-business-logic (operation extension)

Structured list of business-logic steps. Standard OpenAPI tools ignore `x-*`; `confluence-api-doc` parses this back into the page's Business Logic section, so it must be faithful.

```yaml
x-business-logic:
  - step: 1
    text: Validate that referenced Purpose exists and is active
  - step: 4
    text: Persist the consent
    substeps:
      - "4.1 Write the consent row"
      - "4.2 Write the audit log"
```

- **Source & counting are rule-bound** (single source: [`go-scan-patterns.md`](go-scan-patterns.md) §Usecase Header Comment Detection + §Step Classification Examples). Priority 1: transcribe `### Logical` / `Step N:` header comments **verbatim** (one list entry per `Step N:`, sub-steps `4.1/4.2` → `substeps`). Priority 2 (no comments): code-derived — 1 step per repo/service/external call and per sentinel-returning `if`/`switch`; a repo call + its nil-check = 2 steps; NOT a step: error propagation, stdlib, struct construction, entity mutation without I/O, logging, metrics, early/final return.
- `text` is one line per step; never add, drop, merge, or reword a Priority-1 step.

---

## Error Responses (`responses` + x-error-catalog)

OpenAPI keys responses by **status code**, but api-doc lists **one row per sentinel** even when several share a status. To keep that fidelity, each error status gets one `responses.<NNN>` entry, and where multiple distinct sentinels share that status they are enumerated in **`x-error-catalog`** (which `confluence-api-doc` renders back into the Error Responses table):

```yaml
responses:
  "422":
    description: Business rule violation
    content:
      application/json:
        schema:
          $ref: "../../components/schemas/Error.yaml"
    x-error-catalog:
      - status: 422
        message: purpose not found
        meaning: Referenced purpose does not exist
      - status: 422
        message: consent already exists
        meaning: Duplicate consent for this citizen + purpose
```

Rules (single source for tracing/consolidation/order: [`go-scan-patterns.md`](go-scan-patterns.md) §Error Tracing Patterns + §Consolidation Rules):
- One sentinel = one `x-error-catalog` entry (even when several share a status); `message` matches the actual code string; dedup the same sentinel from multiple methods.
- Wrapped repo/external errors → a single catch-all `"500"` (`$ref` `InternalServerError.yaml`); do not trace into repos.
- Generic 401/403/404/500 → `$ref` the shared `components/responses/*.yaml`; do not redeclare per endpoint.
- Status-key order ascending; within a status, `x-error-catalog` follows the api-doc Rule 5 order (handler errors → usecase sentinels [switch order or code order] → domain-service errors → catch-all).

---

## Shared error responses (`components/responses/<CommonError>.yaml`)

One file per common error, referenced from both the root `components.responses` and per-operation `responses`:

```yaml
# components/responses/Unauthorized.yaml
description: Missing or invalid authentication
content:
  application/json:
    schema:
      $ref: "../schemas/Error.yaml"
```

Provide at least `Unauthorized` (401), `Forbidden` (403), `NotFound` (404), `BadRequest` (400), `InternalServerError` (500), plus a shared `Error` schema:

```yaml
# components/schemas/Error.yaml
type: object
required: [message]
properties:
  message:
    type: string
    description: Error message
    examples: [invalid request]
```

---

## Wrapper / envelope composition

When the handler wraps the payload (`{success, data, message}`), model the envelope as its own schema whose `data` `$ref`s the inner type (don't inline-duplicate the inner fields):

```yaml
# components/schemas/ConsentEnvelope.yaml
type: object
required: [success, data]
properties:
  success:
    type: boolean
    examples: [true]
  data:
    $ref: "./ConsentResponse.yaml"
  message:
    type: ["string", "null"]
    description: Optional message
    examples: ["null"]
```

List envelopes: `data: { type: array, items: { $ref: "./ConsentResponse.yaml" } }` plus `total`/`page` props. The operation's `responses.<NNN>.schema` then `$ref`s the envelope, and the `examples.default.value` shows the full wrapped shape.

---

## Embedded struct → allOf

A struct embedding another (e.g. `ConsentResponse` embeds `BaseResponse`) composes via `allOf`:

```yaml
# components/schemas/ConsentResponse.yaml
allOf:
  - $ref: "./BaseResponse.yaml"
  - type: object
    required: [id, status]
    properties:
      id:
        type: string
        description: Unique identifier of the consent
        examples: [uuid-v4]
      status:
        type: string
        enum: [active, inactive, revoked]
        description: Current status
        examples: [active]
```

If the embedded base is not separately modeled, expand its fields inline (in declaration order, before the own fields).

---

## Field `description` formulas

Populate each property's `description` from the Go field name (apply the FIRST matching rule; max 8 words; factual only; do not inject qualifiers the formula doesn't specify):

| # | Pattern | Formula | Result |
|---|---|---|---|
| 1 | `id` (own PK) | `Unique identifier of the <entity>` | `Unique identifier of the consent` |
| 2 | `*_id` FK | `Reference to <entity>` | `Reference to purpose` |
| 3 | `*_id` non-FK (natural id) | split to words, keep `ID` upper | `citizen_id` → `Citizen ID` |
| 4 | `*_at` timestamp | `Timestamp when <past-tense action>` | `Timestamp when created` |
| 5 | `status` exact | `Current status` | `Current status` |
| 6 | `name`+suffix (`nameTH`) | `Name in <suffix expansion>` | `Name in Thai` |
| 7 | `name` exact | `Name of the <entity>` | `Name of the channel` |
| 8 | Boolean | `Whether <condition from field name>` | `Whether consent is active` |
| 9 | Other | split camelCase/snake_case → words. `No`→number, `TH`→Thai, `EN`→English; unknown abbrev → struct comment, else keep uppercase | `mobileNo` → `Mobile number` |

---

## Example value conventions (for `examples: [...]`)

Same deterministic conventions as api-doc, emitted as the single element of the property's `examples` array (and assembled into the operation-level `examples.default.value` body/response):

| Type | Convention | Value |
|---|---|---|
| UUID (id PK, `*_id` FK) | fixed placeholder | `uuid-v4` |
| String (enum / `status`) | first enum const | `active` |
| String (name/label) | fixed realistic (lookup) | Thai person `สมชาย ใจดี`; EN person `Somchai Jaidee`; entity TH `ช่องทางตัวอย่าง`; phone `0812345678`; email `user@example.com`; URL `https://example.com/callback`; citizen id `1234567890123`; code `CODE001` |
| Number (no default) | smallest typical positive | `1` |
| Number (with default) | the default | `20` |
| Boolean | always | `true` |
| Timestamp | fixed template | `2024-01-01T10:00:00+07:00` |
| Array | exactly 1 item | `[{...}]` |
| Null/absent | `null` when primarily absent | `null` |

**Validation-aware:** after choosing a value, make it satisfy the field's `validate` tag (`alpha`→letters only, `numeric`→digits, `email`/`url`→formats, `len=N`→exact length, `oneof=a b c`→a listed value, `min/max`→range). Mirror constraints into the schema too where natural (`minLength`/`maxLength`/`minimum`/`maximum`/`enum`/`format`).

---

## `$ref` wiring conventions (pin — keep byte-stable)

- Root `paths.<path>` → `"./paths/<group>/<file>.yaml"`.
- Root `components.responses.<X>` → `"./components/responses/<X>.yaml"`.
- Path file → schema: `"../../components/schemas/<Name>.yaml"`.
- Path file → shared response: `"../../components/responses/<Name>.yaml"`.
- Schema file → schema (same dir): `"./<Name>.yaml"`.
- Shared response → schema: `"../schemas/<Name>.yaml"`.
- Always relative file paths (no JSON-pointer-into-root); quote the `$ref` value.

---

## Byte-stable YAML rules

For clean Update-mode diffs and a simple L1 `$ref` check:
- 2-space indentation, block style (no flow `{}`/`[]` except short inline examples and scalar arrays like `enum`/`required`/`examples`).
- Fixed key order per object kind: **operation** = `tags, summary, description, operationId, security, x-business-logic, parameters, requestBody, responses`; **schema** = `type, format, enum, required, properties, items, allOf, additionalProperties, description, examples`; **parameter** = `name, in, required, description, schema, example`.
- Quote version strings (`version: "1.0"`) and any value that YAML could mis-type.
- One trailing newline; no trailing whitespace.

---

## Verification Checklist

**Single source of truth** for *what* must be checked — referenced by the `openapi-doc` skill's Step 4 + Validate Mode. Do not duplicate elsewhere; reference this.

> **Three-layer coverage.** `assets/speccheck.py` (**L1**, deterministic) mechanically covers: root/operation well-formedness · `$ref` resolution · route↔path-file coverage & root-`paths` linkage · property **count** vs Go struct (embedded expanded) · **`required[]`** vs tags · security-scheme resolution · inline-example JSON validity · (optional) a real validator if one is on PATH. The **L2** fresh-eyes verifier (`openapi-doc-verifier.md`) covers judgment: error tracing + `x-error-catalog`, `x-business-logic` step counting, custom-type enums, every `description`/`examples`/nullable detail, property order, success status, security mapping, example shape. **L3** re-derives the route inventory from the router to catch a whole path silently dropped. L1 prints whatever it cannot resolve as a `NOTE` to focus L2.

### Coverage & Structure
- [ ] Every route in code has a Path Item file, and every path file maps to a real route (no orphan)
- [ ] Every path file is `$ref`'d from the root `paths:`; every `$ref` (paths/schemas/responses) resolves to an existing file
- [ ] Handler group structure matches `paths/<group>/` folders
- [ ] `openapi: 3.2.0`; `info.title`/`info.version` present; `servers` set
- [ ] Each operation has `summary`, `description`, `operationId`, `responses` (≥1 success 2xx)
- [ ] Inline `examples.*.value` JSON is valid

### Schema Completeness (critical — open struct source files)
- [ ] Every serializable struct field (exclude `json:"-"` + unexported) has a `properties` entry — none skipped
- [ ] `required[]` correct per tags: required→listed, pointer→omitted, omitempty→omitted, **bool-without-required→omitted**, non-ptr-non-bool→listed
- [ ] Embedded structs via `allOf` (or expanded in order); nested types each have their own `components/schemas/<GoType>.yaml` + `$ref`
- [ ] Custom types → `type: string` + full `enum`
- [ ] Pointer/null-capable fields use `type: ["<t>","null"]` and/or are omitted from `required[]` (no `nullable:`)
- [ ] Wrapper envelope modeled with `data` `$ref` if the handler wraps the payload
- [ ] Inline `c.Query()` params present; `required:false` by default, `true` only if the handler errors when empty
- [ ] Property order follows Go struct field order (embedded first)
- [ ] `description` follows the formula table; `examples` follow the value conventions and satisfy the `validate` tag
- [ ] `examples.default.value` (request & response) includes all mandatory + ≥1 optional field and reflects the real (wrapped) shape

### Business Logic (critical — open ALL usecase methods)
- [ ] Source determined (Priority 1 header comments vs Priority 2 code-derived); `x-business-logic` step count matches the source; Priority-1 steps verbatim; conditional branches documented

### Response Metadata (critical)
- [ ] Success status key matches the handler's actual return (not guessed)
- [ ] `security` matches the route middleware and references a defined `securitySchemes` entry

### Error Completeness (critical — open ALL usecase AND domain-service methods)
- [ ] Every distinct sentinel has an `x-error-catalog` entry (one per sentinel even when sharing a status); messages match code strings; same sentinel deduped
- [ ] Wrapped repo/external → single catch-all `"500"`; generic 401/403/404 → shared `components/responses` `$ref`
- [ ] Status keys ascending; `x-error-catalog` order = handler errors → usecase sentinels → domain-service errors → catch-all

### Text Consistency
- [ ] `summary` = exact PascalCase split, no articles; `description` = `<Verb> <resource>`, verb from method, ≤10 words
- [ ] `info.description` ≤2 sentences, `<Service> provides APIs for <domain>.` pattern
