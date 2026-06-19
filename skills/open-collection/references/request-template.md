# Open Collection — Templates

Templates for every file this skill writes when it turns the `bruno/openapi/` OpenAPI spec into a **runnable** Bruno OpenCollection. Section ordering and indentation are part of the contract — follow them exactly so output is byte-stable across runs.

**The collection carries no `docs:` blocks** — the human-readable documentation stays in the `bruno/openapi/` OpenAPI spec (the single source of truth), and Confluence publishing reads that spec directly (the `confluence-api-doc` skill). In **Spec mode** the request artifact is purely runnable — URLs, params, bodies, headers, auth, environments; **AC-scenario mode** (§8) additionally emits a `runtime.assertions` block per request. `docs:` stays omitted in both modes. For schema-level details on each YAML key, see [`yaml-reference.md`](yaml-reference.md).

---

## 0. Reading the OpenAPI spec source (the input contract)

Input is the `bruno/openapi/openapi.yaml` single-file spec (the `openapi-doc` skill's output). The **runnable** bits come from each **operation**; **do not re-scan Go** (the spec was already verified against the code). **Prefer Bruno's native importer** (`bru import openapi … --collection-format=opencollection`), which resolves `$ref`s and emits the collection in one step; then post-process to the conventions below. If `bru` is unavailable, hand-map each operation:

| OpenAPI element | → Collection field |
|---|---|
| `servers[0].url` | the `{{baseUrl}}` env value (host/base) |
| a `paths.<path>.<method>` operation | one request `.yml` (folder = its `tags[0]`) |
| `summary` | request `info.name` |
| the method + path key | `http.method` + `http.url` = `"{{baseUrl}}<path with {id}→:id>"` |
| `parameters` (`in: path`) | a `params` row `type: path` (+ `:id` in the url) |
| `parameters` (`in: query`) | a `params` row `type: query` |
| `security` (`bearerAuth`/`apiKey`/`[]`) | request/folder `auth` (§3) — `bearerAuth`→bearer, `apiKey`→apikey, `[]`→none |
| `requestBody.content.*.examples.default.value` | `http.body.data` **verbatim** (the runnable body — already JSON-ready) |
| `responses` / `x-error-catalog` | not used (doc-only — they stay in the spec) |

- **Grouping** comes from the operation's `tags[0]` (→ collection folder), mirroring the spec's `tags` grouping.
- `components.schemas` entries are resolved only to shape the body example — they are not emitted into the collection.
- An operation with no `requestBody` → request has **no** `http.body`.
- The spec uses internal `$ref` (`#/components/...`); resolve refs (Bruno's importer does this; a hand-map follows them) before reading an operation whole.

---

## 1. `opencollection.yml`

Runnable-only — **no `docs:` block** (overview lives in the spec's `info`).

```yaml
opencollection: 1.0.0

info:
  name: <Service Name>

bundled: false

extensions:
  bruno:
    ignore:
      - node_modules
      - .git
      - openapi
```

`<Service Name>` ← CLAUDE.md project name, or `info.title` from go.mod if available.

---

## 2. `environments/<NAME>.yml`

One file per environment. Names are lowercase.

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
- `local.yml` — `baseUrl: http://localhost:<port>` (read the port from `main.go`/config — a small peek, not a Go scan; fallback `8080`)
- `sit.yml` — `baseUrl: ""` (leave empty for the user)

**Variable discovery:**
1. Scan every request's `http.url`, headers, and auth blocks for `{{varName}}` placeholders — emit one variable per unique name.
2. Always emit `baseUrl`.
3. Mark as `secret: true` (and set `value: ""`) when the name matches: `token`, `auth_token`, `bearer`, `pin`, `otp`, `password`, `key`, `api_key`, `secret`, `biometric`, `national_id`, `cif`.

> Every `{{var}}` a request references (other than `{{process.env.*}}`) **must** have an entry in at least one environment file — `colcheck.py` flags a reference with no definition.

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

1. **`info.name`** — group subdirectory name → Title Case (`consent` → `Consent`, `account_service` → `Account Service`).
2. **`info.seq`** — `10, 20, 30…` in the order the `tags` appear in the spec.
3. **`request.headers`** — any header sent by **every** request in the group goes here; per-request headers stay in the request file.
4. **`request.auth`** — derive from the operations' `security` (the spec already resolved the middleware):
   - `Bearer token` → `auth: { type: bearer, token: "{{auth_token}}" }`
   - `API Key` → `auth: { type: apikey, key: <header-name>, value: "{{api_key}}", placement: header }`
   - `None` → `auth: none`
   - If every request in the group shares the same auth, lift it here and set each request to `auth: inherit`.

Omit `request.headers`/`request.auth` entirely if there is nothing to lift — keep folder files minimal.

---

## 4. Request File (`<group>/<endpoint>.yml`)

Section order is fixed: **`info` → `http` → `settings`**. No `docs`, no `examples`, and no `runtime` in **Spec mode**. *(In **AC-scenario mode** a `runtime.assertions` block is inserted between `http` and `settings` — see §8.2.)*

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

settings:
  encodeUrl: true
```

- `http.method` / `http.url` ← the operation's method + path key (convert `{id}` → `:id` in the URL).
- `params` ← the `parameters` with `in: path` (`type: path`) + `in: query` (`type: query`); each path param in the URL **must** appear here (see §5). `value` = the parameter's example (as a string).
- `body.data` ← the `requestBody…examples.default.value` **verbatim** — this is the single source for the runnable body; never hand-assemble it from the schema. Omit the whole `body` block when the operation has no `requestBody`.
- `auth: inherit` on the request when the folder declares the auth; otherwise set it explicitly per §3.

---

## 5. Path Parameter Handling

In the **runnable** collection a path parameter appears in **two** places (the native `{id}` form lives in the spec, which this skill reads but does not write):

| Place | Form | Why |
|-------|------|-----|
| `http.url` (YAML string) | `:id` | Bruno's runner reads this to substitute path params. |
| `http.params` (YAML list) | `name: id, type: path` | So Bruno's UI shows an editable param field. |

Read the `{id}` form from the operation's path key + its `in: path` `parameters`, then always emit `:id` in the URL string and `name: id, type: path` in `params`. `colcheck.py` enforces that the two stay in sync.

---

## 6. `seq` Assignment

- **Folders** — `seq: 10, 20, 30…` in the order the `tags` appear in the spec.
- **Requests inside a folder** — `seq: 10, 20, 30…` in the order operations appear in the group.
- **Gaps of 10** let a later update insert an entry without renumbering siblings.
- **Update mode:** add a new request at `highest seq + 10`; don't slot between existing ones (noisy diffs).
- `seq` is **per-folder** — two folders may both start at `seq: 10`. Don't make it globally unique.

---

## 7. Display Names

| Where | Rule | Example |
|-------|------|---------|
| `info.name` in request | the operation's `summary` verbatim (already space-separated) | `Accept Consent` |
| `info.name` in folder | the `tags[0]` group name → Title Case | `consent` → `Consent`; `account_service` → `Account Service` |
| Filename | name by operation (path + method), `.yml` | `accept-consent.yml` |

---

## 8. AC-scenario source mode (the AC→request join)

Applies **only in AC-scenario mode** (SKILL.md `## Source mode`). Instead of one request per spec operation, emit **one request per Ready AC** — a runnable test scenario that asserts the AC's expected outcome. The OpenAPI spec stays the **contract anchor** (method/path/params/auth/schema); neo's `docs/design/<usecase>/` supplies the scenario layer. Spec mode (§0–§7) is unchanged.

### 8.0 Inputs + join order (AC-first · TC-enrichment · spec-anchored)

Read from `docs/design/<usecase>/`; the spec at `bruno/openapi/openapi.yaml` stays the contract anchor.

| Need | Source (in order) | Grep target |
|---|---|---|
| AC inventory + Ready/Blocked | `acceptance-criteria.html` (**required**) | `<ac-card id="AC-NNN" status="ready\|blocked">` |
| endpoint (method + path) | a tracing `<tc-card>` `endpoint=` if present → else `traceability.html` (AC→element) → `api-contracts.html` (Covers-AC) → match a spec op | `<tc-card traces="AC-NNN" endpoint="METHOD /path">` |
| request body | TC `<req>` **verbatim** if present → else the spec op's base example adjusted per the AC `<g>/<w>` (judgment → flag L2) | `<tc-card>…<req>…</req>` |
| expected status | TC `<res>` leading `HTTP NNN` if present → else parse the AC `<t>` (THEN, best-effort) | `<res>HTTP NNN…</res>` |
| error code (error scenarios) | a `<res>` body field whose value is a **stable code** (UPPER_SNAKE, e.g. `DENOMINATION_NOT_SUPPORTED`) → else status-only | `<res>` body JSON |

`test-cases.html` is **optional enrichment** — when an AC has a tracing `<tc-card>`, copy its `<req>`/`<res>`/`endpoint` (highest fidelity; QA already derived the per-scenario data); when absent, derive from the AC + spec and flag for L2. **Do not** run `bru import openapi` in this mode — the importer is endpoint-driven (1 file per operation) and cannot emit N requests per endpoint.

### 8.1 Per-scenario request file

One file per **Ready** AC, grouped by usecase folder:

| Source | → Collection |
|---|---|
| usecase name | `<usecase>/` folder (+ `folder.yml`, §3) |
| AC-ID + scenario name | filename `ac-<nnn>-<scenario-slug>.yml`; `info.name: "AC-NNN — <scenario name>"` |
| spec op (resolved per §8.0) | `http.method` + `http.url` (`{id}`→`:id`, §5); `params` (§0/§5); `auth` (§3) |
| body (§8.0 / §8.3) | `http.body.data` verbatim block scalar `\|-`; omit `body` when the op has none |
| status + error (§8.0 / §8.2) | `runtime.assertions` |

Section order is **`info → http → runtime → settings`** (`runtime` is new to this mode).

### 8.2 `runtime.assertions` (this mode only — opens the `runtime` block)

```yaml
runtime:
  assertions:
    - expression: res.status
      operator: eq
      value: "400"
    - expression: res.body.error
      operator: eq
      value: "DENOMINATION_NOT_SUPPORTED"
```

- The `res.status` assertion is **mandatory**; `value` is the expected HTTP status as a quoted 3-digit string.
- Add a `res.body.<field>` assertion **only** when the expected error carries a **stable code** (UPPER_SNAKE). `<field>` is the actual field of the spec `Error` schema present in the `<res>` body (often `error` / `errorCode` / `code`). When the error value is a human message (e.g. `"Invalid denomination"`), emit the status assertion **only** and leave the body to fresh-eyes — **never assert message text** (brittle).
- `operator`: `eq` for status/code; `isNotEmpty` when an error body is expected but no stable code exists.
- **Omit `disabled`** — assertions are enabled so `bru run` validates them.

### 8.3 Body derivation precedence
1. TC `<req>` present → copy **verbatim** (values already scenario-specific; no L2 flag for the values).
2. No TC → spec op base example, hand-adjusted to the AC `<g>/<w>` (an "invalid input" AC carries the offending value) → **flag for L2** ("scenario body differs from base example by design — confirm vs the AC GIVEN/WHEN").

Never assemble a body from the schema.

### 8.4 Blocked + non-mappable ACs
- **Blocked AC** (`status="blocked"`) → **list + skip**, never emit a request (mirrors neo excluding Blocked from the Dev Loop).
- An AC tracing to a **validation rule / module method / cross-cutting concern** (e.g. audit logging) with **no concrete HTTP target** → list under "ACs not mappable to an HTTP request"; do not invent a request. (Many error-rule ACs *are* reachable as an error scenario on the enforcing endpoint — emit those; only the genuinely target-less ones go here.)
- An AC whose endpoint is **not yet in the spec** (spec lag) → emit best-effort + flag; `colcheck.py` reports it as a NOTE, not an ERROR.

### 8.5 Multiple ACs, one endpoint
Expected (N requests : 1 endpoint) — each Ready AC gets its own file; **no dedup**. The `ac-<nnn>-` prefix keeps filenames unique even when two scenarios share a slug. `seq` is per usecase folder (10, 20, 30…, §6).
