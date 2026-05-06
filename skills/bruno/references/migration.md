# Migrating to Bruno OpenCollection YAML

This is a mapping guide for the three formats users most often arrive with: **curl**, **Postman v2.1 collections**, and **OpenAPI 3.x specs**. Plus a quick `.bru` → `.yml` reference for users who already use Bruno but want to switch formats.

For all conversions, the goal is the same: end up with a request file that drops cleanly into a folder under an `opencollection.yml` and runs.

---

## curl → Bruno YAML

curl is the easiest case. Every flag has a direct equivalent.

```bash
curl -X POST 'https://api.example.com/users?dryRun=true' \
  -H 'Authorization: Bearer eyJhbGc...' \
  -H 'Content-Type: application/json' \
  -d '{"name":"Alice","email":"alice@example.com"}'
```

Becomes:

```yaml
info:
  name: Create User
  type: http
  seq: 10

http:
  method: POST
  url: "{{baseUrl}}/users"
  params:
    - name: dryRun
      value: "true"
      type: query
  headers:
    - name: Content-Type
      value: application/json
  body:
    type: json
    data: |-
      {"name": "Alice", "email": "alice@example.com"}
  auth: inherit              # bearer lifted to collection level
```

And `environments/local.yml`:
```yaml
vars:
  - name: baseUrl
    value: https://api.example.com
  - name: token
    value: ""
    secret: true
```

### Mapping table

