# OpenAPI 3.1 Spec Template

Template for a **single-file OpenAPI 3.1.0 spec**. The output is ONE document — `bruno/openapi.yaml` — holding `info`/`servers`/`tags`, every path inline under `paths:`, and every schema + shared response under `components:`, wired with **internal `$ref`** (`#/components/schemas/<Type>`). One self-contained file renders in any viewer (Bruno API Designer, Swagger Editor) with no external fetch.

```
bruno/openapi.yaml    ← the whole spec: openapi/info/servers/tags + paths (inline) + components (schemas + responses + securitySchemes)
```

**Target version:** `openapi: 3.1.0` (JSON-Schema 2020-12 dialect — union-type nullability, `examples` arrays, `oneOf`). Do **NOT** use the OpenAPI 3.0 `nullable: true` keyword or the singular schema-level `example:` (both are wrong/deprecated for 3.1). Do **not** emit `3.2.0` either — current tooling (Bruno's importer, Swagger, Redocly) does not yet recognize it and rejects the document; 3.1.0 covers every feature here.

**Single document — everything inline.** Paths live directly under `paths:` (no per-path files); schemas live under `components.schemas` (no per-type files); shared errors under `components.responses`. They reference each other with **internal JSON-pointer `$ref`** (`#/components/schemas/<Type>`), which resolves within the one document in every tool. A path that carries two methods (e.g. `GET` + `DELETE` on `/consents/{id}`) lists both operations under that one path key.

**Path params** — native OpenAPI `{param}` form (no `:id` conversion).

---

## Document skeleton (`bruno/openapi.yaml`)

```yaml
openapi: 3.1.0
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
    post:
      # … operation … (see § Operation)
  /consents/{id}:
    get:
      # …
    delete:
      # …
  /consents/{id}/revoke:
    post:
      # …
  /channels:
    get:
      # …
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
  responses:                       # shared common errors (see § Shared error responses)
    Unauthorized: { … }
    Forbidden: { … }
    NotFound: { … }
    BadRequest: { … }
    InternalServerError: { … }
  schemas:                         # one entry per Go type (see § Schema)
    AcceptConsentRequest: { … }
    ConsentResponse: { … }
    Error: { … }
```

- `info.title` = `<Service> API`; `info.version` = the API version from `CLAUDE.md`/router; `info.description` = the overview paragraph (≤2 sentences, `<Service> provides APIs for <domain>.` pattern).
- `servers[].url` = the versioned base (e.g. `/api/v1`); each `paths` key is the path **relative to that base** (so `/api/v1/consents` → key `/consents`).
- `tags[]` = one per handler group (Title Case).
- `paths` maps each URL path to an **inline** Path Item Object (all its methods).
- `components.schemas` = one entry per Go type; `components.responses` = shared common errors; `components.securitySchemes` = the auth schemes. Operations reference these via `#/components/...`.

---

## Operation (a `paths.<path>.<method>` entry)

Each HTTP method on a path is one Operation Object, written inline under its path key.

```yaml
post:
  tags: [Consent]
  summary: Accept Consent
  description: Create consent for citizen.
  operationId: acceptConsent
  security:
    - bearerAuth: []
  requestBody:
    required: true
    content:
      application/json:
        schema:
          $ref: "#/components/schemas/AcceptConsentRequest"
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
            $ref: "#/components/schemas/ConsentResponse"
          examples:
            default:
              value:
                id: uuid-v4
                status: active
                created_at: "2024-01-01T10:00:00+07:00"
    "400":
      $ref: "#/components/responses/BadRequest"
    "422":
      description: Business rule violation
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/Error"
      x-error-catalog:
        - status: 422
          message: purpose not found
          meaning: Referenced purpose does not exist or is inactive
        - status: 422
          message: consent already exists
          meaning: Duplicate consent for this citizen + purpose
    "401":
      $ref: "#/components/responses/Unauthorized"
    "500":
      $ref: "#/components/responses/InternalServerError"
```

- **`summary`** = endpoint display name, exact PascalCase split, no articles (`AcceptConsent` → `Accept Consent`).
- **`description`** = the `<Verb> <resource>[ by/for <qualifier>]` line (verb from HTTP method: POST→Create, GET-single→Retrieve, GET-list→List, PUT→Update, PATCH→Partially update, DELETE→Delete), ≤10 words, CommonMark.
- **`operationId`** = lowerCamelCase of the handler function name (stable, unique).
- **`tags`** = `[<Group>]`.
- **`security`** = `[{bearerAuth: []}]` (JWT/Bearer) | `[{apiKey: []}]` (API key) | `[]` (none — explicit empty array).
- **`requestBody`** — omit entirely when the endpoint takes no body. `required: true` unless the body is optional. Schema is an internal `$ref`; the whole runnable JSON body goes in `examples.default.value` **verbatim** (so `open-collection`/Bruno get an intact runnable body).
- **`responses`** — success status from the handler's actual return (`c.JSON(NNN,…)`, not guessed). `204 No Content` → a `"204": { description: No Content }` with no content block. Error statuses → see § Error Responses.

---

## Schema (a `components.schemas.<GoTypeName>` entry)

One entry per Go type, keyed by the Go type name **as-is** (`AcceptConsentRequest`, `ConsentItem`) — never abbreviate/rename.

```yaml
AcceptConsentRequest:
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
        $ref: "#/components/schemas/ConsentItem"
    flag:
      type: boolean
      description: Whether the flag is set
      examples: [true]
```

- **`required: [...]`** lists the json names of all **M** fields (see § M/O). Omit the key entirely if no field is mandatory.
- **`properties`** in **Go struct field order** (embedded fields first — see § Property Ordering).
- Each property carries `type`, `description`, and `examples` (array form); plus `enum`, `items`, `format`, `default` where applicable. Nested struct types → internal `$ref: "#/components/schemas/<Type>"`.

---

## Go → OpenAPI 3.1 mapping (master table)

| Documented element | OpenAPI 3.1 target |
|---|---|
| `# <Name>` heading | operation `summary` (PascalCase split) |
| description line | operation `description` (CommonMark) |
| `- **Method:**` / `- **Path:**` | the `paths.<path>.<httpMethod>` location itself |
| `- **Auth:**` | operation `security` + a scheme in `components.securitySchemes` |
| Path Parameters table | `parameters[]` with `in: path`, `required: true` |
| Query Parameters table | `parameters[]` with `in: query`, `required` from M/O, `schema.default` for defaults |
| Request Body table | `requestBody.content.application/json.schema` → `#/components/schemas` `$ref` |
| Request Example (json) | `requestBody.content.*.examples.default.value` (verbatim) |
| Response (NNN) field table | `responses.<NNN>.content.application/json.schema` → `#/components/schemas` `$ref` |
| Response Example (json) | `responses.<NNN>.content.*.examples.default.value` (verbatim) |
| Error Responses table | `responses.<NNN>` per status + **`x-error-catalog`** for per-sentinel detail |
| Field row → property | `properties.<json>` with `type`/`description`/`examples` |
| Mandatory (M/O) | membership in the schema's `required: [...]` array |
| Nested `**X Object:**` sub-table | a separate `components.schemas.X` entry + internal `$ref` |
| Embedded struct (e.g. `BaseResponse`) | `allOf: [{$ref: "#/components/schemas/BaseResponse"}, {type: object, ...}]` |
| Wrapper envelope `{success,data,message}` | wrapper schema whose `data` `$ref`s the inner schema |
| service overview + common errors | root `info` + `servers` + `tags` + `components.responses` |

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
| named struct `T` | `$ref: "#/components/schemas/T"` |
| `*T` (pointer) | the `T` mapping, **excluded from `required[]`** (see Nullability) |
| custom `type X string` + const block | `type: string`, `enum: [...]` (all const values) |

### Nullability (3.1 — JSON-Schema union types, NOT `nullable:`)
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

Within each schema, `properties` keys are emitted in this order (YAML preserves it). Keep key order **byte-stable** across runs.

---

## Error Responses (`responses` + x-error-catalog)

OpenAPI keys responses by **status code**, but distinct error sentinels each need **one row** even when several share a status. To keep that fidelity, each error status gets one `responses.<NNN>` entry, and where multiple distinct sentinels share that status they are enumerated in **`x-error-catalog`** (which `confluence-api-doc` renders back into the Error Responses table):

```yaml
responses:
  "422":
    description: Business rule violation
    content:
      application/json:
        schema:
          $ref: "#/components/schemas/Error"
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
- Wrapped repo/external errors → a single catch-all `"500"` (`$ref` `#/components/responses/InternalServerError`); do not trace into repos.
- Generic 401/403/404/500 → `$ref` the shared `#/components/responses/*`; do not redeclare per endpoint.
- Status-key order ascending; within a status, `x-error-catalog` follows the standard order (handler errors → usecase sentinels [switch order or code order] → domain-service errors → catch-all).

---

## Shared error responses (`components.responses.<CommonError>`)

One entry per common error under `components.responses`, referenced from per-operation `responses` via `#/components/responses/<Name>`:

```yaml
components:
  responses:
    Unauthorized:
      description: Missing or invalid authentication
      content:
        application/json:
          schema:
            $ref: "#/components/schemas/Error"
```

Provide at least `Unauthorized` (401), `Forbidden` (403), `NotFound` (404), `BadRequest` (400), `InternalServerError` (500), plus a shared `Error` schema under `components.schemas`:

```yaml
components:
  schemas:
    Error:
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
components:
  schemas:
    ConsentEnvelope:
      type: object
      required: [success, data]
      properties:
        success:
          type: boolean
          examples: [true]
        data:
          $ref: "#/components/schemas/ConsentResponse"
        message:
          type: ["string", "null"]
          description: Optional message
          examples: ["null"]
```

List envelopes: `data: { type: array, items: { $ref: "#/components/schemas/ConsentResponse" } }` plus `total`/`page` props. The operation's `responses.<NNN>.schema` then `$ref`s the envelope, and the `examples.default.value` shows the full wrapped shape.

---

## Embedded struct → allOf

A struct embedding another (e.g. `ConsentResponse` embeds `BaseResponse`) composes via `allOf`:

```yaml
components:
  schemas:
    ConsentResponse:
      allOf:
        - $ref: "#/components/schemas/BaseResponse"
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

## Field `description` — source-priority ladder

Every property under `components.schemas` **MUST** carry a `description` — **enforced by `speccheck.py` (S7)**: a typed property with no description is an ERROR (exempt: a pure-`$ref` property, whose description lives on its target, and the `{Envelope, ErrorEnvelope}` boilerplate wrappers). Populate it from the **highest rung you have evidence for**, and **never invent** — if nothing above the floor applies, use the floor:

| Rung | Source (highest first) | What to write | Example |
|---|---|---|---|
| 1 | Go field **doc-comment** (`// …` above the field) | the comment, trimmed to a clause | `// resolved at open time` → `Resolved at open time` |
| 2 | **Custom enum type** (`type X string` + `const` block) | the allowed values, in prose | `One of: S, G` |
| 3 | **`validate`/`binding` tag** | the real constraint it encodes | `validate:"required,email"` → `Required email address` |
| 4 | **Traceable usecase rule** (a condition visible in the handler→usecase code traced in Step 3) | the business condition | `Required when opening a savings account` |
| 5 | **Formula floor** — field-name split (always available) | the name as a ≤8-word phrase | `branchNo` → `Branch number` |

> **Rung 2 scope:** this only sets the `description` *prose*. The matching `enum:` array on the schema is a separate schema-constraint concern, governed by the **Custom types → `type: string` + full `enum`** rule in the Verification Checklist — not added by the description step.

**Length:** terse by default — most fields, and **every** floor description, are ≤8 words. Expand to a single clause **only** when rung 2–4 carries real information (an enum set, a constraint, a when-required rule); never pad the floor.

**Groundedness (never-guess):** a description must be derivable from the rung it cites in the source. Do not state business meaning that isn't visible in a comment, tag, enum, or traced usecase. When in doubt, drop to the floor — a mechanical name-split is *factual*; an invented sentence is not.

**Rung 5 — the floor (unconditional).** When rungs 1–4 yield nothing, derive the description mechanically from the Go field name (apply the FIRST matching rule; ≤8 words; factual only; do not inject qualifiers the formula doesn't specify). The floor always produces a value, so no property is ever left bare for S7:

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

Deterministic example conventions, emitted as the single element of the property's `examples` array (and assembled into the operation-level `examples.default.value` body/response):

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

All `$ref`s are **internal JSON pointers** into the one document (no file paths) — this is what makes the single file render in every tool:
- Operation → schema: `"#/components/schemas/<Name>"`.
- Operation → shared response: `"#/components/responses/<Name>"`.
- Schema → schema (nested type / array items / envelope `data`): `"#/components/schemas/<Name>"`.
- Embedded base in `allOf`: `"#/components/schemas/<Base>"`.
- Shared response → error schema: `"#/components/schemas/Error"`.
- Always quote the `$ref` value; never use a file path or a bare `#`.

---

## Byte-stable YAML rules

For clean Update-mode diffs and a simple L1 `$ref` check:
- 2-space indentation, block style (no flow `{}`/`[]` except short inline examples and scalar arrays like `enum`/`required`/`examples`).
- Fixed top-level key order: `openapi, info, servers, tags, paths, components`; within `components`: `securitySchemes, responses, schemas`. Emit `paths` keys in router-registration order, and `components.schemas` keys in first-reference order; keep both **byte-stable** across runs.
- Fixed key order per object kind: **operation** = `tags, summary, description, operationId, security, parameters, requestBody, responses`; **schema** = `type, format, enum, required, properties, items, allOf, additionalProperties, description, examples`; **parameter** = `name, in, required, description, schema, example`.
- Quote version strings (`version: "1.0"`) and any value that YAML could mis-type.
- One trailing newline; no trailing whitespace.

---

## Dereferenced view (`bruno/openapi.deref.yaml`)

A **generated companion** to the canonical spec, for viewers (Bruno API Designer, Swagger UI) that don't expand internal `$ref`. The `openapi-doc` skill emits it with `assets/deref.py` **after** the canonical passes verify — it is **derived, never hand-authored, and not separately verified** (its correctness is inherited from the canonical `bruno/openapi.yaml`). It is **not** governed by the Byte-stable YAML rules above (those pin the hand-authored canonical for clean Update diffs); the view's formatting comes from the dumper and is deterministic for a given canonical.

- **What deref does** — replaces every internal `$ref` (`#/components/...`) with a deep copy of its target, recursively. When nothing is left to resolve, the now-redundant `components.schemas` + `components.responses` are dropped; `components.securitySchemes` stay (operations reference them by **name** via `security`, not `$ref`).
- **`allOf` is preserved, not merged** — an `allOf` whose member is a `$ref` keeps the `allOf` with the base **inlined** (faithful dereference; no lossy flattening of `required[]`/`properties`).
- **Recursive types** — a `$ref` pointing back into a type currently being expanded (self-referential / mutually-recursive struct) is **left in place** at the cycle (and reported); `components` is then kept so that pointer still resolves. The output is always finite and valid.
- **Extensions pass through** — `x-error-catalog` and any other `x-*` keys are copied verbatim.
- **Downstream still reads the canonical** — `open-collection` and `confluence-api-doc` consume `bruno/openapi.yaml`, never this view. Do not point them at `openapi.deref.yaml`.

---

## Verification Checklist

**Single source of truth** for *what* must be checked — referenced by the `openapi-doc` skill's Step 4 + Validate Mode. Do not duplicate elsewhere; reference this.

> **Three-layer coverage.** `assets/speccheck.py` (**L1**, deterministic) mechanically covers: root/operation well-formedness · internal `$ref` resolution (every `#/components/...` pointer resolves) · route↔`paths`-key coverage · property **count** vs Go struct (embedded expanded) · **`required[]`** vs tags · **`description` presence** (every `components.schemas` typed property has one; pure-`$ref` + `{Envelope, ErrorEnvelope}` exempt) · security-scheme resolution · inline-example JSON validity · (optional) a real validator if one is on PATH. The **L2** fresh-eyes verifier (`openapi-doc-verifier.md`) covers judgment: error tracing + `x-error-catalog`, custom-type enums, `description` **groundedness** (each one supported by its source rung, not invented) + `examples`/nullable detail, property order, success status, security mapping, example shape. **L3** re-derives the route inventory from the router to catch a whole path silently dropped. L1 prints whatever it cannot resolve as a `NOTE` to focus L2.

### Coverage & Structure
- [ ] Every route in code has a `paths.<path>` entry, and every `paths` key maps to a real route (no orphan)
- [ ] Every internal `$ref` (`#/components/schemas|responses/...`) resolves to a defined component; no file-path `$ref` remains
- [ ] Handler group structure is reflected by `tags` (one per group) and each operation's `tags[0]`
- [ ] `openapi: 3.1.0`; `info.title`/`info.version` present; `servers` set
- [ ] Each operation has `summary`, `description`, `operationId`, `responses` (≥1 success 2xx)
- [ ] Inline `examples.*.value` JSON is valid

### Schema Completeness (critical — open struct source files)
- [ ] Every serializable struct field (exclude `json:"-"` + unexported) has a `properties` entry — none skipped
- [ ] `required[]` correct per tags: required→listed, pointer→omitted, omitempty→omitted, **bool-without-required→omitted**, non-ptr-non-bool→listed
- [ ] Embedded structs via `allOf` (or expanded in order); nested types each have their own `components.schemas.<GoType>` entry + internal `$ref`
- [ ] Custom types → `type: string` + full `enum`
- [ ] Pointer/null-capable fields use `type: ["<t>","null"]` and/or are omitted from `required[]` (no `nullable:`)
- [ ] Wrapper envelope modeled with `data` `$ref` if the handler wraps the payload
- [ ] Inline `c.Query()` params present; `required:false` by default, `true` only if the handler errors when empty
- [ ] Property order follows Go struct field order (embedded first)
- [ ] Every property has a `description`, **grounded** per the source-priority ladder (floor = the formula table; bare property = ERROR, except exempt pure-`$ref` / `{Envelope, ErrorEnvelope}`); `examples` follow the value conventions and satisfy the `validate` tag
- [ ] `examples.default.value` (request & response) includes all mandatory + ≥1 optional field and reflects the real (wrapped) shape

### Response Metadata (critical)
- [ ] Success status key matches the handler's actual return (not guessed)
- [ ] `security` matches the route middleware and references a defined `securitySchemes` entry

### Error Completeness (critical — open ALL usecase AND domain-service methods)
- [ ] Every distinct sentinel has an `x-error-catalog` entry (one per sentinel even when sharing a status); messages match code strings; same sentinel deduped
- [ ] Wrapped repo/external → single catch-all `"500"`; generic 401/403/404 → shared `#/components/responses` `$ref`
- [ ] Status keys ascending; `x-error-catalog` order = handler errors → usecase sentinels → domain-service errors → catch-all

### Text Consistency
- [ ] `summary` = exact PascalCase split, no articles; `description` = `<Verb> <resource>`, verb from method, ≤10 words
- [ ] `info.description` ≤2 sentences, `<Service> provides APIs for <domain>.` pattern
</content>
</invoke>
