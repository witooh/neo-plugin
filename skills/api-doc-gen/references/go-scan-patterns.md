# Go Framework Scan Patterns

How to discover routes and extract endpoint details from Go web frameworks. Start by detecting which framework is used — check `go.mod` for the import path.

## Framework Detection

| Import in go.mod | Framework |
|------------------|-----------|
| `github.com/gofiber/fiber` | Fiber |
| `github.com/labstack/echo` | Echo |
| `github.com/go-chi/chi` | Chi |
| `github.com/gin-gonic/gin` | Gin |

## Route Registration Patterns

### Fiber

```go
// Direct registration
app.Get("/api/v1/users", handler.ListUsers)
app.Post("/api/v1/users", handler.CreateUser)
app.Get("/api/v1/users/:id", handler.GetUser)

// Group registration
api := app.Group("/api/v1")
users := api.Group("/users")
users.Get("/", handler.ListUsers)
users.Post("/", handler.CreateUser)
users.Get("/:id", handler.GetUser)
```

**Search patterns:**
```
app.Get(    app.Post(    app.Put(    app.Patch(    app.Delete(
.Group(
```

**Handler signature:** `func(c *fiber.Ctx) error`

**Parameter extraction:**
- Path params: `c.Params("id")`
- Query params: `c.Query("page")`, `c.QueryInt("limit")`
- Body parsing: `c.BodyParser(&req)`

### Echo

```go
// Direct registration
e.GET("/api/v1/users", handler.ListUsers)
e.POST("/api/v1/users", handler.CreateUser)
e.GET("/api/v1/users/:id", handler.GetUser)

// Group registration
api := e.Group("/api/v1")
users := api.Group("/users")
users.GET("/", handler.ListUsers)
```

**Search patterns:**
```
e.GET(    e.POST(    e.PUT(    e.PATCH(    e.DELETE(
.Group(
```

**Handler signature:** `func(c echo.Context) error`

**Parameter extraction:**
- Path params: `c.Param("id")`
- Query params: `c.QueryParam("page")`
- Body parsing: `c.Bind(&req)`

### Chi

```go
// Direct registration
r.Get("/api/v1/users", handler.ListUsers)
r.Post("/api/v1/users", handler.CreateUser)
r.Get("/api/v1/users/{id}", handler.GetUser)

// Group registration
r.Route("/api/v1", func(r chi.Router) {
    r.Route("/users", func(r chi.Router) {
        r.Get("/", handler.ListUsers)
        r.Post("/", handler.CreateUser)
        r.Get("/{id}", handler.GetUser)
    })
})
```

**Search patterns:**
```
r.Get(    r.Post(    r.Put(    r.Patch(    r.Delete(
r.Route(
```

**Handler signature:** `func(w http.ResponseWriter, r *http.Request)`

**Parameter extraction:**
- Path params: `chi.URLParam(r, "id")`
- Query params: `r.URL.Query().Get("page")`
- Body parsing: `json.NewDecoder(r.Body).Decode(&req)`

### Gin

```go
// Direct registration
r.GET("/api/v1/users", handler.ListUsers)
r.POST("/api/v1/users", handler.CreateUser)
r.GET("/api/v1/users/:id", handler.GetUser)

// Group registration
api := r.Group("/api/v1")
users := api.Group("/users")
users.GET("/", handler.ListUsers)
```

**Search patterns:**
```
r.GET(    r.POST(    r.PUT(    r.PATCH(    r.DELETE(
.Group(
```

**Handler signature:** `func(c *gin.Context)`

**Parameter extraction:**
- Path params: `c.Param("id")`
- Query params: `c.Query("page")`, `c.DefaultQuery("page", "1")`
- Body parsing: `c.ShouldBindJSON(&req)`

## Usecase Header Comment Detection

Business logic steps should be extracted from the usecase method's header comment when available. This is Priority 1 — the developer's documented intent is the most reliable and deterministic source.

### Format

All usecase methods use `/* */` block comments with this structure:

```go
/*
### Business Requirement
<description of what the function does>

### Logical
Step 1: <description>
Step 2: <description>
Step 3: <description>
Step 4: <description>
Step 4.1: <sub-step description>
Step 4.2: <sub-step description>
Step 5: <description>
*/
func (uc *consentUseCase) AcceptConsent(ctx context.Context, input *AcceptConsentInput) (*AcceptConsentOutput, error) {
```

### Detection Procedure

1. Open the usecase `.go` file containing the method
2. Read the comment block directly above the `func` signature
3. Find the `### Logical` section
4. Extract all lines matching `Step <number>:` — these are the business logic steps
5. Transcribe verbatim as numbered steps:
   - `Step 1: Validate purposes input` → `1. Validate purposes input`
   - `Step 4.1: Fetch purpose by code` → sub-item under step 4: `   4.1. Fetch purpose by code`

