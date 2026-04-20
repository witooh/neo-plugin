# API Documentation Templates

Templates for multi-file API documentation. The output is a directory structure with an index file and individual endpoint files grouped by domain.

```
docs/api/
├── index.md                      ← Index Template
├── <group>/
│   ├── <endpoint-name>.md        ← Per-Endpoint Template
│   └── ...
└── ...
```

---

## Index Template (`docs/api/index.md`)

Use this template for the index file that serves as the entry point for all API docs.

```markdown
# <Service Name> API Documentation

**Version:** <X.Y>
**Base URL:** `/api/v<N>`

## Overview

<Service name> provides APIs for <domain>. <One sentence about main capabilities>.

---

## Endpoints

### <Group Name> (e.g., Consent)

| Method | Path | Endpoint | File |
|--------|------|----------|------|
| `POST` | `/api/v1/consents` | Accept Consent | [accept-consent](consent/accept-consent.md) |
| `GET` | `/api/v1/consents/{citizen_id}` | Get Consents by Citizen | [get-consents-by-citizen](consent/get-consents-by-citizen.md) |
| `GET` | `/api/v1/consents/{id}` | Get Consent | [get-consent](consent/get-consent.md) |
| `DELETE` | `/api/v1/consents/{id}/revoke` | Revoke Consent | [revoke-consent](consent/revoke-consent.md) |

### <Group Name> (e.g., Channel)

| Method | Path | Endpoint | File |
|--------|------|----------|------|
| `POST` | `/api/v1/channels` | Create Channel | [create-channel](channel/create-channel.md) |
| `GET` | `/api/v1/channels` | Get All Channels | [get-all-channels](channel/get-all-channels.md) |

---

## Common Error Responses

All endpoints may return the following common errors:

| Status | Error Message         | Description                         |
| ------ | --------------------- | ----------------------------------- |
| 400    | invalid request       | Request body or query param invalid |
| 401    | unauthorized          | Missing or invalid authentication   |
| 403    | forbidden             | Insufficient permissions            |
| 404    | not found             | Resource does not exist             |
| 500    | internal server error | Unexpected server-side failure      |
```

---

## Per-Endpoint Template (individual file)

Each file contains exactly ONE endpoint. Do not include document headers or TOC — those live in `index.md`.

**Endpoint display name** (`# <Name>`): PascalCase → space-separated words. `AcceptConsent` → `Accept Consent`. No articles (a/an/the), no extra words — exact PascalCase split only.

**Endpoint description** (line below `# <Name>`): `<Verb> <resource>[ by/for <qualifier>]`. Verb from HTTP method: POST→Create, GET(single)→Retrieve, GET(list)→List, PUT→Update, PATCH→Partially update, DELETE→Delete. No articles. Max 10 words.

````markdown
> [API Documentation](../index.md) > [<Group Name>](./) > <Endpoint Name>

# <Endpoint Name>

<One sentence describing what this endpoint does.>

- **Method:** `GET` | `POST` | `PUT` | `PATCH` | `DELETE`
- **Path:** `/api/v1/<resource>/{path-param}`
- **Auth:** `Bearer token` | `API Key` | `None`

## Path Parameters (if any)

| Field Name | Description | Type   | Mandatory | Example    | Remark |
| ---------- | ----------- | ------ | --------- | ---------- | ------ |
| `id`       | Resource ID | String | M         | `"uuid-1"` |        |

## Query Parameters (if any)

| Field Name | Description           | Type   | Mandatory | Example | Remark        |
| ---------- | --------------------- | ------ | --------- | ------- | ------------- |
| `page`     | Page number (1-based) | Number | O         | `1`     | Default: `1`  |
| `limit`    | Items per page        | Number | O         | `20`    | Default: `20` |

## Request Body (if any)

| Field Name   | Description          | Type    | Mandatory | Example           | Remark                |
| ------------ | -------------------- | ------- | --------- | ----------------- | --------------------- |
| `field_name` | What this field does | String  | M         | `"example_value"` |                       |
| `items`      | List of item objects | Array   | M         |                   | See Item Object below |
| `flag`       | Boolean toggle       | Boolean | O         | `true`            |                       |

