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
  Also trigger when neo delegates API documentation tasks to this skill.
compatibility:
  environment: claude-code
  tools:
    - Read
    - Glob
    - Grep
    - Bash
    - Edit
    - Write
    - Agent
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

**Confirm scope before scanning:**
- **Not a Go project** — if there is no `go.mod` and no `references/<lang>-scan-patterns.md` for the detected language, STOP and tell the user this skill currently supports Go only; do not scan or guess patterns.
- **Monorepo (multiple `go.mod`)** — ask the user which service to document, then scope `<project-root>`, the handler base, and `docs/api/` to that one service (e.g. `services/<name>/docs/api/`); do not merge services into one doc set.

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

**Excluded routes** — a route matched by a `docs/api/.docignore` glob file, or carrying a `// apidoc:ignore` comment above its registration, is intentionally undocumented (internal/debug/health): skip it in Generate/Update and treat it as expected-absent in Validate (not a Missing File).

### Step 1b: Discover Handler Groups

After finding routes, scan the handler directory structure to determine grouping. Read [`references/go-scan-patterns.md`](references/go-scan-patterns.md) § Handler Directory Scanning for detailed patterns.

1. **Locate handler base directory** — typically `internal/delivery/http/handler/` or `internal/handler/`
2. **List subdirectories** — each subdirectory = one group (e.g., `handler/consent/` → group "consent")
3. **Map handler files to endpoints** — each Go file (excluding `handler.go`, `request.go`, `response.go`, `dto.go`, `*_test.go`) contributes **one endpoint per exported receiver method** — usually one, but a file exporting several methods yields several endpoints (don't stop at the first)
4. **Extract function name(s)** — for **each** exported receiver method, convert PascalCase to kebab-case for the filename. If one handler method is registered under multiple `(method, path)` pairs, emit one doc file per pair, disambiguating by verb (e.g. `get-user.md` / `update-user.md`)
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

   **Priority 2 — Code-derived counting rules (fallback):** Only if no step comments exist. Count **1 step** per: repo/store/service/other-usecase/external call · a business-rule `if`/`switch` that returns a typed/sentinel error (`errs.UseCasef(...)`, `ErrXxx`) — even inside a `for` loop · an external-state side effect (audit-log write, cache set/invalidate). A repo call **plus** its following `if result == nil { return sentinel }` = **2 separate steps** (never merged). **NOT** a step: error propagation (`if err != nil { return ..., err }`), stdlib (`time.Now`/`uuid.New`/`json.Marshal`), struct construction / assignment / type conversion, internal no-I/O utility (mapper/converter), entity mutation without I/O (`entity.Revoke()`/`Accept()`), logging/metrics, context enrichment, early success return, final success `return`. Do not summarize — if the usecase does 8 things, the doc has 8 steps.

   Full rulings + worked examples are the single source in [`references/go-scan-patterns.md`](references/go-scan-patterns.md) § Step Classification Examples — do not restate them here.
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

**Field description column** — apply the FIRST matching rule from the 9-pattern formula table, the single source in [`references/api-doc-template.md`](references/api-doc-template.md) § Field Description Patterns (`id`→"Unique identifier of…", `*_id` FK→"Reference to…", `*_id` non-FK→split words keep `ID`, `*_at`→"Timestamp when…", `status`→"Current status", `name`+suffix→"Name in …", `name`→"Name of the …", bool→"Whether …", other→mechanical split). Do NOT inject domain qualifiers beyond the formula. Max 8 words, factual.

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

Classify each field **M** (mandatory) or **O** (optional) from its Go struct tags — a wrong M/O misleads consumers about what they must send or will always receive, so this is critical. The full rule tables + rationale are the **single source** in [`references/api-doc-template.md`](references/api-doc-template.md) § M/O Classification; in brief:

- **Request:** `binding`/`validate:"required"` → **M** · pointer (`*T`) / `json:",omitempty"` / `bool` without required → **O** · non-pointer non-bool without required → **M**.
- **Response:** pointer → **O** · non-pointer → **M**.

The `bool`-without-required → O case is deliberate: Go's `json.Unmarshal` assigns `false` on absence, so `false` is a meaningful default, not a missing value (a truly required bool would carry `binding:"required"`).

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
6. **Default/fallback + scope** — always include the catch-all 500. List only errors **specific to this endpoint** plus that 500; generic cross-cutting rows (401 unauthorized, 403 forbidden) live only in `index.md` § Common Error Responses — do NOT repeat them in every endpoint file.
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
2. Usecase typed errors — **if the handler has an `errors.Is`/error-map switch, in switch order; otherwise** in usecase code order (top to bottom)
3. Domain service typed errors — immediately after the usecase error that triggers the service call (service code order)
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

Validate runs the **same two-layer engine** as Step 4 — it is pure verification (no writing), so the script + fresh-eyes split applies directly.

1. **Layer 1 — script backbone:** run `python3 <ASSET_DIR>/doccheck.py docs/api/ --src <project-root>` (`ASSET_DIR` / `<project-root>` and the loop-until-green / ~3-rounds-escalate rule are defined in Step 4 Layer 1). Its mismatch report (missing/orphan files, field count, M/O, broken links) is the deterministic spine of the validation — do not hand-eyeball what the script already measures.
2. **Deep-check the rest at the same depth as Step 2** — open the actual struct files and ALL usecase methods for the judgment items the script flags as `NOTE` (error rows, step counts, custom types), not just surface-level presence.
3. **Offer fresh-eyes (default yes)** — same prompt as Step 4 Layer 1.5; on yes, dispatch the `api-doc-verifier` (read-only) for the judgment pass.

Run **every item** in the [Verification Checklist](references/api-doc-template.md#verification-checklist) across the two layers. Then produce a report (tag each finding's source — `script` or `fresh-eyes`):

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

Verification is **two layers**: a deterministic script (always) + an optional independent fresh-eyes agent. The old single-agent self-check is gone — an author re-reading their own work repeats their own blind spots. A doc passes on **evidence (the script is green) + a second pair of eyes**, never on the writing agent's confidence.

#### Layer 1 — Script tripwire (always, deterministic)

Run the checker — it compares `docs/api/` against the code and flags what a machine can measure (endpoint coverage, field count, M/O, JSON validity, broken index links):

```
python3 <ASSET_DIR>/doccheck.py docs/api/ --src <project-root>
```

`ASSET_DIR` = `<skill base dir>/assets` (the skill-load message gives "Base directory for this skill"); `<project-root>` = the repo root where `go.mod` lives (usually `.`). The script is a **tripwire, not ground truth** — regex cannot parse Go like a compiler, so a flag means "inspect this", not "this is definitely wrong".

- **exit 0** → Layer 1 green, go to Layer 1.5.
- **exit 1 (ERRORs)** → for each ERROR, open the actual struct/route and confirm:
  - real mismatch → fix the doc → re-run `doccheck.py`
  - genuine false positive (e.g. an embedded struct the regex mis-resolved) → skip it + record under Warnings (never blindly "fix" a false positive)
  - **Loop** until exit 0, **OR ~3 rounds with no progress → STOP and escalate** to the user with the remaining ERRORs listed. Never fake a green run.
- Collect every **`NOTE`** line the script prints (each ends in `needs fresh-eyes`) — these mark what the script could not verify; they feed Layer 2. NOTEs do not fail the run.

#### Layer 1.5 — Offer fresh-eyes (default yes)

Ask the user once via `AskUserQuestion`: *"Run an independent fresh-eyes verify of the generated docs? (default: yes)"*
- **no** → skip Layer 2; go to Output (mark Layer 2 "skipped by user").
- **yes** → Layer 2.

#### Layer 2 — Fresh-eyes verifier (independent agent)

Dispatch a verifier that did **not** write the docs — it re-reads the source itself and checks only the judgment-level accuracy the script cannot (error-row tracing, step counting, M/O edge cases, custom types, text formulas):

```
Agent(subagent_type: "general-purpose", description: "verify api doc", prompt: """
# Role: API Doc Verifier
Read first: <SKILL_DIR>/references/api-doc-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the docs just generated. Check ONLY judgment-level accuracy
(do not re-do the script's mechanical checks). Read the source code yourself.

## Docs under review
docs/api/<group>/<file>.md   (list the files just created/updated)

## doccheck NOTEs to focus on
<paste every NOTE line from Layer 1>

## Project conventions
CLAUDE.md (the relevant section)

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
""")
```

`SKILL_DIR` = the skill base dir (same source as `ASSET_DIR`). **Missing it = the verifier cannot read its role file and fails silently** — always send it.

- Verifier returns findings (it is read-only) → **you** fix the docs → re-run `doccheck.py` (Layer 1) to confirm nothing regressed.
- Do **not** auto-redispatch the verifier (cost). If findings are deep/numerous, offer the user a second fresh-eyes round (default yes) — one judgment round, then escalate.

Together, Layer 1 (mechanical items) + Layer 2 (judgment items) cover the full [Verification Checklist](references/api-doc-template.md#verification-checklist).

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

**Verification (two-layer):**
- **Layer 1 — doccheck.py:** ✅ PASS (0 ERROR) / ❌ ESCALATED ([N] ERROR remain after ~3 rounds)
  - Endpoint coverage: ✅/❌ · Field count: [X/Y files] · M/O: [X/Y fields] · JSON + index links: ✅/❌
  - Loop rounds used: [0/1/2/3]
- **Layer 2 — fresh-eyes verifier:** ✅ Clean / ⚠️ [N] findings fixed / ⏭ Skipped by user / ⏸ Not run
  - Error rows: [findings] · Step counting: [findings] · M/O edge + custom types: [findings]
- **Verdict:** ✅ Both layers green / ⚠️ Passed with warnings / ⏸ Escalated to user

**Warnings:** [false positives skipped, custom types unresolved by script, remaining discrepancies, etc.]
```