### Rules

- **Copy verbatim** — do not rephrase, merge, or reinterpret step descriptions
- **Sub-steps** (e.g., `Step 4.1`, `Step 4.2`) become indented sub-items under the parent step
- **Do not add steps** that aren't in the comment — even if the code does more
- **Do not remove steps** that are in the comment — even if you think they're redundant
- **If no `### Logical` section exists** or no `Step N:` lines found → fall back to Priority 2 (code-derived counting rules below)

### What Does NOT Qualify

```go
/*
### Business Requirement
Create a new purpose with a unique code.
*/
func (uc *purposeUseCase) CreatePurpose(...) {
```

A comment block with only `### Business Requirement` and NO `### Logical` section = no step comments → use Priority 2.

---

## Step Classification Examples (Priority 2 fallback)

Code-derived step counting — use ONLY when the usecase has no header comment steps. Walk through usecase code line by line and classify each:

### Count as 1 step

```go
func (u *ConsentUsecase) Create(ctx context.Context, req CreateInput) (*Consent, error) {
    // STEP: repo call
    purpose, err := u.purposeRepo.FindByID(ctx, req.PurposeID)

    // NOT a step: error propagation (if err != nil + wrapped error)
    if err != nil {
        return nil, fmt.Errorf("find purpose: %w", err)
    }

    // STEP: business rule check (if + sentinel error)
    if purpose.Status != PurposeStatusActive {
        return nil, ErrPurposeInactive
    }

    // STEP: business rule check (if + sentinel error)
    if purpose.ExpiredAt != nil && purpose.ExpiredAt.Before(time.Now()) {
        return nil, ErrPurposeExpired
    }

    // NOT a step: struct construction
    consent := &Consent{
        ID:        uuid.New().String(),
        CitizenID: req.CitizenID,
        PurposeID: req.PurposeID,
        Status:    ConsentStatusActive,
    }

    // STEP: repo call
    if err := u.repo.Create(ctx, consent); err != nil {
        return nil, fmt.Errorf("create consent: %w", err)
    }

    // STEP: side effect (external state change)
    if err := u.auditLog.Write(ctx, "consent.created", consent.ID); err != nil {
        return nil, fmt.Errorf("write audit log: %w", err)
    }

    // STEP: external system call
    if err := u.notifier.Send(ctx, consent); err != nil {
        return nil, fmt.Errorf("send notification: %w", err)
    }

    // NOT a step: logging (observability)
    log.Info("consent created", "id", consent.ID)

    // NOT a step: metrics (observability)
    metrics.Increment("consent.created")

    // NOT a step: final return of success result
    return consent, nil
}
```

**Result: 6 steps**
1. Find purpose by ID
2. Validate purpose is active
3. Validate purpose is not expired
4. Create consent record
5. Write audit log for consent creation
6. Send notification

### Ambiguous patterns — explicit rulings

These patterns caused inconsistent counts. Follow these rulings exactly:

```go
// PATTERN 1: Repo call + nil check = 2 SEPARATE steps
// ────────────────────────────────────────────────────
purpose, err := u.purposeRepo.GetByCode(ctx, code) // STEP 1: repo call
if err != nil { return nil, errs.WithStack(err) }  // NOT a step: error propagation
if purpose == nil {                                  // STEP 2: business rule (sentinel)
    return nil, errs.UseCasef("purpose not found")
}
// → These are ALWAYS 2 steps. Never merge repo call + nil sentinel into 1.

// PATTERN 2: Sentinel inside a for loop = still 1 step
// ─────────────────────────────────────────────────────
for _, p := range input.Purposes {
    // STEP: repo call (inside loop — still counts)
    purpose, err := u.purposeRepo.GetByCode(ctx, p.Code)
    if err != nil { return nil, errs.WithStack(err) }  // NOT: error propagation

    // STEP: business rule sentinel (inside loop — still counts)
    if purpose == nil {
        return nil, errs.UseCasef("purpose not found")
    }

    // STEP: business rule sentinel (inside loop — still counts)
    if purpose.Scope() == ScopeAccountNo && p.ScopeValue == nil {
        return nil, errs.UseCasef("scope_value required")
    }
}
// → Loop body steps count normally. The for loop itself is not a step.

// PATTERN 3: Entity mutation without I/O = NOT a step
// ───────────────────────────────────────────────────
for _, c := range consentsToRevoke {
    c.Revoke()          // NOT a step: in-memory state change, no I/O
    c.Accept(...)       // NOT a step: same — entity method, no I/O
}
// The repo.Update() or txManager.WithTransaction() that persists = the step.

// PATTERN 4: Early return of success (no error) = NOT a step
// ──────────────────────────────────────────────────────────
if len(consentsToRevoke) == 0 {
    return &Output{Items: []}, nil  // NOT a step: early success return, no sentinel error
}
// → Only if/switch returning a TYPED ERROR is a step. Returning success early is control flow.
```