**Item Object:**

| Field Name | Description     | Type   | Mandatory | Example   | Remark |
| ---------- | --------------- | ------ | --------- | --------- | ------ |
| `code`     | Item code       | String | M         | `"CODE1"` |        |
| `value`    | Optional detail | String | O         | `"abc"`   |        |

## Request Example

```json
{
  "field_name": "example_value",
  "items": [{ "code": "CODE1" }, { "code": "CODE2", "value": "abc" }],
  "flag": true
}
```

## Response (<HTTP Status> <Status Text>)

| Field Name   | Description            | Type   | Mandatory | Example                  | Remark               |
| ------------ | ---------------------- | ------ | --------- | ------------------------ | -------------------- |
| `id`         | Unique identifier of the record | String | M         | `"uuid-v4"`              |                      |
| `status`     | Current status         | String | M         | `"active"`               | "active", "inactive" |
| `created_at` | Timestamp when created | String | M         | `"2024-01-01T10:00:00+07:00"` |                      |
| `updated_at` | Timestamp when updated | String | M         | `"2024-01-01T10:00:00+07:00"` |                      |

## Response Example

```json
{
  "id": "uuid-v4",
  "status": "active",
  "created_at": "2024-01-01T10:00:00+07:00",
  "updated_at": "2024-01-01T10:00:00+07:00"
}
```

## Business Logic

One step per distinct action in the usecase — read the usecase method and list every action it performs:

1. Validate that referenced Purpose exists and is active
2. Check for existing consent for this Citizen + Purpose combination
3. Create new Consent record with status `active`
4. Create audit log entry for consent creation
5. Send notification to data subject via notification service

## Error Responses

| Status | Error Message | Description |
| ------ | ------------- | ----------- |
| 400 | invalid request | Request body validation failed |
| 404 | record not found | Resource does not exist |
| 422 | \<specific message\> | Business rule violation |
| 500 | internal server error | Server-side failure |
````

**Table formatting rule:** Use minimal column padding — single space between `|` and content (e.g., `| 400 | message | desc |`). Do not pad with extra spaces to align columns. This ensures byte-identical tables across runs.

---

## Field Table Conventions

| Convention  | Meaning                                                                                                  |
| ----------- | -------------------------------------------------------------------------------------------------------- |
| Mandatory   | Use `M` for required fields, `O` for optional. Classify from Go struct tags — see M/O table below        |
| Type values | `String`, `Number`, `Boolean`, `Array`, `Object`                                                         |
| Timestamps  | Always ISO 8601 with Asia/Bangkok timezone (+07:00): `"2024-01-01T10:00:00+07:00"`                                                         |
| UUIDs       | Use `"uuid-v4"` or `"uuid-<noun>"` as example values (e.g., `"uuid-consent-1"`)                          |
| Nested obj  | Use `Array` or `Object` type + `See <GoTypeName> Object below` in Remark column, then add a separate sub-table |
| Enum values | List allowed values in Remark (e.g., `"active"`, `"inactive"`, `"revoked"`)                              |
| Null fields | Show `null` in Example when the field can be null                                                        |

### M/O Classification (from Go struct tags)

**Request fields:**

| Condition | M/O |
|-----------|-----|
| Has `binding:"required"` or `validate:"required"` | M |
| Pointer type (`*string`, `*int`, `*bool`, etc.) | O |
| Has `json:",omitempty"` without required tag | O |
| `bool` type WITHOUT `binding:"required"` | O |
| Non-pointer, non-bool, WITHOUT required tag | M |

**Response fields:**

| Condition | M/O |
|-----------|-----|
| Pointer type (with or without `omitempty`) | O |
| Non-pointer type | M |

`bool` without `binding:"required"` is O because Go's `json.Unmarshal` assigns `false` when the field is absent — the sender can legitimately omit it.

