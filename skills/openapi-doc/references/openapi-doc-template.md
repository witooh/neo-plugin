# API-Spec Drift Rules (Go ↔ `docs/api/*.yaml`)

The canonical reference for **what counts as drift** between the Go implementation and the custom-YAML **API spec** at `docs/api/`, plus the Go→spec mapping the drift check applies. `openapi-doc` **generates nothing** — the api-spec is the source of truth (authored spec-first by neo's Architect); this skill scans Go and reports where the code disagrees with the spec. Referenced by the skill's Step 2 + the fresh-eyes verifier.

> **Three-layer coverage.** `assets/speccheck.py` (**L1**, deterministic) mechanically covers: **route coverage** (every Go route documented, every spec endpoint implemented — both directions) · **field presence** (a serializable Go field with no spec row; a spec field absent from the struct) · **M/O** (struct tags vs `mandatory: M|O`) · **type** (the confident Go→spec-type cases). The **L2** fresh-eyes verifier (`openapi-doc-verifier.md`) covers judgment the script degraded to `NOTE`: unconfident struct matches, the response envelope, inline query/path params, custom-type fields, and **error-status tracing** (spec `errors[]` ↔ Go sentinels). **L3** re-derives both inventories (router + `docs/api/`) to catch a whole route/endpoint silently un-compared. L1 prints whatever it cannot decide as a `NOTE` to focus L2.

---

## The api-spec it reads (schema summary)

The **canonical authoring spec** is neo's `templates/api-spec.md` — this is a consumer-side summary of just the keys the drift check reads. Layout: `docs/api/_meta.yaml` (global) + `docs/api/<domain>/<endpoint>.yaml` (one per endpoint) + a generated `index.md` + a hand-kept `VERSION.md`.

```yaml
# docs/api/<domain>/<endpoint>.yaml — the keys drift uses
method: POST                      # GET | POST | PUT | PATCH | DELETE   ─┐ D1 route match
path: /accounts/account           # route template; {param} for path params ┘ (method + normalised path)
request_body:
  fields:                         # ─┐ D2 vs the Go request struct
    - { name: customerId, type: String, mandatory: M, … }   #  name=json key · type · mandatory(M|O)
responses:
  - status: 200
    fields:                       # the response ENVELOPE ({status,data,…}) — NOT drift-checked (wrapper)
      - { name: data, type: Object, mandatory: M, object: AccountResponse }
    objects:                      # ─┐ D2 vs the Go payload struct(s)
      AccountResponse:            #  one field list per nested object table
        - { name: accountId, type: String, mandatory: M, … }
```

- `_meta.yaml` → `extra_endpoints: [{method, path, …}]` are **index-only** rows with no spec file (e.g. a health probe); the drift check treats them as **documented** so their Go route is not flagged.
- Drift reads only `method` / `path` / `request_body.fields` / `responses[].objects.*` (+ `extra_endpoints`). `description` / `business_logic` / `example` / `remark` / `errors` are spec-side prose the Architect owns — **not** mechanically drift-checked (errors are an L2 fresh-eyes concern).

---

## D1 · Route drift (method + normalised path, both directions)

Normalise each path for comparison (`{id}`/`:id` → `{}`, trailing slash off) and match base-URL-suffix-tolerantly (`/api/v1/accounts` matches `/accounts`).
- A **Go route** with no spec endpoint (and not in `extra_endpoints`) = **DRIFT** — undocumented route (add a spec file, or confirm it is intentionally undocumented and skip).
- A **spec endpoint** (a real file) with no Go route = **DRIFT** — unimplemented (spec-first pending) or a removed route — confirm.

## D2 · Field drift (per matched endpoint)

For each spec field group — `request_body.fields` (request) and each `responses[].objects.<Name>` (response) — reverse-lookup the Go struct whose serializable json names best fit the group (strict subset first; a safe high-overlap fallback so a *stale* spec field is still caught), then compare:
- **Presence** — a serializable Go field (excl. `json:"-"` / unexported / embedded-expanded) with **no spec row** = DRIFT (undocumented); a spec field with **no Go field** = DRIFT (stale).
- **M/O** — recompute M/O from the struct tags (table below) and compare to the spec `mandatory` (`M`|`O`); a disagreement = DRIFT.
- **Type** — map the Go field type (table below) and compare to the spec `type`; a **confident** disagreement = DRIFT.

A field group with **no confident struct match**, the **response envelope** wrapper fields, and **handler-inline** query/path params degrade to **NOTE** (fresh-eyes), never a false DRIFT.

---

## Type mapping (Go → custom-YAML `type`)

The spec vocab is `String` / `Number` / `Integer` / `Boolean` / `Object` / `Array`. Only the **confident** rows below are drift-checked; anything else maps to *unknown* and is **skipped** (so type drift never false-positives on a named struct, custom enum type, `time.Time`, interface, or `json.RawMessage`).

| Go type | spec `type` (drift-checked) |
|---|---|
| `string` | `String` |
| `int`, `int8…int64`, `uint…`, `byte`, `rune` | `Number` (or `Integer` — both accepted) |
| `float32`, `float64` | `Number` |
| `bool` | `Boolean` |
| `[]T` | `Array` |
| `map[string]T` | `Object` |
| `time.Time`, named struct `T`, custom `type X string`, interface, `json.RawMessage` | *unknown → skipped (no type drift)* |
| `*T` (pointer) | the `T` row, **and** affects M/O (below) |

Nested object / array-of fields carry `object: <Name>` in the spec and `Object`/`Array` as the type; their Go counterpart is a struct / slice-of-struct (`object`/`array` matches; the named-struct element type itself is skipped for type drift and compared **as its own response object**).

---

## M/O Classification (struct tags → `mandatory`)

The drift check recomputes M/O from the Go struct tags and compares it to the spec's `mandatory` column.

**Request structs:**

| Condition | M/O |
|---|---|
| Has `binding:"required"` or `validate:"required"` | **M** |
| Pointer type (`*string`, `*int`, …) | **O** |
| Has `json:",omitempty"` without required | **O** |
| `bool` WITHOUT `binding:"required"` | **O** |
| Non-pointer, non-bool, WITHOUT required | **M** |

**Response structs:** pointer → **O**; non-pointer → **M**.

`bool` without `required` is **O** because Go's `json.Unmarshal` leaves it `false` when absent — the sender may omit it. Query params from inline `c.Query(...)` are **handler-inline**, not struct fields → the drift check leaves them to fresh-eyes (`required:false` by default, `true` only if the handler errors when empty — read the handler).

Field extraction completeness, embedded-struct expansion, custom-type resolution, and **error tracing** all follow the single source: [`go-scan-patterns.md`](go-scan-patterns.md) (§Extracting Request/Response Structs, §Field Extraction Completeness, §Error Tracing Patterns).

---

## Drift Verification Checklist

**Single source of truth** for *what* must be checked — referenced by the skill's Step 2 + the verifier. Do not duplicate elsewhere; reference this.

### Routes (D1)
- [ ] Every route in Go code has a `docs/api/<domain>/*.yaml` endpoint (or an `_meta.extra_endpoints` row), and every spec endpoint maps to a real route (no orphan / unconfirmed spec-first-pending)
- [ ] Path + method match (normalised, base-URL-suffix-tolerant); a one-sided route is reported with its direction

### Fields (D2 — open the struct source files)
- [ ] Every serializable struct field (exclude `json:"-"` + unexported; embedded expanded) has a spec row — none undocumented
- [ ] No spec field is absent from its struct (no stale rows left after a Go rename/removal)
- [ ] `mandatory` correct per tags: required→M, pointer→O, omitempty→O, **bool-without-required→O**, non-ptr-non-bool→M; response pointer→O, non-pointer→M
- [ ] `type` agrees on the confident cases (`bool`/`[]T`/numeric/`map`/`string`); custom/struct/`time.Time` left to fresh-eyes
- [ ] Nested object / array-of fields carry `object:` + are compared as their own response object

### Judgment (L2 fresh-eyes — the script's NOTEs)
- [ ] Field groups with no confident struct match were reached and reconciled
- [ ] Response envelope wrapper + inline query/path params verified against the handler
- [ ] Custom-type fields (`type X string` + `const`) — the spec `remark`/values still match the const block
- [ ] **Error-status tracing** — each spec `errors[]` row is backed by a real Go sentinel (handler + usecase + domain-service), and every traced sentinel is documented; wrapped repo/external → a single `500`

### Completeness (L3)
- [ ] Both inventories re-derived (router + `docs/api/`); no whole route/endpoint silently un-compared