### Do NOT count — summary

| Code pattern | Why not a step |
|---|---|
| `if err != nil { return ..., err }` | Error propagation — no business decision |
| `if err != nil { return ..., fmt.Errorf(...) }` | Error propagation — wrapped |
| `uuid.New()`, `time.Now()` | Standard library — no I/O |
| `entity := &Struct{...}` | Struct construction |
| `entity.Revoke()`, `entity.Accept()` | Entity mutation — in-memory, no I/O |
| `mapper.ToResponse(entity)` | Internal utility — no I/O |
| `log.Info(...)`, `log.Error(...)` | Observability — not business logic |
| `metrics.Increment(...)` | Observability — not business logic |
| `ctx = context.WithValue(...)` | Context enrichment — no side effect |
| `if len(x) == 0 { return empty, nil }` | Early success return — not a sentinel error |
| `return consent, nil` | Final success return |

---

## Extracting Request/Response Structs

After finding a handler, trace the request and response types:

### Request Structs

Look for structs with JSON tags used in body parsing:

```go
type CreateUserRequest struct {
    Name     string `json:"name" validate:"required"`
    Email    string `json:"email" validate:"required,email"`
    Age      int    `json:"age,omitempty" validate:"min=0,max=150"`
}
```

**Tag interpretation:**
- `json:"name"` → field name in JSON
- `json:",omitempty"` → optional field
- `validate:"required"` or `binding:"required"` → mandatory (M)
- `validate:"min=X,max=Y"` → range constraint (note in Remark)
- `validate:"oneof=a b c"` → enum values (note in Remark)

**M/O Classification for Request Fields:**

| Go type + tags | M/O | Reason |
|----------------|-----|--------|
| Any type with `binding:"required"` or `validate:"required"` | M | Framework enforces |
| `*string`, `*int`, `*bool`, etc. (pointer) | O | Can be nil |
| Any type with `json:",omitempty"` (no required) | O | Explicitly optional |
| `bool` WITHOUT required tag | O | Zero value `false` is valid default; omitting the field is valid |
| Non-pointer, non-bool WITHOUT required tag | M | Expected to be present |

**Where to find:** Same package as handler, typically `request.go` or `dto.go`

### Query Parameters from Handler Code

Not all query params live in a request struct — some are extracted directly in the handler:

```go
func (h *Handler) ListConsents(c *fiber.Ctx) error {
    // These query params are NOT in a struct
    page := c.QueryInt("page", 1)
    limit := c.QueryInt("limit", 20)
    status := c.Query("status")
    sortBy := c.Query("sort_by", "created_at")

    // This one IS in a struct
    var filter FilterRequest
    c.QueryParser(&filter)
    // ...
}
```

**You must scan for BOTH sources:**
1. **Struct-based** — query params in a request struct (found via `QueryParser`, `BindQuery`, `ShouldBindQuery`)
2. **Inline extraction** — query params extracted directly via `c.Query("name")`, `c.QueryInt("name")`, `c.QueryParam("name")`, `c.DefaultQuery("name", "default")`, `r.URL.Query().Get("name")`

For inline query params, document:
- Field Name: the string argument (e.g., `"page"`)
- Type: infer from the extraction method (`QueryInt` → Number, `Query` → String)
- Default: if provided as second argument (e.g., `c.QueryInt("page", 1)` → Default: `1`)
- Mandatory: **`O` by default**. Mark `M` only if handler has explicit error return when param is empty (e.g., `if param == "" { return c.Status(400)... }`). No visible check in handler code → always `O`

### Response Structs

```go
type UserResponse struct {
    ID        string    `json:"id"`
    Name      string    `json:"name"`
    Email     string    `json:"email"`
    CreatedAt time.Time `json:"created_at"`
}
```

**Where to find:** Same package as handler, typically `response.go` or inline in handler

### Response Wrapper Detection

Many APIs wrap responses in a standard envelope. Before documenting the response, check how the handler returns data:

```go
// Pattern 1: Direct struct return — document the struct fields directly
return c.JSON(200, consentResponse)

// Pattern 2: Wrapper struct — document BOTH the wrapper AND inner data
return c.JSON(200, Response{
    Success: true,
    Data:    consentResponse,
    Message: "consent created",
})

// Pattern 3: Helper function — read the helper to find the wrapper
return response.Success(c, 201, consentResponse)
```

