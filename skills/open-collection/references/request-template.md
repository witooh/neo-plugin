# Open Collection — Templates

Templates for every file this skill writes when it turns the `bruno/openapi/` OpenAPI spec into a **runnable** Bruno OpenCollection. Section ordering and indentation are part of the contract — follow them exactly so output is byte-stable across runs.

**The collection is runnable-only.** It carries no `docs:` blocks — the human-readable documentation stays in the `bruno/openapi/` OpenAPI spec (the single source of truth), and Confluence publishing reads that spec directly (the `confluence-api-doc` skill). This skill's job is purely the *runnable* artifact: URLs, params, bodies, headers, auth, environments. For schema-level details on each YAML key, see [`yaml-reference.md`](yaml-reference.md).

---

## 0. Reading the OpenAPI spec source (the input contract)

Input is the `bruno/openapi/` split spec (the `openapi-doc` skill's output). The **runnable** bits come from each **operation**; **do not re-scan Go** (the spec was already verified against the code). **Prefer Bruno's native importer** (`bru import openapi … --collection-format=opencollection`), which resolves `$ref`s and emits the collection in one step; then post-process to the conventions below. If `bru` is unavailable, hand-map each operation:

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
| `responses` / `x-business-logic` / `x-error-catalog` | not used (doc-only — they stay in the spec) |

- **Grouping** comes from the operation's `tags[0]` (→ collection folder), mirroring the spec's `paths/<group>/` layout.
- `components/schemas/*` are resolved only to shape the body example — they are not emitted into the collection.
- An operation with no `requestBody` → request has **no** `http.body`.
- The spec is split with `$ref`; resolve refs (Bruno's importer does this; a hand-map follows them) before reading an operation whole.

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

Section order is fixed: **`info` → `http` → `settings`**. No `docs`, no `runtime`, no `examples`.

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
