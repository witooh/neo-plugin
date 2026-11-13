# OpenCollection YAML: Schema Reference (v1.0.0)

Authoritative key/section reference for files this skill writes. Distilled from the OpenCollection spec ([docs](https://docs.usebruno.com/opencollection-yaml/structure-reference)) and the steering files used in the `tcrb/bruno-api-documents` workspace.

This skill writes a **subset** of the OpenCollection spec: the sections needed for a runnable request whose `docs:` block is the endpoint's contract. Optional features the skill never emits (graphql body, oauth2, awsv4, multipart with file streams, etc.) are listed in the Auth Types and Body Types tables for completeness but are not used unless the contract calls for them. The `docs:` layout itself is [`docs-template.md`](docs-template.md).

---

## File Roles

| File | Purpose |
|------|---------|
| `opencollection.yml` | Collection root. One per collection. Holds `info` + bundling/ignore config + the service-level `docs:`. |
| `environments/<NAME>.yml` | One file per environment. Holds variables (including secrets). |
| `<folder>/folder.yml` | Folder metadata + inherited headers/auth for child requests. |
| `<folder>/<request>.yml` | One **runnable** HTTP request. `info` + `http` + `runtime` + `settings` + `docs`: `docs:` is the endpoint's contract. |

---

## `opencollection.yml` (Collection Root)

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

docs: |-
  <the collection-root docs: Overview, Field Information, Error Response Body, Common Error Responses>
```

| Key | Required | Notes |
|-----|----------|-------|
| `opencollection` | yes | Schema version. Always `1.0.0` for this skill. |
| `info.name` | yes | Display name shown in Bruno UI. Use the service name from `CLAUDE.md`. |
| `docs` | yes | The service-level contract: `## Overview`, optional `## Field Information`, required `## Error Response Body` and `## Common Error Responses` (K11). Layout in [`docs-template.md`](docs-template.md). |
| `bundled` | no | `false` for multi-file collections (always false for this skill). |
| `extensions.bruno.ignore` | no | Path globs Bruno's runner skips. Default to `node_modules` + `.git`. |

---

## `environments/<NAME>.yml`

```yaml
name: local
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
| `name` | yes | Environment name (local, sit, uat, prod). Lowercase. |
| `variables[].name` | yes | Variable identifier (used in `{{name}}` interpolation). |
| `variables[].value` | yes | String. Leave `""` for secrets: never commit real credentials. |
| `variables[].secret` | no | `true` masks the value in Bruno's UI/logs. Use for tokens, PINs, biometric data. |

**Generator behavior:**
- Always emit `baseUrl` even if the code uses a different name: the user can rename.
- Add a variable for each `{{<name>}}` reference in request URLs, headers, params, bodies or auth. K8 counts both `environments/` and the request's own `runtime.variables` as definitions.
- For values that look like secrets (token, pin, otp, password, key, secret, biometric, national_id, citizen_id where it's the *requester's* identity), emit them with `secret: true` and `value: ""`. K8 ERRORs on a committed value for `password` / `secret` / `token` / `bearer` / `otp` / `api key` names and NOTEs one for `pin` / `national` / `citizen` / `cif` / `biometric` names.
- Values: `local` runs as committed and every other environment fills only `baseUrl` (SKILL.md Step 3, `environments/`). Keep each comment with its variable: edit these files as text.

---

## `folder.yml`

Two patterns exist in the wild: this skill uses the **full** pattern because the user opted into CoreTeam2-style folders.

```yaml
info:
  name: <Folder Display Name>
  type: folder
  seq: 10

request:
  headers:
    - name: Accept-Language
      value: TH
    - name: X-Device-ID
      value: "{{device_id}}"
  auth: inherit

docs: |-
  <domain prose, when there is any>
```

| Key | Required | Notes |
|-----|----------|-------|
| `info.name` | yes | Display name (e.g., `Account`, `Balance`): the domain in Title Case. |
| `info.type` | yes | Always `folder`. |
| `info.seq` | yes | Sort order among sibling folders. Assign 10, 20, 30… |
| `request.headers` | no | Headers inherited by every request inside this folder. Lift here when every request shares the same header. |
| `request.auth` | no | Auth inherited by child requests: `inherit` or an explicit auth block (see Auth Types). Omitted when the folder's endpoints share no auth. |
| `docs` | no | Domain prose for callers; omit when there is none. |

---

## Request File (`<request>.yml`)

Section order (this skill emits in exactly this order; K1 enforces it):

```yaml
info: ...
http: ...
runtime: ...    # at least one `type: tests` script (K7)
settings: ...
docs: ...       # the endpoint's contract
```

`examples` is never emitted.

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
| `seq` | yes | Sort order **within this folder**. Skill assigns 10, 20, 30 to leave room for inserts; a new request added by Generate to an existing folder takes the highest `seq` + 10. |

### `http`

```yaml
http:
  method: POST
  url: "{{baseUrl}}/api/v1/consents/:id?page=1"
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
| `method` | yes | `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`, `HEAD`. Matches the `### Endpoint` method (K2). |
| `url` | yes | Always quoted when it contains `{{vars}}` or `:params`. Use Bruno-style `:name` for path params: the `### Endpoint` line's `{id}` becomes `:id` here (K2). Carries the query string too: Bruno CLI 3.3.0 sends only the query the url holds, never a `type: query` row on its own. |
| `params` | no | All path **and** query params declared explicitly. `type: path` or `type: query`. Every `:name` in the URL needs a `type: path` row (K3); every `type: query` row is also in the URL's query string (K13). |
| `headers` | no | Per-request headers only. Folder-level shared headers belong in `folder.yml`. |
| `body.type` | only if body | `json`, `text`, `xml`, `form-urlencoded`, `multipart-form`, `graphql`. This skill emits `json` for application/json bodies; `form-urlencoded` for `application/x-www-form-urlencoded`. |
| `body.data` | only if body | **String**, not a map. Use `|-` block scalar to preserve multi-line JSON formatting. Its key paths equal the `docs:` Body Example's (K5); values may differ and may be `{{vars}}`. A record id the request needs to exist is a `{{var}}`, and an optional id that turns a create into an update is left out (K14 NOTEs a literal id). |
| `auth` | no | `inherit` when `folder.yml` sets the auth, or an explicit auth block. When `### Auth` is `None`: omitted, or `inherit` while no enclosing `folder.yml` sets an auth (K12). |

### `runtime`

```yaml
runtime:
  scripts:
    - type: tests
      code: |-
        test("status is 201", function() { expect(res.status).to.equal(201); });
    - type: after-response   # only in a request whose response holds an id later requests read
      code: |-
        bru.setVar("accountId", res.body.data.accountId);
```

| Key | Required | Notes |
|-----|----------|-------|
| `scripts[].type` | yes | `tests` runs after the response. Bruno also accepts `before-request` and `after-response`; this skill writes `tests`, plus `after-response` in a request whose response holds an id that later requests read (`bru.setVar`), and preserves any others it finds. |
| `scripts[].code` | yes | JavaScript string (`|-`). Assertions use Chai `expect` inside `test("<name>", function() { … })`. The response is `res`: `res.status` or `res.getStatus()`, `res.getBody()`. |
| `variables[]` | no | `{ name, value }` request-scoped variables; `{{process.env.VAR}}` reads a real secret from the OS env. |

- K7: at least one `type: tests` script must reference `res.status` (or `res.getStatus()`). A `runtime.assertions` list does not satisfy K7.
- The default test asserts the first success status: `test("status is 200", function() { expect(res.status).to.equal(200); });`.
- In a Generate on an existing request, `runtime` is user-authored: keep it as-is and add a status test only when none exists.

### `settings`

```yaml
settings:
  encodeUrl: true
```

Always emit `encodeUrl: true` at minimum (per steering rule 4). Other settings (`timeout`, `followRedirects`, `maxRedirects`) are only emitted when the user has explicitly asked or the source code suggests them.

### `docs`

The endpoint's contract: Markdown generated from code, in a `|-` block scalar, a **string**, not a map. Layout, table rules and Audience rules are in [`docs-template.md`](docs-template.md); `brunocheck.py` K2-K6 and K10 check it.

---

## Auth Types

A request whose folder sets the auth reads `auth: inherit`; the auth itself is set on the folder. A request with no auth has no `auth` key: on Bruno CLI 3.3.0 such a request sends no auth even inside a folder that sets one, and `auth: none` fails with `Unsupported auth type`. Under folders that set no auth, `auth: inherit` also runs on Bruno CLI 3.3.0, so K12 accepts it. The forms (the explicit ones go in `folder.yml.request.auth` when needed):

| Type | YAML shape | When the skill emits it |
|------|-----------|-------------------------|
| `inherit` | `auth: inherit` | The folder sets the auth: request defers to folder, folder defers to parent. Also accepted when `### Auth` is `None` and no enclosing folder sets an auth. |
| no auth | no `auth` key | `### Auth` is `None`. Never `auth: none` (K12). |
| `bearer` | `auth: { type: bearer, token: "{{auth_token}}" }` | `### Auth` is a Bearer/JWT token. |
| `apikey` | `auth: { type: apikey, key: X-API-Key, value: "{{api_key}}", placement: header }` | `### Auth` is an API key. |
| `basic` | `auth: { type: basic, username: "{{basic_user}}", password: "{{basic_pass}}" }` | `### Auth` is Basic auth. |
| `digest` | `auth: { type: digest, username: ..., password: ... }` | Rare, emit only if explicitly stated. |
| `oauth2` | full oauth2 config | Skill does not emit by default: flag for user to configure. |
| `awsv4` | full awsv4 config | Skill does not emit by default: flag for user to configure. |

When the same auth applies to every folder in the collection, prefer setting it on the folders rather than the root, because real codebases usually have *some* unauthenticated routes (health, version, login) and a root-level auth forces every folder to override.

---

## Body Types

| `body.type` | Notes |
|-------------|-------|
| `json` | `body.data` is the JSON payload as a string. Use `|-`. |
| `text` | Raw text. `body.data` is a string. |
| `xml` | XML string in `body.data`. |
| `form-urlencoded` | `body.data` is an array of `{ name, value }`. |
| `multipart-form` | Array of `{ name, value, type }`. `type: file` for file uploads. Skill flags multipart for manual review, file paths are user-specific. |
| `graphql` | `body.data` has `query` and `variables` keys. Skill does not emit by default. |

This skill only emits `json` and `form-urlencoded` automatically. Other types are flagged for the user to confirm.

---

## Variables and Interpolation

| Syntax | Where | Purpose |
|--------|-------|---------|
| `{{varName}}` | URL, headers, body string, params, auth fields | Read from environment or runtime variable. |
| `{{process.env.VAR}}` | `runtime.variables[].value` only | Read from OS env (via `.env` file). Used for real secrets. The skill never writes a literal value here. K8 skips these. |
| `bru.getEnvVar(name)` / `bru.setEnvVar(name, val)` | Scripts | Read/write env var from JS. Skill does not emit these; it preserves them. |
| `bru.getVar(name)` / `bru.setVar(name, val)` | Scripts | Read/write a collection-scoped runtime variable, which overrides the environment variable of the same name. The skill emits `bru.setVar` only to store a run-time id (§`runtime`) and preserves any others. |

---

## YAML Rules This Skill Must Follow

1. **Always quote URLs containing `{{vars}}` or `:params`.** Unquoted `{` starts a YAML flow mapping and breaks parsing.
2. **Use `|-` block scalar for JSON `body.data`, `runtime.scripts[].code` and `docs`** so newlines and indentation are preserved literally.
3. **Two-space indentation throughout.** No tabs.
4. **List items use `- key: value` form**, one item per block: easier to diff than the flow form `[{...}, {...}]`.
5. **Strings that look like booleans, numbers, dates, or `yes/no/null` must be quoted.** Example: `value: "1"` not `value: 1` when the variable should be a string. The skill always quotes `param.value` strings.
6. **`seq` is an integer**, not a string. Write `seq: 10`, not `seq: "10"`.
7. **Comments are allowed (`# ...`)** but the skill avoids them in generated files.