**How to detect:**
1. In the handler's success return, look at the argument passed to `c.JSON(...)`, `c.Status(...).JSON(...)`, or similar
2. If it's a wrapper struct (e.g., `Response{}`), `Grep` for `type Response struct` to find the wrapper definition
3. If it's a helper function (e.g., `response.Success()`), read the helper to find what wrapper it uses

**If a wrapper exists**, the doc response table must reflect the actual JSON the API returns:

```go
// Wrapper definition
type Response struct {
    Success bool        `json:"success"`
    Data    interface{} `json:"data"`
    Message string      `json:"message"`
}
```

Document the response as the full envelope:

| Field Name | Type | Description | Remark |
|------------|------|-------------|--------|
| `success` | Boolean | Operation result | |
| `data` | Object | Response payload | See ConsentResponse Object below |
| `message` | String | Status message | |

Then add a sub-table for the inner data object.

**If no wrapper** (direct struct return), document the struct fields as the top-level response.

### Response Discovery Fallbacks

If you cannot find a named response struct in `response.go`, check these alternatives in order:

**Fallback 1: Handler returns domain entity directly**
```go
consent, _ := h.usecase.GetByID(ctx, id)
return c.JSON(200, consent)  // returns entity, no response struct
```
→ Find the entity struct (`Grep` for `type Consent struct` in domain/entity package) and document its `json` tagged fields.

**Fallback 2: Handler constructs response inline**
```go
return c.JSON(200, fiber.Map{
    "id":     consent.ID,
    "status": consent.Status,
    "items":  items,
})
```
→ Document each key in the map as a response field. Trace the value types from the source variables.

**Fallback 3: Handler maps entity fields manually**
```go
return c.JSON(200, map[string]interface{}{
    "consent_id": consent.ID,
    "purpose":    consent.Purpose.Name,
})
```
→ Same as Fallback 2 — document the map keys and trace value types.

In all fallback cases, check whether the result is wrapped in a response envelope (see Response Wrapper Detection above).

### Auth Type Detection

Determine the auth type from middleware applied to the route or route group:

```go
// Fiber — JWT middleware on group
api := app.Group("/api/v1", jwtMiddleware)      // → all routes in group: "Bearer token"
public := app.Group("/api/v1/public")            // → no auth middleware: "None"

// Gin — auth middleware on group
authorized := r.Group("/api/v1")
authorized.Use(middleware.JWTAuth())             // → "Bearer token"

// Chi — middleware on route
r.With(middleware.APIKeyAuth).Get("/webhook", handler.Webhook)  // → "API Key"

// Echo — middleware on group
api := e.Group("/api/v1", middleware.JWT())       // → "Bearer token"
```

**How to detect:**
1. Find the route group this endpoint belongs to (from Step 1)
2. Check if the group has auth middleware attached (`.Use(jwt...)`, `.Use(auth...)`, or inline in group definition)
3. Check for route-level middleware overrides (e.g., a public endpoint inside an otherwise protected group)

**Search patterns:** `Grep` for `JWT`, `Auth`, `Bearer`, `APIKey`, `middleware` near the route group definition.

| Middleware pattern | Auth type for doc |
|---|---|
| JWT, Bearer, `jwtMiddleware` | `Bearer token` |
| API key, `APIKeyAuth`, `X-API-Key` | `API Key` |
| No auth middleware on route/group | `None` |

### Success Status Code

Check the handler's success return to determine the actual HTTP status — do not assume 200:

```go
// 200 OK — typical for GET, PUT, PATCH
return c.JSON(200, response)
return c.Status(fiber.StatusOK).JSON(response)

// 201 Created — typical for POST that creates a resource
return c.Status(201).JSON(response)
return c.Status(fiber.StatusCreated).JSON(response)

// 204 No Content — typical for DELETE, or actions with no response body
return c.SendStatus(204)
return c.Status(fiber.StatusNoContent).Send(nil)

// Helper function — read the helper to find the status code
return response.Created(c, result)   // might be 201
return response.Success(c, result)   // might be 200
```

**Search:** look for `c.JSON(`, `c.Status(`, `c.SendStatus(` in the handler's success path (the non-error return). The first argument or the status method argument is the HTTP status code.

If 204 No Content, the endpoint has no response body — omit the Response section in the doc.

### Error Mapping

Look for error-to-status-code mapping in handlers:

```go
// Typed error checks (preferred pattern)
switch {
case errors.Is(err, domain.ErrNotFound):
    return c.Status(fiber.StatusNotFound).JSON(...)
case errors.Is(err, domain.ErrDuplicate):
    return c.Status(fiber.StatusConflict).JSON(...)
default:
    return c.Status(fiber.StatusInternalServerError).JSON(...)
}
```

