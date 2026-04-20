---
name: api-doc-gen
description: >
  Generate and validate API documentation from source code. Scans handler/router
  files to produce structured Markdown API docs in docs/api/ — one file per endpoint,
  grouped by handler domain. Or validates existing docs against the current codebase.
  Use this skill whenever the user wants to generate API docs, update API documentation,
  check if API docs are out of date, create endpoint documentation from code, or says
  things like "gen api doc", "สร้าง api doc", "อัปเดต api doc",
  "เช็ค api doc ตรงกับ code ไหม", "document these endpoints", "api doc outdated".
  Also trigger when neo-team delegates API documentation tasks to this skill.
compatibility:
  environment: claude-code
  tools:
    - Read
    - Glob
    - Grep
    - Bash
    - Edit
    - Write
---

# API Doc Generator

Generate or validate API documentation by scanning source code. Currently optimized for Go (with Fiber, Echo, Chi, Gin support). The output is a multi-file directory structure — one Markdown file per endpoint, grouped by handler domain — so each API is easy to find, review, and maintain independently.

## Output Structure

```
docs/api/
├── index.md              ← service header, overview, endpoints table, common errors
├── <group>/
│   ├── <endpoint>.md     ← one endpoint per file
│   └── ...
└── ...
```

- **Grouping:** each subdirectory under the handler base directory = one group
- **File naming:** handler function name converted to kebab-case (e.g., `AcceptConsent` → `accept-consent.md`)
- **Path params in docs:** always use `{param}` format in documented paths, regardless of framework syntax in code (`:id` → `{id}`, `{id}` stays `{id}`)
- **Index:** `docs/api/index.md` links to every endpoint file

## Modes

| Mode | When to use | What it does |
|------|-------------|--------------|
| **Generate** | No `docs/api/` directory exists, or user wants to regenerate from scratch | Scan code → create `docs/api/` with `index.md` + group folders + per-endpoint files |
| **Update** | `docs/api/index.md` exists, code has changed | Scan code → diff against existing files → add/update/remove individual endpoint files + regenerate `index.md` |
| **Validate** | User wants to check consistency | Compare all files in `docs/api/` vs code → report per-file discrepancies without modifying |

Detect the mode automatically:
1. If `docs/api/index.md` doesn't exist → **Generate**
2. If user says "validate", "check", "เช็ค" → **Validate**
3. Otherwise → **Update**

If a legacy `docs/api-doc.md` exists but no `docs/api/` directory, treat as **Generate** (migration from old single-file format).

The user can override by specifying the mode explicitly.

## Workflow

### Step 0: Read Project Context

Read `CLAUDE.md` (or `AGENTS.md`, `CONTRIBUTING.md`) to understand:
- Project name and purpose (for the doc header)
- Framework used (Fiber, Echo, Chi, Gin)
- Project structure conventions
- API versioning pattern (e.g., `/api/v1/`)

If no convention file exists, infer from the code structure.

### Step 1: Discover Routes

Scan the codebase for route registration patterns. Read [`references/go-scan-patterns.md`](references/go-scan-patterns.md) for framework-specific patterns.

**What to find:**
- All registered routes (method + path)
- The handler function each route maps to
- Route groups and prefixes
- Middleware applied (auth, validation)

**Where to look (in order):**
1. Router setup file — often `cmd/api/main.go`, `internal/router.go`, or `routes.go`
2. Route group files — `internal/<domain>/routes.go`
3. Handler files — `internal/<domain>/handler/*.go`

### Step 1b: Discover Handler Groups

After finding routes, scan the handler directory structure to determine grouping. Read [`references/go-scan-patterns.md`](references/go-scan-patterns.md) § Handler Directory Scanning for detailed patterns.

1. **Locate handler base directory** — typically `internal/delivery/http/handler/` or `internal/handler/`
2. **List subdirectories** — each subdirectory = one group (e.g., `handler/consent/` → group "consent")
3. **Map handler files to endpoints** — each Go file (excluding `handler.go`, `request.go`, `response.go`, `dto.go`, `*_test.go`) maps to one endpoint doc file
4. **Extract function name** — find the exported receiver method in each file, convert PascalCase to kebab-case for the filename
5. **Build group map** — `{ group: "consent", endpoints: [{ function: "AcceptConsent", file: "accept-consent.md", method: "POST", path: "/api/v1/consents" }, ...] }`