### Row Ordering (mandatory)

Follow Go struct field order (top to bottom):
1. Embedded struct fields first — expanded in their declaration order
2. Then the struct's own fields in declaration order
3. Sub-tables appear immediately after the parent table that references them

### Example Value Conventions

| Type | Convention | Example Value |
|------|-----------|---------------|
| UUID | Fixed placeholder | `"uuid-v4"` |
| String (enum) | First enum value from const block | `"active"` |
| String (name/label) | Fixed realistic value (see lookup table below) | `"สมชาย ใจดี"` |
| String (other) | Fixed realistic value from field context | `"0812345678"` |
| Number (integer, no default) | Smallest typical positive value | `1` |
| Number (with known default) | Use the default value | `20` |
| Boolean | Always `true` | `true` |
| Timestamp | Fixed template timestamp | `"2024-01-01T10:00:00+07:00"` |
| Array (in example JSON) | Exactly 1 item | `[{...}]` |
| Null/optional | `null` when field is primarily "absent" | `null` |

**String subtype classification** — use the field description pattern (#1-#9) to determine which String convention applies:

| Field description rule | String subtype | Example |
|---|---|---|
| #1 `id` PK, #2 `*_id` FK | UUID | `"uuid-v4"` |
| #3 `*_id` non-FK | String (other) — realistic value | `"1234567890123"` |
| #5 `status`, any enum type | String (enum) | `"active"` |
| #6 `name` + suffix, #7 `name` | String (name/label) — realistic fixed | `"สมชาย ใจดี"`, `"Consent Form"` |
| #9 Other | String (other) — realistic fixed | `"0812345678"` |

**Fixed realistic value lookup** — use these deterministic values for common field contexts. Match by field name/suffix (case-insensitive). If no match, derive a short realistic value from the field's Go struct comment or domain context:

| Field context | Fixed value |
|---|---|
| Thai person name (`firstNameTH`, `lastNameTH`, person-context `nameTH`) | `"สมชาย ใจดี"` |
| English person name (`firstNameEN`, `lastNameEN`, person-context `nameEN`) | `"Somchai Jaidee"` |
| Thai entity name (`name_th` on non-person entity like channel, segment, purpose) | `"ชื่อ<entity>ภาษาไทย"` e.g. channel → `"ช่องทางตัวอย่าง"` |
| English entity name (`name_en` on non-person entity) | `"Example <Entity>"` e.g. channel → `"Example Channel"` |
| Generic name (`name`, `channelName`, `purposeName`) | `"<entity> name"` e.g. `"Consent Form"` |
| Phone (`mobileNo`, `phoneNumber`, `tel`) | `"0812345678"` |
| Email (`email`, `contactEmail`) | `"user@example.com"` |
| URL (`url`, `callbackUrl`, `webhook`) | `"https://example.com/callback"` |
| Address | `"123 Example St"` |
| Description (`description`, `desc`, `remark`) | `"Example description"` |
| Code/reference (`code`, `refCode`, `transactionId`) | `"CODE001"` |
| Thai citizen ID (`citizenId`, `citizen_id`) | `"1234567890123"` |

**Validation-aware examples** — after choosing an example value from the conventions above, cross-check it against the field's `validate` struct tag. The example MUST satisfy all validation rules:

| Validate tag | Constraint | Bad example | Correct example |
|---|---|---|---|
| `alpha` | Letters only | `"name01"` | `"SomchaiJaidee"` |
| `numeric` | Digits only | `"abc123"` | `"1234567890123"` |
| `email` | Email format | `"user"` | `"user@example.com"` |
| `url` | URL format | `"homepage"` | `"https://example.com"` |
| `len=N` | Exact length | `"12345"` (len=13) | `"1234567890123"` |
| `min=X,max=Y` (string) | Length range | `"a"` (min=3) | `"abc"` |
| `min=X,max=Y` (number) | Value range | `0` (min=1) | `1` |
| `oneof=a b c` | Enum values | `"d"` | `"a"` |

If the convention-derived example violates a tag, adjust the value to comply while staying as close to the convention as possible.

### Remark Column Rules

| Condition | Remark content | Example |
|-----------|---------------|---------|
| Enum type | List all values in quotes | `"active"`, `"revoked"`, `"expired"` |
| Has default value | `Default: <value>` | `Default: 1` |
| `validate` tag with range | `Min: X, Max: Y` | `Min: 1, Max: 100` |
| `validate` tag with max length | `Max length: N` | `Max length: 255` |
| Nested object/array | `See <GoTypeName> Object below` | `See ConsentItem Object below` |
| No special condition | Leave empty | |

### Sub-table Naming

Use Go type name as-is + " Object:" suffix in bold:
- `[]ConsentItem` → `**ConsentItem Object:**`
- `ResponseData` → `**ResponseData Object:**`
- Never abbreviate or rename the Go type

### Field Description Patterns

Apply the FIRST matching rule (top wins). Do NOT inject domain/entity qualifiers beyond what the formula specifies.

| # | Pattern | Formula | Result |
|---|---------|---------|--------|
| 1 | `id` (struct's own PK) | `Unique identifier of the <entity>` | `Unique identifier of the consent` |
| 2 | `*_id` FK (references another entity's PK) | `Reference to <entity>` | `Reference to purpose` |
| 3 | `*_id` NOT a FK (natural/business identifier) | Split into words, keep `ID` uppercase | `citizen_id` → `Citizen ID` |
| 4 | `*_at` (timestamp) | `Timestamp when <past-tense action>` | `Timestamp when created` |
| 5 | `status` (exact) | `Current status` | `Current status` |
| 6 | `name` + suffix (e.g., `nameTH`, `nameEN`) | `Name in <suffix expansion>` | `nameTH` → `Name in Thai` |
| 7 | `name` (exact) | `Name of the <entity>` | `Name of the channel` |
| 8 | Boolean | `Whether <condition from field name>` | `Whether consent is active` |
| 9 | Other | Mechanically split camelCase/snake_case → words → noun phrase. Known abbreviations: `No`→number, `TH`→Thai, `EN`→English. Unknown abbreviations: use Go struct field comment if available; if none, keep as-is in uppercase. Do NOT add words absent from field name or struct comment. | `mobileNo` → `Mobile number`, `cif` (no comment) → `CIF` |

Max 8 words. Factual only.

---

## Verification Checklist

This is the **single source of truth** for all verification checks — used by Step 4 (verify after Generate/Update) and Validate Mode. Do not duplicate these checks elsewhere; reference this checklist instead.

### Coverage & Structure
- [ ] Every route in code has a corresponding `.md` file, and vice versa (no missing or orphan files)
- [ ] Every endpoint file is listed in `index.md` endpoints table, and every index entry points to an existing file
- [ ] Handler directory structure matches `docs/api/` directory structure (group consistency)
- [ ] Every endpoint file has Method, Path, and at least one example
- [ ] Breadcrumb navigation uses correct relative paths
- [ ] JSON examples are valid (no trailing commas, correct types)
- [ ] Version number in `index.md` header is up to date

### Field Completeness (critical — open struct source files to verify)
- [ ] All field tables use `M`/`O` for Mandatory column
- [ ] M/O classification correct: re-check each field against struct tags — `binding:"required"` → M, pointer → O, `omitempty` → O, **`bool` without required → O**, non-pointer non-bool without required → M
- [ ] Request body field count matches serializable fields in struct (exclude `json:"-"` and unexported) — no field skipped
- [ ] Response field count matches serializable fields in struct (exclude `json:"-"` and unexported) — no field skipped
- [ ] Embedded/composed struct fields are expanded into the parent table (e.g., `BaseResponse` fields included)
- [ ] Custom types resolved to underlying type with enum values listed in Remark
- [ ] Pointer fields (`*Type`) and `omitempty` fields marked as `O` with `null` in Example where appropriate
- [ ] Nested objects (`[]Struct`, `Struct`) each have their own sub-table, named `**<GoTypeName> Object:**`
- [ ] Response wrapper documented correctly if handler wraps response in envelope (e.g., `{success, data, message}`)
- [ ] Query params from inline `c.Query()` handler calls included (not just struct-based)
- [ ] Inline query params: `O` by default, `M` only if handler explicitly returns error when param is empty
- [ ] Row ordering follows Go struct field order — embedded fields first, then own fields
- [ ] Field descriptions follow formula: ID→"Unique identifier of...", FK→"Reference to...", timestamp→"Timestamp when...", etc.
- [ ] Example values follow conventions: UUID→`"uuid-v4"`, enum→first value, timestamp→`"2024-01-01T10:00:00+07:00"`, boolean→`true`, name/label→realistic fixed from lookup table
- [ ] Example values satisfy field's `validate` struct tag (e.g., `alpha` tag → no digits, `len=13` → exactly 13 chars)
- [ ] Remark column: enum values listed, defaults noted, constraints noted, empty when no special condition
- [ ] JSON examples include all mandatory fields and at least one optional field
- [ ] JSON examples reflect actual response shape (including wrapper if present)

### Business Logic Completeness (critical — open ALL usecase methods to verify)
- [ ] **Source check:** determine whether steps came from header comments (Priority 1) or code-derived counting rules (Priority 2)
- [ ] If Priority 1 (header comments): steps in doc match the `Step N:` lines verbatim — no steps added, removed, or reworded. Sub-steps (4.1, 4.2) are indented sub-items.
- [ ] If Priority 2 (code-derived): counted as 1 step: repo/service/external call, sentinel-returning `if`/`switch` (even inside loops), state-changing side effect
- [ ] If Priority 2: repo call + nil sentinel check = 2 separate steps (never merged)
- [ ] If Priority 2: NOT counted: error propagation, stdlib calls, struct construction, entity mutation without I/O, logging, metrics, context enrichment, early success return, final `return`
- [ ] Step count matches the source (comment step count OR code-derived action count)
- [ ] Conditional branches are documented (e.g., "If X, do Y")
- [ ] Side effects included (audit log, cache invalidate, event publish) — but NOT logging/metrics

### Response Metadata (critical)
- [ ] Success status code matches handler's actual return (200/201/204 etc.), not guessed
- [ ] Auth type matches middleware applied to the route

### Error Response Completeness (critical — open ALL usecase AND domain service methods to verify)
- [ ] ALL usecase methods the handler calls have been read — not just one
- [ ] ALL domain service methods called by the usecase have been opened and read (variable names like `*Validator*`, `*Service*`; import paths with `domain/service/`)
- [ ] Every typed error return across all usecase methods AND domain service methods has a matching row in the Error Responses table
- [ ] Each sentinel error (`ErrXxx`) = exactly 1 row, even if multiple sentinels share the same HTTP status code — never consolidate
- [ ] Wrapped `fmt.Errorf` errors from usecase → NOT traced into repo — covered by single catch-all 500 row
- [ ] Same sentinel from multiple usecase methods → deduplicated to 1 row (dedup by error variable name + status code)
- [ ] Handler-level errors exhaustively checked: bind/parse (400), validation (422), param parse (400) — all present if handler has the pattern
- [ ] Default/catch-all error case (500) included as the last row
- [ ] Error messages match the actual strings from `errors.New("...")` in the code, not generic placeholders
- [ ] Row ordering: handler errors (ascending status) → usecase sentinels (handler switch order) → catch-all 500

### Text Consistency
- [ ] Endpoint display name: exact PascalCase split, no articles (`AcceptConsent` → `Accept Consent`)
- [ ] Endpoint description: `<Verb> <resource>[ by/for <qualifier>]`, verb from HTTP method, no articles, max 10 words
- [ ] Index overview: max 2 sentences, follows `<Service> provides APIs for <domain>.` pattern