Extract each case as an error response entry in the doc.

## Field Extraction Completeness

When extracting request/response structs, every field must appear in the doc. These patterns catch fields that are easy to miss.

### Embedded Structs

```go
type CreateConsentResponse struct {
    entity.BaseResponse              // ← embedded — expand ALL its fields into the doc
    ConsentID string `json:"consent_id"`
    Status    string `json:"status"`
}

type BaseResponse struct {
    ID        string    `json:"id"`
    CreatedAt time.Time `json:"created_at"`
    UpdatedAt time.Time `json:"updated_at"`
}
```

The doc table must include `id`, `created_at`, `updated_at`, `consent_id`, and `status` — 5 fields total, not 3.

**How to find:** search for struct definitions without a field name (just the type). Then read that embedded struct and add its fields.

### Pointer and Optional Fields

```go
type UpdateRequest struct {
    Name     *string  `json:"name,omitempty"`     // optional, can be null
    Email    string   `json:"email"`              // required
    DeleteAt *string  `json:"delete_at,omitempty"` // optional, can be null
}
```

- `*Type` → Mark as `O`, show `null` in Example column when relevant
- `json:",omitempty"` → confirms optional, may be absent from response

### Custom/Domain Types

```go
type Consent struct {
    Status ConsentStatus `json:"status"`  // custom type
    Amount decimal.Decimal `json:"amount"` // third-party type
}

type ConsentStatus string
const (
    ConsentStatusActive  ConsentStatus = "active"
    ConsentStatusRevoked ConsentStatus = "revoked"
    ConsentStatusExpired ConsentStatus = "expired"
)
```

- Document the underlying type (`String`) in the Type column
- List all enum values in the Remark column: `"active"`, `"revoked"`, `"expired"`
- For `decimal.Decimal` → document as `String` (JSON representation) with Remark: `"decimal number as string"`

**How to find:** when you see a non-primitive type, `Grep` for `type <TypeName>` to find its definition and constants.

### Slice/Array of Structs

```go
type ListResponse struct {
    Items []ConsentItem `json:"items"`
    Total int           `json:"total"`
}

type ConsentItem struct {
    ID     string `json:"id"`
    Status string `json:"status"`
}
```

- Parent table: `items` → Type: `Array`, Remark: `See ConsentItem Object below`
- Add a separate sub-table for `ConsentItem` with all its fields

### Map Fields

```go
type MetadataResponse struct {
    Metadata map[string]interface{} `json:"metadata"`
}
```

- Document as Type: `Object`, Remark: `"key-value pairs, dynamic structure"`

### Excluded Fields — Do NOT Document

These fields exist in the Go struct but are NOT part of the JSON API:

```go
type Consent struct {
    ID        string     `json:"id"`           // ✅ document — normal json field
    Status    string     `json:"status"`       // ✅ document — normal json field
    DeletedAt *time.Time                       // ✅ document — exported, no json tag → serialized as "DeletedAt"
    Internal  string     `json:"-"`            // ❌ SKIP — explicitly excluded from JSON
    secret    string     `json:"secret"`       // ❌ SKIP — unexported (lowercase), never serialized
}
```

**Rules:**
- `json:"-"` → field is excluded from JSON serialization — do NOT include in doc
- Unexported fields (lowercase first letter) → never serialized by `encoding/json` — do NOT include
- Exported fields with no `json` tag → serialized using the Go field name as-is (e.g., `DeletedAt` → `"DeletedAt"` in JSON). Include in doc with the Go field name.

When counting "json tags in struct vs rows in doc", exclude `json:"-"` and unexported fields from the count.

### Cross-check Procedure

After writing a field table:
1. Re-read the source struct file
2. Count serializable fields: `json:"<name>"` tags where name is NOT `-`, plus exported fields without json tags — exclude `json:"-"` and unexported fields
3. Count rows in table → must match the serializable field count
4. Check for embedded structs → verify their fields are included
5. Check for custom types → verify underlying type and enum values are documented

## Error Tracing Patterns

Use a **usecase-first** approach: start by reading ALL usecase methods to enumerate all business errors, then supplement with handler-level errors. The usecase layer is the source of truth for what can go wrong — the handler just maps those errors to HTTP status codes.

### Step 1: Read ALL Usecase Methods (start here)

This is the most important step. Some handlers call multiple usecase methods — you must read ALL of them.

**How to find the usecase methods:**
1. In the handler, find every usecase/service call: `h.usecase.Create(...)`, `h.purposeUsecase.GetByID(...)`, `h.notifier.Send(...)`, etc. — there may be more than one
2. For each call, find the implementation — `Grep` for the method name in `usecase/`, `service/`, or `internal/` directories
3. Open each implementation file and read the full method body