If the handler directory has no subdirectories (flat structure), fall back to grouping by route prefix.

### Step 2: Extract Endpoint Details

For each discovered route, trace from handler → usecase → repository to extract:

1. **Request shape** — handler's request struct (path params, query params, request body)
2. **Response shape** — handler's response struct (success and error cases), including any response wrapper
3. **Success status code** — check the handler's success return to determine the actual HTTP status (200/201/204/etc.), do not guess
4. **Business logic** — open and read ALL usecase methods called by the handler, then extract steps using this priority:

   **Priority 1 — Usecase header comments (preferred):** Read the comment block directly above the `func` signature. Look for the `### Logical` section containing `Step N:` lines. If found, transcribe them verbatim as numbered steps. Sub-steps (`Step 4.1:`, `Step 4.2:`) become indented sub-items. Do not reinterpret, merge, or add steps — copy exactly what the developer wrote.

   Read [`references/go-scan-patterns.md`](references/go-scan-patterns.md) § Usecase Header Comment Detection for the exact detection procedure and supported formats.

   **Priority 2 — Code-derived counting rules (fallback):** Only if no step comments exist in the header. Walk through the happy-path flow line by line and classify each line:

   **Count as 1 step:**
   - Repository/store method call (`u.repo.Xxx(...)`, `u.store.Xxx(...)`)
   - Other usecase/service method call (`u.otherUsecase.Xxx(...)`, `u.service.Xxx(...)`)
   - External system call (notification send, event publish, message queue, HTTP client)
   - Business rule `if`/`switch` that returns a **typed/sentinel error** (`errs.UseCasef(...)`, `ErrXxx`, `errs.Invalid(...)`, etc.) — the condition check itself is the step. **This applies even inside a `for` loop** — each sentinel-returning `if` in a loop body is still 1 step.
   - Side effect that changes external state: audit log write, cache invalidate/set

   **Clarifications — common ambiguous patterns:**
   - **Repo call followed by nil check:** A repo call and its subsequent `if result == nil { return sentinel }` are **2 separate steps** — the repo call is a step (I/O), and the nil check is a step (business rule returning sentinel). Never merge them.
   - **Sentinel inside a `for` loop:** If a `for` loop body contains an `if` that returns a typed error, that `if` is **1 step** — loops do not suppress step counting. The loop itself is not a step; each qualifying action inside it is.
   - **Entity mutation method without I/O** (e.g., `entity.Revoke()`, `entity.Accept()`): **NOT a step** — it changes in-memory state but has no I/O. The subsequent repo persist call (`repo.Update()`) is the step.
   - **Early return of success without error** (e.g., `if len(items) == 0 { return empty, nil }`): **NOT a step** — it is a control flow shortcut, not a business rule check that returns a typed error.

   **Do NOT count as a step:**
   - Error propagation: `if err != nil { return ..., err }` or `if err != nil { return ..., fmt.Errorf(...) }`
   - Standard library: `time.Now()`, `uuid.New()`, `json.Marshal`, `strconv.Atoi`
   - Struct construction, variable assignment, type conversion
   - Internal utility with no I/O: mapper, converter, formatter
   - Entity mutation method without I/O: `entity.Revoke()`, `entity.Accept()`, `entity.Decline()`
   - Observability: `log.Info(...)`, `log.Error(...)`, `metrics.Increment(...)`
   - Context enrichment: `ctx = context.WithValue(...)`
   - Early return of success result (empty result, idempotent shortcut)
   - Final `return` of success result

   Do not summarize multiple actions into one step — if the usecase does 8 things, the doc must have 8 steps.

   Read [`references/go-scan-patterns.md`](references/go-scan-patterns.md) § Step Classification Examples for concrete code examples.
5. **Error responses** — mapped HTTP status codes from error handling

Track which group each endpoint belongs to — this determines its file placement in Step 3.

#### Deterministic Text Rules

Free-text fields must follow these formulas to produce consistent output across runs.

**Endpoint description** (`# <Name>` subtitle):
- Pattern: `<Verb> <resource>[ by/for <qualifier>]`
- Verb from HTTP method: POST→Create, GET(single)→Retrieve, GET(list)→List, PUT→Update, PATCH→Partially update, DELETE→Delete
- No articles (a/an/the). Max 10 words. Must start with verb.
- Examples: "Create consent", "Retrieve consent by ID", "List channels"

