# OpenCollection YAML — Schema Reference (v1.0.0)

Authoritative key/section reference for files this skill writes. Distilled from the OpenCollection spec ([docs](https://docs.usebruno.com/opencollection-yaml/structure-reference)) and the steering files used in the `tcrb/bruno-api-documents` workspace.

This skill writes a **subset** of the spec — only the sections needed to represent a request generated from Go source. Optional features the skill never emits (graphql body, oauth2, awsv4, multipart with file streams, etc.) are listed in the Auth Types and Body Types tables for completeness but are not used by the generator unless detected in code.

---

## File Roles

| File | Purpose |
|------|---------|
| `opencollection.yml` | Collection root. One per collection. Holds `info` + bundling/ignore config. |
| `environments/<NAME>.yml` | One file per environment. Holds variables (including secrets). |
| `<folder>/folder.yml` | Folder metadata + inherited headers/auth for child requests. |
| `<folder>/<request>.yml` | One HTTP request. `info` + `http` + (optional `runtime`) + `settings` + (optional `examples`) + (optional `docs`). |

---

## `opencollection.yml` (Collection Root)

```yaml
opencollection: 1.0.0

info:
  name: <Service Name>

docs: |-
  # <Service Name> API

  <Overview paragraph — what the service does.>

  ## Common Error Responses

  | Status | Error Message | Description |
  | ------ | ------------- | ----------- |
  | 400 | invalid request | Request body or query param invalid |
  | 401 | unauthorized | Missing or invalid authentication |
  | 500 | internal server error | Unexpected server-side failure |

bundled: false

extensions:
  bruno:
    ignore:
      - node_modules
      - .git
```

| Key | Required | Notes |
|-----|----------|-------|
| `opencollection` | yes | Schema version. Always `1.0.0` for this skill. |
| `info.name` | yes | Display name shown in Bruno UI. Use the service name from `CLAUDE.md`. |
| `docs` | yes | Collection-root markdown (`\|-` block) — service overview + Common Error Responses table. `publish` syncs it to the Confluence **parent page**. Replaces the old `index.md`. See [`request-template.md`](request-template.md) §1 + [`api-doc-template.md`](api-doc-template.md) § Index Template. |
| `bundled` | no | `false` for multi-file collections (always false for this skill). |
| `extensions.bruno.ignore` | no | Path globs Bruno's runner skips. Default to `node_modules` and `.git`. |

---

## `environments/<NAME>.yml`

```yaml
name: LOCAL
variables:
  - name: baseUrl
    value: http://localhost:8080
  - name: auth_token
    value: ""
    secret: true
  - name: device_id
    value: "00000000-0000-0000-0000-000000000000"
```

| Key | Required | Notes |
|-----|----------|-------|
| `name` | yes | Environment name (LOCAL, SIT, UAT, PROD). Uppercase per the steering convention. |
| `variables[].name` | yes | Variable identifier (used in `{{name}}` interpolation). |
| `variables[].value` | yes | String. Leave `""` for secrets — never commit real credentials. |
| `variables[].secret` | no | `true` masks the value in Bruno's UI/logs. Use for tokens, PINs, biometric data. |

**Generator behavior:**
- Always emit `baseUrl` even if the code uses a different name — the user can rename.
- Add a variable for each `{{<name>}}` reference seen in route paths, middleware headers, or path/query params.
- For values that look like secrets (token, pin, otp, password, key, secret, biometric, national_id, citizen_id where it's the *requester's* identity), emit them with `secret: true` and `value: ""`.

---

## `folder.yml`

Two patterns exist in the wild — this skill uses the **full** pattern because the user opted into CoreTeam2-style folders.

```yaml
info:
  name: <Folder Display Name>
  type: folder
  seq: 1

request:
  headers:
    - name: Accept-Language
      value: TH
    - name: X-Device-ID
      value: "{{device_id}}"
  auth: inherit
```

| Key | Required | Notes |
|-----|----------|-------|
| `info.name` | yes | Display name (e.g., `Consent`, `Channel`). Derived from the handler subdirectory. |
| `info.type` | yes | Always `folder`. |
| `info.seq` | yes | Sort order among sibling folders. Assign 10, 20, 30… in the order groups appear in the route registration file. |
| `request.headers` | no | Headers inherited by every request inside this folder. Lift here when every request shares the same header. |
| `request.auth` | no | Auth inherited by child requests. Values: `inherit`, `none`, or an explicit auth block (see Auth Types). |

---

## Request File (`<request>.yml`)

Section order (this skill emits in exactly this order):

```yaml
info: ...
http: ...
settings: ...
docs: |-
  ...
```

No `runtime` section. No `examples` section. The user opted out of generating tests/assertions/scripts.

### `info`

```yaml
info:
  name: Accept Consent
  type: http
  seq: 10
```

| Key | Required | Notes |
|-----|----------|-------|
| `name` | yes | Display name. PascalCase → space-separated (`AcceptConsent` → `Accept Consent`). |
| `type` | yes | Always `http` for HTTP requests. |
| `seq` | yes | Sort order **within this folder**. Skill assigns 10, 20, 30 to leave room for inserts. |

### `http`

```yaml
http:
  method: POST
  url: "{{baseUrl}}/api/v1/consents/:id"
  params:
    - name: id
      value: "uuid-v4"
      type: path
    - name: page
      value: "1"
      type: query
  headers:
    - name: Content-Type
      value: application/json
  body:
    type: json
    data: |-
      {
        "purpose_code": "MARKETING",
        "channel_id": "uuid-channel-1"
      }
  auth: inherit
```

| Key | Required | Notes |
|-----|----------|-------|
| `method` | yes | `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`, `HEAD`. |
| `url` | yes | Always quoted when it contains `{{vars}}` or `:params`. Use Bruno-style `:name` for path params, regardless of framework syntax in source (`:id` → `:id`, `{id}` → `:id`). |
| `params` | no | All path **and** query params declared explicitly. `type: path` or `type: query`. Path params must match the placeholders in the URL string. |
| `headers` | no | Per-request headers only. Folder-level shared headers belong in `folder.yml`. |
| `body.type` | only if body | `json`, `text`, `xml`, `form-urlencoded`, `multipart-form`, `graphql`. This skill emits `json` for application/json bodies; `form-urlencoded` for `application/x-www-form-urlencoded`. |
| `body.data` | only if body | **String**, not a map. Use `|-` block scalar to preserve multi-line JSON formatting. |
| `auth` | yes | `inherit` (default — read from `folder.yml`), `none`, or an explicit auth block. |

### `settings`

```yaml
settings:
  encodeUrl: true
```

Always emit `encodeUrl: true` at minimum (per steering rule 4). Other settings (`timeout`, `followRedirects`, `maxRedirects`) are only emitted when the user has explicitly asked or the source code suggests them.

### `docs`

```yaml
docs: |-
  # <Name>

  <Description>

  - **Method:** `POST`
  - **Path:** `/api/v1/consents`
  - **Auth:** `Bearer token`

  ## Request Body
  ...
```

Block-scalar markdown. Structure mirrors the per-endpoint template — see [`request-template.md`](request-template.md) for the full layout.

---

## Auth Types

`auth: inherit` is the default for request files; the actual auth is set on the folder. The explicit forms (used in `folder.yml.request.auth` when needed):

| Type | YAML shape | When the generator emits it |
|------|-----------|------------------------------|
| `inherit` | `auth: inherit` | Default — request defers to folder, folder defers to parent. |
| `none` | `auth: none` | Route has no auth middleware. |
| `bearer` | `auth: { type: bearer, token: "{{auth_token}}" }` | JWT/Bearer middleware detected on the route group. |
| `apikey` | `auth: { type: apikey, key: X-API-Key, value: "{{api_key}}", placement: header }` | API key middleware detected. |
| `basic` | `auth: { type: basic, username: "{{basic_user}}", password: "{{basic_pass}}" }` | Basic-auth middleware detected. |
| `digest` | `auth: { type: digest, username: ..., password: ... }` | Rare — emit only if explicitly detected. |
| `oauth2` | full oauth2 config | Skill does not emit by default — flag for user to configure. |
| `awsv4` | full awsv4 config | Skill does not emit by default — flag for user to configure. |

When the same auth applies to every folder in the collection, prefer setting it on the folders rather than the root, because real codebases usually have *some* unauthenticated routes (health, version, login) and a root-level auth forces every folder to override.

---

## Body Types

| `body.type` | Notes |
|-------------|-------|
| `json` | `body.data` is the JSON payload as a string. Use `|-`. |
| `text` | Raw text. `body.data` is a string. |
| `xml` | XML string in `body.data`. |
| `form-urlencoded` | `body.data` is an array of `{ name, value }`. |
| `multipart-form` | Array of `{ name, value, type }`. `type: file` for file uploads. Skill flags multipart for manual review — file paths are user-specific. |
| `graphql` | `body.data` has `query` and `variables` keys. Skill does not emit by default. |

This skill only emits `json` and `form-urlencoded` automatically. Other types are flagged for the user to confirm.

---

## Variables and Interpolation

| Syntax | Where | Purpose |
|--------|-------|---------|
| `{{varName}}` | URL, headers, body string, params, auth fields | Read from environment or runtime variable. |
| `{{process.env.VAR}}` | `runtime.variables[].value` only | Read from OS env (via `.env` file). Used for real secrets. The skill never writes a literal value here. |
| `bru.getEnvVar(name)` / `bru.setEnvVar(name, val)` | Scripts | Read/write env var from JS. Skill does not emit scripts. |
| `bru.getVar(name)` / `bru.setVar(name, val)` | Scripts | Read/write collection-scoped runtime variable. Skill does not emit scripts. |

---

## YAML Rules This Skill Must Follow

1. **Always quote URLs containing `{{vars}}` or `:params`.** Unquoted `{` starts a YAML flow mapping and breaks parsing.
2. **Use `|-` block scalar for JSON `body.data`** so newlines and indentation are preserved literally.
3. **Use `|-` block scalar for `docs:`** so markdown formatting survives.
4. **Two-space indentation throughout.** No tabs.
5. **List items use `- key: value` form**, one item per block — easier to diff than the flow form `[{...}, {...}]`.
6. **Strings that look like booleans, numbers, dates, or `yes/no/null` must be quoted.** Example: `value: "1"` not `value: 1` when the variable should be a string. The skill always quotes `param.value` strings.
7. **`seq` is an integer**, not a string. Write `seq: 10`, not `seq: "10"`.
8. **Comments are allowed (`# ...`)** but the skill avoids them in generated files — the doc lives in `docs:` instead.

---

## Reference Files Pointed To By This Skill

When the skill needs deeper context on a specific area, it reads these siblings in the same `api-doc/references/` directory:

- [`go-scan-patterns.md`](go-scan-patterns.md) — Go route/handler/usecase/struct scanning patterns (1000+ lines).
- [`api-doc-template.md`](api-doc-template.md) — Field/error documentation conventions (M/O rules, field-description formulas, example-value lookup, verification checklist).