**What to extract — read every line and list ALL error returns:**

```go
func (u *ConsentUsecase) Create(ctx context.Context, req CreateConsentInput) (*Consent, error) {
    // ERROR 1: Business rule — duplicate check
    existing, err := u.repo.FindByCitizenAndPurpose(ctx, req.CitizenID, req.PurposeID)
    if existing != nil {
        return nil, ErrConsentAlreadyExists       // ← collect this
    }

    // ERROR 2: Dependency check — purpose must exist
    purpose, err := u.purposeRepo.FindByID(ctx, req.PurposeID)
    if err != nil {
        return nil, ErrPurposeNotFound             // ← collect this
    }

    // ERROR 3: Status validation — purpose must be active
    if purpose.Status != PurposeStatusActive {
        return nil, ErrPurposeInactive             // ← collect this
    }

    // ERROR 4: Expiry check — purpose must not be expired
    if purpose.ExpiredAt != nil && purpose.ExpiredAt.Before(time.Now()) {
        return nil, ErrPurposeExpired              // ← collect this
    }

    // ERROR 5: Repository error — create failed
    consent, err := u.repo.Create(ctx, ...)
    if err != nil {
        return nil, fmt.Errorf("create consent: %w", err)  // ← collect this (wrapped → 500)
    }

    // ERROR 6: Side-effect error — notification failed
    if err := u.notifier.Send(ctx, consent); err != nil {
        return nil, fmt.Errorf("send notification: %w", err) // ← collect this (wrapped → 500)
    }

    return consent, nil
}
```

**Build an error inventory from this method:**

| # | Error Variable/Expression | Source | Error Type |
|---|--------------------------|--------|------------|
| 1 | `ErrConsentAlreadyExists` | business rule | sentinel |
| 2 | `ErrPurposeNotFound` | dependency check | sentinel |
| 3 | `ErrPurposeInactive` | status validation | sentinel |
| 4 | `ErrPurposeExpired` | expiry check | sentinel |
| 5 | `fmt.Errorf("create consent: %w", err)` | repo failure | wrapped |
| 6 | `fmt.Errorf("send notification: %w", err)` | external call | wrapped |

Every `return ..., err` or `return ..., ErrXxx` line = one row in this inventory. Do not skip any.

**If the usecase calls its own private/helper methods** (e.g., `u.validatePurpose(...)`), read those too — they may return additional sentinel errors that bubble up. However, do NOT follow calls into repository or external service implementations (see Step 4: Error Tracing Boundary).

### Step 2: Map Usecase Errors to HTTP Status

Take the error inventory from Step 1 and find how the handler maps each one to an HTTP status code.

Go back to the handler and read its error handling block:

```go
// In handler — after calling usecase
result, err := h.usecase.Create(ctx, input)
if err != nil {
    switch {
    case errors.Is(err, domain.ErrConsentAlreadyExists):
        return c.Status(409).JSON(...)    // inventory #1 → 409
    case errors.Is(err, domain.ErrPurposeNotFound):
        return c.Status(404).JSON(...)    // inventory #2 → 404
    case errors.Is(err, domain.ErrPurposeInactive):
        return c.Status(422).JSON(...)    // inventory #3 → 422
    case errors.Is(err, domain.ErrPurposeExpired):
        return c.Status(422).JSON(...)    // inventory #4 → 422
    default:
        return c.Status(500).JSON(...)    // inventory #5, #6 → 500
    }
}
```

**Important:** if a usecase error does NOT have an explicit handler case, it falls through to the `default` → 500. Still document it — note the error message will be the generic 500 message.

### Step 3: Handler-Level Errors (supplement)

These are errors that happen in the handler *before* calling the usecase:

```go
func (h *Handler) CreateConsent(c *fiber.Ctx) error {
    // HANDLER ERROR 1: Bind error → 400
    var req CreateConsentRequest
    if err := c.BodyParser(&req); err != nil {
        return c.Status(400).JSON(ErrorResponse{Message: "invalid request body"})
    }

    // HANDLER ERROR 2: Validation error → 422
    if err := h.validator.Struct(req); err != nil {
        return c.Status(422).JSON(ErrorResponse{Message: "validation failed", Details: err})
    }

    // HANDLER ERROR 3: Path param parsing → 400
    id, err := uuid.Parse(c.Params("id"))
    if err != nil {
        return c.Status(400).JSON(ErrorResponse{Message: "invalid id format"})
    }
    // ... then calls usecase
}
```