**Endpoint display name** (`# <Name>` heading):
- PascalCase → space-separated: `AcceptConsent` → `Accept Consent`
- No articles, no extra words. Exact PascalCase split only.

**Field description column** — apply the FIRST matching rule (top wins). Do NOT inject domain/entity qualifiers beyond what the formula specifies:

| # | Pattern | Formula | Result |
|---|---------|---------|--------|
| 1 | `id` (struct's own PK) | `Unique identifier of the <entity>` | `Unique identifier of the consent` |
| 2 | `*_id` that is a FK (references another entity's PK) | `Reference to <entity>` | `Reference to purpose` |
| 3 | `*_id` NOT a FK (natural/business identifier) | Split into words, keep `ID` uppercase | `citizen_id` → `Citizen ID` |
| 4 | `*_at` (timestamp) | `Timestamp when <past-tense action>` | `Timestamp when created` |
| 5 | `status` (exact match) | `Current status` | `Current status` |
| 6 | `name` + suffix (`nameTH`, `nameEN`, etc.) | `Name in <suffix expansion>` | `nameTH` → `Name in Thai` |
| 7 | `name` (exact match) | `Name of the <entity>` | `Name of the channel` |
| 8 | Boolean type | `Whether <condition from field name>` | `Whether consent is active` |
| 9 | Other | Mechanically split camelCase/snake_case → words → noun phrase. Known abbreviations: `No`→number, `TH`→Thai, `EN`→English. Unknown abbreviations: use Go struct field comment if available; if none, keep as-is in uppercase. Do NOT add words absent from field name or struct comment. | `mobileNo` → `Mobile number`, `cif` (no comment) → `CIF` |

Max 8 words. Factual only.

**Business logic step wording:**
- Start with imperative verb derived from the method/function name
- Pattern: `<Verb> <object>[ qualifier]`
- If inline comment exists on/above the code line → use comment text verbatim
- `u.repo.FindByID(ctx, id)` → "Find consent by ID" | `if purpose.Status != Active` → "Validate purpose is active"

**Index overview paragraph**:
- Derive from CLAUDE.md or README project description
- Pattern: `<Service name> provides APIs for <domain>. <One sentence about main capabilities>.`
- Max 2 sentences.

**Where to find these:**
- Request/Response structs: `handler/request.go`, `handler/response.go`, or inline in handler files
- Response wrapper: check how handler returns data — may wrap in `Response{Success, Data, Message}` (see `go-scan-patterns.md` § Response Wrapper Detection)
- Domain entities: `entity.go` in the domain package (handler may return entity directly if no response struct exists)
- Query params: both struct-based AND inline `c.Query()` calls in handler (see `go-scan-patterns.md` § Query Parameters from Handler Code)
- Success status code: check the handler's `c.JSON(statusCode, ...)` or `c.Status(code).JSON(...)` — do not assume 200
- Error mapping: handler's error-to-status-code logic
- Auth type: determined from middleware on the route group — check for JWT/Bearer middleware, API key middleware, or no auth. Document as `Bearer token`, `API Key`, or `None` in the endpoint header
- Validation rules: request struct tags (`validate:"required"`, `binding:"required"`), usecase validation

#### M/O Classification Rules

Determine Mandatory (M) or Optional (O) from Go struct definition. This is critical for API correctness — a wrong M/O misleads consumers about what they must send or what they will always receive.

**Request fields:**

| Condition | M/O | Reason |
|-----------|-----|--------|
| Has `binding:"required"` or `validate:"required"` | M | Framework rejects request if missing |
| Pointer type (`*string`, `*int`, `*bool`, etc.) | O | Can be nil; `null` in JSON |
| Has `json:",omitempty"` (without required) | O | Explicitly optional |
| `bool` WITHOUT `binding:"required"` | O | Zero value `false` is valid default; sender can omit the field and Go deserializes as `false` — this is NOT a missing value, it's a meaningful default |
| Non-pointer, non-bool, WITHOUT `binding:"required"` | O | Zero value (`""`, `0`) is used as default; gin does not enforce presence without `binding:"required"` |

**Response fields:**

| Condition | M/O | Reason |
|-----------|-----|--------|
| Pointer type (`*time.Time`, `*string`, etc.) with `omitempty` | O | May be absent or `null` in JSON |
| Pointer type WITHOUT `omitempty` | O | Can be `null` in JSON |
| Non-pointer type | M | Always present in JSON serialization |

The key insight for `bool`: in Go, `json.Unmarshal` silently assigns `false` when a bool field is absent from input. Unlike `string` or `int` where absence typically indicates a problem, `false` is an intentional, meaningful default for booleans. If the API designer wanted the field to be required, they would have added `binding:"required"`.

#### Field Completeness — Every Field Matters

The doc must be a 1:1 mirror of the code structs. A missing field or wrong type makes the doc unreliable and defeats its purpose. Follow these rules:

1. **Read the full struct** — open the actual `.go` file containing the struct and read every field. Do not rely on memory or partial scans. Count only serializable fields (exclude `json:"-"` and unexported fields) — if a struct has 20 serializable fields, the doc must have 20 rows.
2. **Follow embedded/composed structs** — if a struct embeds another (`BaseResponse`, `Pagination`, `Timestamps`), read that parent struct too and include all its fields in the doc table.
3. **Resolve custom types** — if a field uses a custom type (e.g., `ConsentStatus`, `NullString`, `decimal.Decimal`), trace its definition and document the underlying type + allowed values in the Remark column.
4. **Pointer and omitempty fields** — `*string` or `json:",omitempty"` means the field is optional and can be `null`. Mark as `O` and show `null` in Example when appropriate.
5. **Nested objects and arrays** — if a field is a struct or slice-of-struct, create a separate sub-table for that object type. The parent table Remark column should say `See <GoTypeName> Object below`.
6. **Row ordering** — follow Go struct field order (top to bottom). Embedded struct fields first (expanded in their declaration order), then the struct's own fields. Sub-tables appear immediately after the parent table that references them.
7. **Cross-check after writing** — after writing the field table, re-read the source struct and compare line by line. Every serializable field (exclude `json:"-"` and unexported fields) must have a matching row in the table.

Read [`references/go-scan-patterns.md`](references/go-scan-patterns.md) § Field Extraction Completeness for detailed patterns on embedded structs, custom types, and edge cases.

#### Error Response Completeness — Every Error Path Matters

A partial error table gives false confidence. Use a **usecase-first** approach — the usecase layer is the source of truth for business errors. Then supplement with handler-level errors.

1. **Open and read ALL usecase methods** — Read the handler to find every usecase call it makes. For each usecase method, open the file and read the entire function body. List every distinct typed error it constructs (e.g., `errs.UseCasef(...)`, `errs.Invalid(...)`, `errs.NotFoundf(...)`) — these become error response rows. Wrapped/propagated errors from repo calls (`return nil, err`, `errs.WithStack(err)`) consolidate into the catch-all 500.
2. **Open and read ALL domain service methods called by the usecase** — this step is mandatory, not optional. For each domain service call in the usecase (variable names like `*Validator*`, `*Service*`, `service.New*`; import paths containing `domain/service/`), open the service file and read the called method. List every typed error the service constructs (`errs.Domainf(...)`, `errs.Newf(...)`, etc.). A single service method may have multiple error returns with different messages — count each distinct `return errs.*` as a separate error. Do NOT skip this step — domain services contain business logic errors that map to 4xx, not 500.
3. **Trace errors to HTTP status** — for each error found in steps 1-2, go back to the handler and find how it maps that error to an HTTP status code (via `errors.Is` switch, error type assertion, or error map). This gives you the Status + Error Message for the doc.
4. **Handler-level errors** — scan the handler function itself for direct non-2xx returns that happen *before* calling the usecase: bind/parse errors (400), validation errors (422), auth middleware rejections (401/403), path param parsing errors (400).
5. **Sentinel error discovery** — search for `var Err... = errors.New(...)` in the domain/entity package. Cross-reference with all the usecase methods to confirm which ones this endpoint can actually trigger.
6. **Default/fallback case** — always include the catch-all error (usually 500 Internal Server Error) that handles unexpected errors.
7. **Cross-check after writing** — re-read ALL usecase methods AND domain service methods AND the handler's error mapping. Count typed error returns across all of them + direct error returns in the handler → must match the rows in the error table.

**Deterministic Error Enumeration Rules** — follow these rules exactly to ensure consistent output across runs:

| Rule | Description |
|------|-------------|
| **One sentinel = one row** | Every distinct typed error return = exactly 1 row, even if multiple errors share the same HTTP status code. **Error Message column must use the exact format string from the code** — copy the first argument of `errors.New("...")`, `errs.UseCasef("...")`, `errs.Domainf("...")`, etc. Replace `%s`, `%d`, `%.1f` with `{placeholder}` using the variable name (e.g., `errs.UseCasef("purpose with code '%s' not found", p.PurposeCode)` → `purpose with code '{code}' not found`). Never use `'...'` or generic placeholders — always derive from the actual format string. |
| **Wrapped/propagated errors — trace by layer** | For errors propagated via `return nil, err` from a **domain service** call → trace into the service to find its typed errors (they are business logic, not 500). For errors propagated from **repository/external** calls → do NOT trace; treat as catch-all 500. `fmt.Errorf("...: %w", err)` or `errs.WithStack(err)` wrapping a repo/external error → also catch-all 500. |
| **One catch-all 500 row** | All wrapped/unhandled errors that have no explicit `errors.Is` case in the handler → consolidate into exactly 1 row: `500 | internal server error`. Never expand these into multiple 500 rows. |
| **Dedup by error variable** | If the handler calls multiple usecase methods that can return the same sentinel (e.g., `ErrNotFound` from 2 different methods), document it as 1 row only. Dedup key = (sentinel variable name + HTTP status code). |
| **Handler errors are exhaustive** | Always check for ALL of these — not optional: bind/parse error → 400, validation error → 422, path param parse error → 400. If the handler has the pattern, include the row. Do not skip any. |

**Row ordering** — list error rows in this fixed order:
1. Handler-level errors (400 bind, 400 param parse, 422 validation) — in status code ascending order
2. Usecase typed errors — in the order they appear in the usecase code (top to bottom, line by line). If the handler has an `errors.Is` switch, use the switch order instead.
3. Domain service typed errors — in the order they appear in the service code (top to bottom). Place them immediately after the usecase error that triggers the service call.
4. Catch-all 500 — always last row

Read [`references/go-scan-patterns.md`](references/go-scan-patterns.md) § Error Tracing Patterns for comprehensive patterns on how errors flow through layers.

### Step 3: Generate, Update, or Validate

Read [`references/api-doc-template.md`](references/api-doc-template.md) for the exact output format (Index Template + Per-Endpoint Template).

#### Generate Mode

Create the `docs/api/` directory structure:

1. **Create `docs/api/index.md`** using the Index Template:
   - Service name, version, base URL
   - Overview paragraph
   - Endpoints table per group — each row links to the per-endpoint file
   - Common error responses section

2. **Create group directories** — `docs/api/<group>/` for each handler group

3. **Create per-endpoint files** — `docs/api/<group>/<endpoint-name>.md` using the Per-Endpoint Template:
   - Breadcrumb navigation back to index
   - One endpoint only: method, path, auth, params, request/response, business logic, errors
   - Use `H1` for the endpoint name (it's the top-level heading in its own file)
   - Use `H2` for sub-sections (Path Parameters, Request Body, etc.)

#### Update Mode

1. Read existing `docs/api/index.md` and all group directories
2. Build a map of existing documented endpoints (file path → endpoint)
3. Scan code to get current endpoints (same as Generate)
4. Diff and apply changes:
   - **New endpoints** → create new `.md` file in the appropriate group directory
   - **Removed endpoints** → delete the orphaned `.md` file; if group directory is empty, remove it
   - **Changed endpoints** → update only the changed file
   - **Group changes** → if a handler moved to a different group directory, move the doc file
5. Regenerate `docs/api/index.md` to reflect current state
6. Preserve any manually-added notes in endpoint files that aren't auto-generated

#### Validate Mode

Compare all files in `docs/api/` against discovered routes **at the same depth as Step 2** — open the actual struct files and ALL usecase methods, not just check surface-level presence.

Run **every item** in the [Verification Checklist](references/api-doc-template.md#verification-checklist). Then produce a report:

```
## API Doc Validation Report

**Status:** [In Sync / Out of Sync]
**Checked:** [timestamp]
**Structure:** docs/api/ with [N] groups, [M] endpoint files

### Missing Files (endpoints in code but no doc file)
- POST /api/v1/consents → expected at docs/api/consent/accept-consent.md
  handler: AcceptConsent (internal/delivery/http/handler/consent/accept_consent.go:12)

### Orphan Files (doc files with no matching endpoint in code)
- docs/api/consent/delete-consent.md → no matching route found

### Field Mismatches (per file)
Check performed: opened struct source file, counted serializable fields vs doc rows.
- docs/api/consent/get-consent.md
  - Response: struct has 8 fields, doc has 6 rows — MISSING: `revoked_at`, `revoked_by`
  - Response: `status` documented as String, code uses `ConsentStatus` (enum: "active", "revoked", "expired")
  - Request: embedded `BaseRequest` has 2 fields not in doc: `request_id`, `trace_id`

### Error Response Mismatches (per file)
Check performed: opened ALL usecase methods, counted error returns vs doc rows.
- docs/api/consent/accept-consent.md
  - Usecase `Create()` has 5 error returns, doc has 3 error rows — MISSING:
    - `ErrPurposeExpired` → should be 422
    - `fmt.Errorf("send notification: %w", err)` → should be 500
  - Handler bind error (400) not documented

### Index Integrity
- TOC link to `consent/revoke-consent.md` → file exists: ✅/❌
- Group "purpose" listed in index but directory is empty

### Summary
| Category | Count |
|----------|-------|
| Groups in code | X |
| Groups in docs | Y |
| Endpoints in code | X |
| Endpoint files in docs | Y |
| Missing files | Z |
| Orphan files | W |
| Field mismatches | N |
| Error response mismatches | E |
| Broken index links | P |
```

### Step 4: Verify (mandatory after every Generate/Update)

Every time you create or modify files in `docs/api/`, run a full verification pass before reporting completion. This catches drift between the docs you just wrote and the actual code. Skipping this step means silent errors ship.

Run **every item** in the [Verification Checklist](references/api-doc-template.md#verification-checklist) at the same depth as Step 2 — re-open the actual struct source files and ALL usecase methods, do not check from memory.

**M/O verification (critical):** For each field in every table, verify M/O against the struct tag:
- Re-read the struct and check each field's `binding`/`validate` tags and whether it's a pointer
- `bool` fields without `binding:"required"` → must be `O`
- Pointer fields → must be `O`
- Fields with `binding:"required"` → must be `M`

**Fix or report:**

- If mismatches are found → fix the doc immediately, then re-run the checklist to confirm the fix
- If all checks pass → proceed to output
- Maximum 2 fix-and-recheck cycles. If issues persist after 2 rounds, report the remaining discrepancies in the output as warnings

## Expanding to Other Languages

This skill currently focuses on Go. The scanning logic is in `references/go-scan-patterns.md`. To add a new language:
1. Create `references/<language>-scan-patterns.md` with framework-specific route/handler patterns
2. Update Step 0 to detect the language from project files (`go.mod` → Go, `package.json` → Node.js, etc.)
3. The template and output format remain the same regardless of language

## Output

After completion, report:

```
## API Doc Generator

**Mode:** [Generate / Update / Validate]
**Output:** docs/api/ ([N] groups, [M] endpoint files)
**Structure:**
  - docs/api/index.md
  - docs/api/consent/ (5 files)
  - docs/api/channel/ (6 files)
  - docs/api/purpose/ (12 files)

**Changes:**
- Created: consent/accept-consent.md, consent/get-consent.md, ...
- Updated: channel/create-channel.md (added new query param)
- Removed: legacy/old-endpoint.md (route removed from code)

**Verification:** [✅ Passed — docs match code / ⚠️ Passed with warnings / ❌ Issues remain]
- File coverage: X endpoints in code, Y files in docs — Match: ✅/❌
- Index integrity: all links resolve — ✅/❌
- Field accuracy: [X/Y endpoint files — struct field count matches doc row count]
- Error response accuracy: [X/Y endpoint files — usecase error count matches doc error rows]
- Fix cycles used: [0/1/2]

**Warnings:** [any issues found — missing structs, unresolvable types, remaining discrepancies, etc.]
```