| curl | Bruno |
|------|-------|
| `-X METHOD` | `http.method` |
| URL path | `http.url` (lift host into `{{baseUrl}}` env var) |
| `?key=value` in URL | move into `http.params` with `type: query` |
| `-H 'Key: Value'` | `http.headers[]` |
| `-H 'Authorization: Bearer X'` | lift into collection-level `auth: bearer` + `{{token}}` env var |
| `-H 'Authorization: Basic …'` | `auth: { type: basic, username, password }` (don't keep the base64) |
| `-d '…'` (with `Content-Type: application/json`) | `body.type: json`, `body.data: \|- …` |
| `-d 'a=1&b=2'` (form) | `body.type: form-urlencoded` |
| `-F 'file=@path'` | `body.type: multipart-form` with `type: file` |
| `--data-binary @file.json` | `body.type: json`, paste contents into `data` |
| `-u user:pass` | `auth: { type: basic, username, password }` |
| `-G --data-urlencode` | move pairs into `http.params` |
| `-L` (follow redirects) | `settings.followRedirects: true` (default) |
| `--insecure` | not in YAML; runtime concern only |

### Gotchas
- **Don't keep the literal bearer token in the file.** Always lift to env.
- **Multiple `-H` of the same name** are valid in curl. In Bruno, list them as separate header entries — Bruno preserves order.
- **`-d` without `Content-Type`** defaults to form encoding in curl. If that's the intent, use `form-urlencoded`. If the body is JSON-ish, the user almost always meant JSON — confirm if ambiguous.

---

## Postman v2.1 → Bruno YAML

Postman exports are JSON. The structure maps cleanly:

| Postman | Bruno |
|---------|-------|
| `info.name` | root `opencollection.yml` `info.name` |
| `item[]` (folder) | a folder + `folder.yml` |
| `item[]` (request) | one request `*.yml` |
| `request.method` | `http.method` |
| `request.url.raw` | `http.url` |
| `request.url.query[]` | `http.params[]` (`type: query`) |
| `request.url.variable[]` | `http.params[]` (`type: path`) |
| `request.header[]` | `http.headers[]` |
| `request.body.mode: raw` + `options.raw.language: json` | `body.type: json` |
| `request.body.mode: urlencoded` | `body.type: form-urlencoded` |
| `request.body.mode: formdata` | `body.type: multipart-form` |
| `request.body.mode: graphql` | `body.type: graphql` (or top-level `graphql:`) |
| `request.auth.type: bearer` | `auth.type: bearer` |
| `event[].script.exec` (listen `prerequest`) | `runtime.scripts[].type: before-request` |
| `event[].script.exec` (listen `test`) | `runtime.scripts[].type: tests` |
| `{{var}}` in any field | `{{var}}` (same syntax) |

### Script API mapping (Postman → Bruno)

This is the bit that breaks if you copy-paste blindly. Postman uses the `pm.*` namespace; Bruno uses `bru` + `req` + `res`.

| Postman | Bruno |
|---------|-------|
| `pm.environment.get("k")` | `bru.getEnvVar("k")` |
| `pm.environment.set("k", v)` | `bru.setEnvVar("k", v)` |
| `pm.variables.get("k")` | `bru.getVar("k")` |
| `pm.variables.set("k", v)` | `bru.setVar("k", v)` |
| `pm.request.headers.add({key,value})` | `req.setHeader("key", "value")` |
| `pm.response.json()` | `res.body` (already parsed) |
| `pm.response.code` | `res.status` |
| `pm.response.responseTime` | `res.responseTime` |
| `pm.test("name", fn)` | `test("name", fn)` |
| `pm.expect(x).to.equal(y)` | `expect(x).to.equal(y)` |

### Postman environment files

A Postman environment export looks like:
```json
{
  "name": "local",
  "values": [
    {"key": "baseUrl", "value": "http://localhost:3000", "enabled": true}
  ]
}
```
Becomes `environments/local.yml`:
```yaml
vars:
  - name: baseUrl
    value: http://localhost:3000
```
Drop `enabled: false` entries entirely (or carry over with `disabled: true` if the user wants them visible).

### Gotchas
- **Pre-request scripts that fetch tokens** are common in Postman. The Bruno equivalent works the same way — write the token into `bru.setVar("token", …)` and reference `{{token}}` in subsequent requests.
- **Postman collection variables** (the third scope, between env and global) don't have a direct Bruno equivalent. Lift them into the environment, or into `vars` at the collection root.
- **`pm.sendRequest`** for chaining inside a single test doesn't translate. The Bruno way is to make a separate request file and rely on `seq` + shared vars.

---

## OpenAPI 3.x → Bruno YAML

OpenAPI describes *what* the API is. Bruno describes *how to call it*. There's no perfect 1-to-1 — you're generating example invocations, not the spec.

### File layout

- One folder per OpenAPI **tag**.
- One request file per **operation** (path + method).
- Path itself becomes the URL with `{param}` → `{{param}}` (and a `params` entry of `type: path`).

### Per-operation mapping

| OpenAPI | Bruno |
|---------|-------|
| `summary` | `info.name` |
| `description` | `docs:` |
| `operationId` | useful for the file name (kebab-case it) |
| `tags[0]` | parent folder |
| HTTP method | `http.method` |
| Path | `http.url` (with `{{baseUrl}}` prefix from `servers[0].url`) |
| `parameters[].in: path` | `http.params[]` `type: path` |
| `parameters[].in: query` | `http.params[]` `type: query` |
| `parameters[].in: header` | `http.headers[]` |
| `requestBody.content.application/json.example` | `body.data` (string-ified JSON) |
| `requestBody.content.application/json.schema` | invent a body that matches; flag if user wants a schema-driven generator |
| `security: [{bearerAuth: []}]` | `auth: inherit` (with collection-level bearer) |
| `responses.201.description` | not stored; can go into a `tests` script as a comment |

### Example

OpenAPI snippet:
```yaml
paths:
  /users/{id}:
    get:
      operationId: getUser
      tags: [users]
      summary: Get a user
      parameters:
        - in: path
          name: id
          required: true
          schema: { type: string }
      responses:
        '200': { description: OK }
```

Becomes `users/get-user.yml`:
```yaml
info:
  name: Get a user
  type: http
  seq: 10
  tags: [users]

http:
  method: GET
  url: "{{baseUrl}}/users/:id"
  params:
    - name: id
      value: "{{userId}}"
      type: path
  auth: inherit

runtime:
  assertions:
    - expression: res.status
      operator: eq
      value: "200"

docs: |-
  Returns the user with the given id.
```

### Gotchas
- **OpenAPI doesn't tell you which environment to hit.** Take `servers[0].url` as the default `baseUrl` and ask if there are others (staging, prod).
- **Schema-only request bodies** require you to fabricate values. Use the `example`/`examples` if present; otherwise generate something plausible and flag it for review.
- **`oneOf` / `anyOf` request bodies** can't be represented as a single Bruno request — generate one file per variant if it matters.

---

## `.bru` → OpenCollection YAML

If the user is already on Bruno but wants to switch from the original `.bru` format to YAML, the structure is the same — only the syntax differs.

`.bru`:
```
meta {
  name: Create User
  type: http
  seq: 2
}
post {
  url: {{baseUrl}}/users
  body: json
  auth: inherit
}
headers {
  Content-Type: application/json
}
body:json {
  {"name": "Alice"}
}
auth:bearer {
  token: {{token}}
}
script:pre-request {
  bru.setVar("traceId", crypto.randomUUID());
}
tests {
  test("status 201", function() {
    expect(res.status).to.equal(201);
  });
}
```

YAML:
```yaml
info:
  name: Create User
  type: http
  seq: 2

http:
  method: POST
  url: "{{baseUrl}}/users"
  headers:
    - name: Content-Type
      value: application/json
  body:
    type: json
    data: |-
      {"name": "Alice"}
  auth:
    type: bearer
    token: "{{token}}"

runtime:
  scripts:
    - type: before-request
      code: |-
        bru.setVar("traceId", crypto.randomUUID());
    - type: tests
      code: |-
        test("status 201", function() {
          expect(res.status).to.equal(201);
        });
```

### Mapping cheatsheet

| `.bru` block | YAML location |
|--------------|---------------|
| `meta { name, type, seq }` | `info` |
| `get { url }` / `post { url }` etc. | `http.method` (from block name) + `http.url` |
| `headers { K: V }` | `http.headers[]` |
| `query { K: V }` | `http.params[]` `type: query` |
| `body:json { … }` | `body.type: json`, `body.data` |
| `body:form-urlencoded { K: V }` | `body.type: form-urlencoded`, `body.data` array |
| `auth:bearer { token }` | `auth: { type: bearer, token }` |
| `auth:basic { user, pass }` | `auth: { type: basic, username, password }` |
| `script:pre-request { … }` | `runtime.scripts[].type: before-request` |
| `script:post-response { … }` | `runtime.scripts[].type: after-response` |
| `tests { … }` | `runtime.scripts[].type: tests` |
| `assert { res.status: eq 200 }` | `runtime.assertions[]` |
| `vars:pre-request { K: V }` | `vars` (or set in a `before-request` script) |
| `docs { … }` | `docs:` |

The folder layout (`environments/`, `folder.bru` → `folder.yml`, request files) is identical between formats. Only the file extension and inner syntax change.