**Search patterns:**
- `BodyParser`, `Bind`, `ShouldBindJSON` → 400 bind error
- `validator.Struct`, `validate` → 422 validation error
- `uuid.Parse`, `strconv.Atoi` → 400 param parse error
- `c.Status(4xx)`, `c.Status(5xx)` → direct error returns

### Step 4: Error Tracing Boundary (strict)

The boundary is **usecase + domain service**. Trace INTO domain services but NOT into repositories or external services.

**What to trace into (business logic layers):**
- Domain services called by the usecase (e.g., `scopeValidator.ValidateX(...)`, `service.DoY(...)`) — these contain business rules and return typed errors (not just 500). Open the service method and collect all its typed error returns.
- Private/helper methods within the usecase package — same reason.

**What NOT to trace into (infrastructure layers):**
- Repository implementations (`u.repo.Create(...)`, `u.repo.FindByID(...)`)
- External HTTP clients, message queues, notification services
- Any function in `infrastructure/`, `repository/`, or third-party packages

**Error classification by source:**
- Typed error constructed in usecase body (e.g., `errs.UseCasef(...)`) → collect as sentinel
- Typed error constructed in domain service body → trace into service, collect as sentinel
- `return nil, err` propagating a **domain service** error → trace the service to find its typed errors
- `return nil, err` propagating a **repo/external** error → catch-all 500
- `fmt.Errorf("...: %w", err)` or `errs.WithStack(err)` wrapping repo/external → catch-all 500

**How to distinguish domain service from repo:** check the variable name and package. `u.repo.*`, `u.*Repo.*`, `u.store.*` → repository. `u.*Service.*`, `u.*Validator.*`, `service.New*` → domain service. When in doubt, check the import path — `domain/service/` or `domain/` = trace, `infrastructure/` or `repository/` = don't trace.

**Why this boundary matters:** tracing into repos produces inconsistent results because different runs may follow different call depths. Domain services are part of the business logic and return meaningful typed errors that consumers need to know about. Keeping repository as the hard boundary ensures consistent error enumeration.

### Sentinel Error Discovery

Find all domain-level sentinel errors — the complete set of business errors:

```go
// Search for: var Err
var (
    ErrNotFound             = errors.New("not found")
    ErrConsentAlreadyExists = errors.New("consent already exists")
    ErrConsentRevoked       = errors.New("consent already revoked")
    ErrPurposeNotFound      = errors.New("purpose not found")
    ErrPurposeInactive      = errors.New("purpose is inactive")
    ErrPurposeExpired       = errors.New("purpose expired")
    ErrDuplicate            = errors.New("duplicate record")
)
```

**Search command:** `Grep` for `var Err` or `= errors.New(` in the domain/entity package to find all sentinel errors.

Then cross-reference: which of these errors appear in the usecase methods you read in Step 1? Only those are relevant to this endpoint.

### Common Error Handling Patterns

**Pattern 1: errors.Is switch**
```go
switch {
case errors.Is(err, domain.ErrNotFound):
    return c.Status(404).JSON(...)
case errors.Is(err, domain.ErrDuplicate):
    return c.Status(409).JSON(...)
default:
    return c.Status(500).JSON(...)
}
```

**Pattern 2: Custom error type assertion**
```go
var appErr *apperror.AppError
if errors.As(err, &appErr) {
    return c.Status(appErr.HTTPStatus()).JSON(...)
}
```
→ Find the `AppError` type definition and all places it's created with specific status codes.

**Pattern 3: Error mapping function/map**
```go
var errorStatusMap = map[error]int{
    domain.ErrNotFound:  404,
    domain.ErrDuplicate: 409,
    domain.ErrForbidden: 403,
}
```
→ Every entry in this map is an error response row.

**Pattern 4: Middleware error handler**
```go
app.Use(func(c *fiber.Ctx) error {
    err := c.Next()
    // centralized error mapping
})
```
→ Read the middleware to find additional error-to-status mappings that apply globally.

### Cross-check Procedure

After writing the error table for an endpoint:
1. Re-read ALL usecase methods — count every **sentinel** error return across all of them
2. Re-read the handler — count handler-level errors (Step 3) + verify mapping for each sentinel (Step 2)
3. Apply Consolidation Rules (below) to get the expected row count
4. Compare expected rows vs actual rows in the doc table — must match exactly
5. Verify the catch-all 500 row is present as the last row

### Consolidation Rules

These rules eliminate ambiguity and ensure the same error table is produced every run.

**Rule 1 — One sentinel = one row (never consolidate by status code)**

```go
// Usecase returns 2 different sentinels, both mapped to 422 in handler:
case errors.Is(err, domain.ErrPurposeInactive):
    return c.Status(422).JSON(...)    // → row: 422 | purpose is inactive
case errors.Is(err, domain.ErrPurposeExpired):
    return c.Status(422).JSON(...)    // → row: 422 | purpose expired
```
→ **2 rows** in the error table, NOT 1 combined "422 | business rule violation" row.

