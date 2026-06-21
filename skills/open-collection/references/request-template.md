# Open Collection — Templates

Templates for every file this skill writes when it turns the `docs/api/*.yaml` **API spec** (custom YAML) into a **runnable** Bruno OpenCollection. Section ordering and indentation are part of the contract — follow them exactly so output is byte-stable across runs.

**The collection is self-documenting (Spec mode)** — each request embeds a generated `docs:` block rendered from its api-spec endpoint (via `yaml2md.py`), and the collection root + folders carry the `_meta` overview / group prose. The runnable bits (URLs, params, bodies, headers, auth, environments) come from the same api-spec. **AC-scenario mode** (§8) instead emits a `runtime.assertions` block per request and **carries no `docs:`** (a scenario's assertions are its contract). Confluence publishing reads the api-spec directly (the `confluence-api-doc` skill). For schema-level details on each YAML key, see [`yaml-reference.md`](yaml-reference.md).

---

## 0. Reading the api-spec source (the input contract)

Input is the `docs/api/*.yaml` custom-YAML **API spec** (the `neo` Architect's output; drift-checked against Go by `openapi-doc`). One `<domain>/<endpoint>.yaml` = one endpoint; `_meta.yaml` holds the service-level metadata. **Do not scan Go** (the api-spec was already drift-checked against the code). There is **no `bru import openapi`** — the custom YAML is not OpenAPI; **hand-map** each endpoint:

| api-spec element | → Collection field |
|---|---|
| `_meta.base_url` (+ a dev port from config) | the `{{baseUrl}}` env value (host/base) |
| a `<domain>/<endpoint>.yaml` file | one request `.yml` (folder = its `domain`) |
| `endpoint` | request `info.name` |
| `method` + `path` | `http.method` + `http.url` = `"{{baseUrl}}<path with {id}→:id>"` |
| `path_params[]` | a `params` row `type: path` (+ `:id` in the url) |
| `query_params[]` | a `params` row `type: query` |
| `auth` (`Bearer …`/`API Key`/`None`) | request/folder `auth` (§3) — bearer→bearer, apikey→apikey, None→none |
| `request_body.example` | `http.body.data` **verbatim** (the runnable body — already JSON-ready) |
| the whole endpoint (description / params / fields / business_logic / errors) | rendered into the request **`docs:`** by `yaml2md.py` (Spec mode) |
| `_meta` (overview / field_info / common_errors) | the collection-root `docs:`; `_meta.domains.<d>` → the folder `docs:` |

- **Grouping** comes from the endpoint's `domain` (→ collection folder), mirroring the api-spec's by-domain tree.
- Response field tables / `objects:` / `errors:` are doc-only for the runnable request, but **are** rendered into `docs:` (Spec mode) by `yaml2md.py` — never hand-write the `docs:` markdown.
- An endpoint with no `request_body` → request has **no** `http.body`.

---

## 1. `opencollection.yml`

```yaml
opencollection: 1.0.0

info:
  name: <Service Name>

docs: |-
  <the _meta INDEX render — Spec mode>

bundled: false

extensions:
  bruno:
    ignore:
      - node_modules
      - .git
```

`<Service Name>` ← CLAUDE.md project name, or `info.title` from go.mod if available. **`docs:`** (Spec mode) = `python3 <ASSET_DIR>/yaml2md.py --index docs/api/_meta.yaml docs/api` (the service overview, Field Information, the by-domain endpoint list, and Common Error Responses). Omit `docs:` in AC-scenario mode. The api-spec source lives under `docs/api/` (outside the collection root), so no `ignore` entry is needed for it.

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

docs: |-
  <the _meta.domains.<group> prose — Spec mode, when present>

request:
  headers:
    - name: <header-name>
      value: <header-value-or-{{var}}>
  auth: <inherit | none | {type, ...}>
```

**Discovery rules:**

1. **`info.name`** — the `domain` → Title Case, or `_meta.domains.<domain>.title` when set (`account` → `Account`).
2. **`info.seq`** — `10, 20, 30…` in `_meta.domains` order (by `seq`).
3. **`docs:`** (Spec mode) — the domain's group prose from `_meta.domains.<group>` (`title` + `description`) when present; omit when there is none, and omit entirely in AC-scenario mode.
4. **`request.headers`** — any header sent by **every** request in the group goes here; per-request headers stay in the request file.
5. **`request.auth`** — derive from the endpoints' `auth`:
   - `Bearer token` → `auth: { type: bearer, token: "{{auth_token}}" }`
   - `API Key` → `auth: { type: apikey, key: <header-name>, value: "{{api_key}}", placement: header }`
   - `None` → `auth: none`
   - If every request in the group shares the same auth, lift it here and set each request to `auth: inherit`.

Omit `request.headers`/`request.auth` entirely if there is nothing to lift — keep folder files minimal.

---

## 4. Request File (`<group>/<endpoint>.yml`)

Section order is fixed: **`info` → `http` → `docs` → `settings`** (Spec mode). No `examples`, no `runtime` in Spec mode. *(In **AC-scenario mode** the order is `info → http → runtime → settings` — a `runtime.assertions` block replaces `docs:`; see §8.2.)*

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

docs: |-
  <the endpoint render — Spec mode>

settings:
  encodeUrl: true
```

- `http.method` / `http.url` ← the endpoint's `method` + `path` (convert `{id}` → `:id` in the URL).
- `params` ← `path_params` (`type: path`) + `query_params` (`type: query`); each path param in the URL **must** appear here (see §5). `value` = the param's `example` (as a string).
- `body.data` ← the endpoint's `request_body.example` **verbatim** — this is the single source for the runnable body; never hand-assemble it. Omit the whole `body` block when the endpoint has no `request_body`.
- **`docs:`** (Spec mode) ← `python3 <ASSET_DIR>/yaml2md.py docs/api/<group>/<endpoint>.yaml` — the rendered endpoint Markdown, copied verbatim into the block scalar. **Never hand-write it**; `colcheck.py` K7 fails any request whose `docs:` ≠ this render. Omit `docs:` entirely in AC-scenario mode.
- `auth: inherit` on the request when the folder declares the auth; otherwise set it explicitly per §3.

---

## 5. Path Parameter Handling

In the **runnable** collection a path parameter appears in **two** places (the native `{id}` form lives in the api-spec `path`, which this skill reads but does not write):

| Place | Form | Why |
|-------|------|-----|
| `http.url` (YAML string) | `:id` | Bruno's runner reads this to substitute path params. |
| `http.params` (YAML list) | `name: id, type: path` | So Bruno's UI shows an editable param field. |

Read the `{id}` form from the endpoint's `path` + its `path_params`, then always emit `:id` in the URL string and `name: id, type: path` in `params`. `colcheck.py` enforces that the two stay in sync.

---

## 6. `seq` Assignment

- **Folders** — `seq: 10, 20, 30…` in `_meta.domains` order (by `seq`).
- **Requests inside a folder** — `seq: 10, 20, 30…` in the order endpoints appear in the group (file order).
- **Gaps of 10** let a later update insert an entry without renumbering siblings.
- **Update mode:** add a new request at `highest seq + 10`; don't slot between existing ones (noisy diffs).
- `seq` is **per-folder** — two folders may both start at `seq: 10`. Don't make it globally unique.

---

## 7. Display Names

| Where | Rule | Example |
|-------|------|---------|
| `info.name` in request | the endpoint's `endpoint` name verbatim | `Create`; `Get Account` |
| `info.name` in folder | the `domain` → Title Case (or `_meta.domains.<d>.title`) | `account` → `Account` |
| Filename | the endpoint file stem, `.yml` | `create.yml`; `get.yml` |

---

## 8. AC-scenario source mode (the AC→request join)

Applies **only in AC-scenario mode** (SKILL.md `## Source mode`). Instead of one request per api-spec endpoint, emit **one request per Ready AC** — a runnable test scenario that asserts the AC's expected outcome. The api-spec stays the **contract anchor** (method/path/params/auth/fields); neo's `docs/design/<usecase>/` supplies the scenario layer. Spec mode (§0–§7) is unchanged. AC-scenario requests carry **no `docs:`** — the assertions are the contract.

### 8.0 Inputs + join order (AC-first · TC-enrichment · api-spec-anchored)

Read from `docs/design/<usecase>/`; the api-spec at `docs/api/*.yaml` stays the contract anchor.

| Need | Source (in order) | Grep target |
|---|---|---|
| AC inventory + Ready/Blocked | `acceptance-criteria.html` (**required**) | `<ac-card id="AC-NNN" status="ready\|blocked">` |
| endpoint (method + path) | a tracing `<tc-card>` `endpoint=` if present → else `traceability.html` (AC→element) → the api-spec endpoint whose `covers_ac:` lists the AC → match | `<tc-card traces="AC-NNN" endpoint="METHOD /path">` · `covers_ac: [AC-NNN]` |
| request body | TC `<req>` **verbatim** if present → else the api-spec endpoint's `request_body.example` adjusted per the AC `<g>/<w>` (judgment → flag L2) | `<tc-card>…<req>…</req>` |
| expected status | TC `<res>` leading `HTTP NNN` if present → else parse the AC `<t>` (THEN, best-effort) | `<res>HTTP NNN…</res>` |
| error code (error scenarios) | a `<res>` body field whose value is a **stable code** (UPPER_SNAKE, e.g. `DENOMINATION_NOT_SUPPORTED`) → else status-only | `<res>` body JSON |

`test-cases.html` is **optional enrichment** — when an AC has a tracing `<tc-card>`, copy its `<req>`/`<res>`/`endpoint` (highest fidelity; QA already derived the per-scenario data); when absent, derive from the AC + api-spec and flag for L2. Always **hand-map** (there is no importer); AC-scenario is N requests per endpoint, one per Ready AC.

### 8.1 Per-scenario request file

One file per **Ready** AC, grouped by usecase folder:

| Source | → Collection |
|---|---|
| usecase name | `<usecase>/` folder (+ `folder.yml`, §3) |
| AC-ID + scenario name | filename `ac-<nnn>-<scenario-slug>.yml`; `info.name: "AC-NNN — <scenario name>"` |
| api-spec endpoint (resolved per §8.0) | `http.method` + `http.url` (`{id}`→`:id`, §5); `params` (§0/§5); `auth` (§3) |
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
- Add a `res.body.<field>` assertion **only** when the expected error carries a **stable code** (UPPER_SNAKE — an api-spec `errors[].code` / `_meta.common_errors[].code`). `<field>` is the actual field the error response body uses (often `error` / `errorCode` / `code`). When the error value is a human message (e.g. `"Invalid denomination"`), emit the status assertion **only** and leave the body to fresh-eyes — **never assert message text** (brittle).
- `operator`: `eq` for status/code; `isNotEmpty` when an error body is expected but no stable code exists.
- **Omit `disabled`** — assertions are enabled so `bru run` validates them.

### 8.3 Body derivation precedence
1. TC `<req>` present → copy **verbatim** (values already scenario-specific; no L2 flag for the values).
2. No TC → the api-spec endpoint's `request_body.example`, hand-adjusted to the AC `<g>/<w>` (an "invalid input" AC carries the offending value) → **flag for L2** ("scenario body differs from base example by design — confirm vs the AC GIVEN/WHEN").

Never assemble a body from the field tables.

### 8.4 Blocked + non-mappable ACs
- **Blocked AC** (`status="blocked"`) → **list + skip**, never emit a request (mirrors neo excluding Blocked from the Dev Loop).
- An AC tracing to a **validation rule / module method / cross-cutting concern** (e.g. audit logging) with **no concrete HTTP target** → list under "ACs not mappable to an HTTP request"; do not invent a request. (Many error-rule ACs *are* reachable as an error scenario on the enforcing endpoint — emit those; only the genuinely target-less ones go here.)
- An AC whose endpoint is **not yet in the api-spec** (spec lag) → emit best-effort + flag; `colcheck.py` reports it as a NOTE, not an ERROR.

### 8.5 Multiple ACs, one endpoint
Expected (N requests : 1 endpoint) — each Ready AC gets its own file; **no dedup**. The `ac-<nnn>-` prefix keeps filenames unique even when two scenarios share a slug. `seq` is per usecase folder (10, 20, 30…, §6).