**Rule 2 — Wrapped errors = catch-all 500 (do not trace into repo)**

```go
// Usecase has 3 wrapped error returns:
return nil, fmt.Errorf("create consent: %w", err)
return nil, fmt.Errorf("send notification: %w", err)
return nil, fmt.Errorf("update cache: %w", err)
```
→ **1 row** total: `500 | internal server error`. Do NOT create 3 separate 500 rows.

**Rule 3 — Dedup by sentinel variable name**

```go
// Handler calls 2 usecase methods that can both return ErrNotFound:
purpose, err := h.purposeUsecase.GetByID(...)   // can return ErrNotFound
consent, err := h.consentUsecase.GetByID(...)    // can also return ErrNotFound

// Handler has one case for it:
case errors.Is(err, domain.ErrNotFound):
    return c.Status(404).JSON(...)
```
→ **1 row**: `404 | not found`. NOT 2 rows for "purpose not found" and "consent not found".

**Rule 4 — Handler errors are an exhaustive checklist**

Always check for ALL of these patterns in the handler. If present, include the row — never skip:

```go
// Check 1: bind/parse → always 400
if err := c.BodyParser(&req); err != nil { ... }     // → row: 400 | invalid request body

// Check 2: validation → always 422
if err := h.validator.Struct(req); err != nil { ... } // → row: 422 | validation failed

// Check 3: param parse → always 400
id, err := uuid.Parse(c.Params("id")); ...            // → row: 400 | invalid id format
```

**Rule 5 — Row ordering (fixed)**

List error rows in this order — no deviation:
1. Handler-level errors (400, 422) — ascending by status code
2. Usecase sentinel errors — in the order they appear in the handler's `errors.Is` switch (top to bottom)
3. Catch-all `500 | internal server error` — always last row

## Scan Strategy

1. **Find go.mod** → detect framework
2. **Find router file** → `Grep` for route registration patterns
3. **Resolve handler functions** → follow the function reference to its definition
4. **Find request/response structs** → `Grep` for struct types used in handlers
5. **Find error mapping** → look for status code assignments in handler error paths
6. **Find domain entities** → if response wraps an entity, trace to `entity.go`
7. **Scan handler directory** → determine endpoint grouping (see below)

## Handler Directory Scanning

After detecting routes, scan the handler directory to determine endpoint grouping for multi-file output.

### Finding the Handler Base Directory

Common locations (search in order):
1. `internal/delivery/http/handler/`
2. `internal/handler/`
3. `internal/<domain>/handler/`
4. `handler/`

Use `Glob` with `**/handler/` to find it. Pick the one that contains subdirectories with `.go` files.

### Mapping Directory to Groups

Each subdirectory under the handler base = one group:

```
handler/
├── consent/           → group "consent"
│   ├── handler.go     → skip (constructor/setup)
│   ├── request.go     → skip (shared structs)
│   ├── response.go    → skip (shared structs)
│   ├── accept.go      → endpoint file
│   └── get.go         → endpoint file
├── channel/           → group "channel"
│   ├── handler.go     → skip
│   └── create.go      → endpoint file
└── health/            → group "health"
    ├── handler.go     → skip
    └── health.go      → endpoint file
```

### Excluded Files

Skip these — they are not endpoint handlers:
- `handler.go` — constructor, `NewHandler()`, route registration
- `request.go`, `response.go`, `dto.go` — shared struct definitions
- `*_test.go` — test files
- `middleware.go` — middleware definitions

### Function Name to Filename

Convert the handler's exported receiver method name from PascalCase to kebab-case:

| Function Name | File Name |
|---------------|-----------|
| `AcceptConsent` | `accept-consent.md` |
| `GetConsentHistory` | `get-consent-history.md` |
| `CreateChannel` | `create-channel.md` |
| `GetAllChannels` | `get-all-channels.md` |

To find the function name, look for the exported receiver method in each Go file:
```go
func (h *ConsentHandler) AcceptConsent(c *gin.Context) { ... }
//                        ^^^^^^^^^^^^^^ this is the function name
```

### Single-File Handler Edge Case

If a group directory contains only `handler.go` (no separate action files), extract all exported receiver methods from `handler.go` itself — each method becomes a separate endpoint doc file.

### Flat Structure Fallback

If the handler directory has no subdirectories (all `.go` files at the top level), group by the first path segment after the API version prefix:
- `/api/v1/consent/*` routes → group "consent"
- `/api/v1/channel/*` routes → group "channel"
