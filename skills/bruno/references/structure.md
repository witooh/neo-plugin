# Bruno OpenCollection YAML — Full Structure Reference

A request file (`*.yml` inside a collection) has up to five top-level keys:

| Key | Required | Purpose |
|-----|----------|---------|
| `info` | yes | Metadata (name, type, seq, tags) |
| `http` | yes (for HTTP requests) | Method, URL, params, headers, body, auth |
| `graphql` | alt | Use **instead of** `http` for GraphQL requests |
| `runtime` | no | `scripts` and `assertions` |
| `settings` | no | Per-request switches (URL encoding, timeouts, redirects) |
| `docs` | no | Markdown describing the request |
| `vars` | no | Request-scoped variables (rare; usually live in env or folder) |

## `info`

```yaml
info:
  name: Get User              # required
  type: http                  # http | graphql | folder
  seq: 10                     # sort order within parent folder
  tags:                       # filterable via `bru run --tags`
    - users
    - smoke
  description: |              # optional, shown in UI
    Fetches a single user by id.
```

## `http`

```yaml
http:
  method: GET                 # GET POST PUT PATCH DELETE OPTIONS HEAD TRACE CONNECT
  url: "{{baseUrl}}/users/:id"
  params:
    - name: id
      value: "42"
      type: path              # path | query
    - name: include
      value: profile
      type: query
      disabled: false
  headers:
    - name: Accept
      value: application/json
    - name: X-Trace-Id
      value: "{{traceId}}"
      disabled: false
  body:                       # see body types below
    type: json
    data: |-
      {"hello": "world"}
  auth: inherit               # see auth section below
```

`disabled: true` keeps the entry in the file (and visible in diffs) but skips it at run time. Use this rather than deleting when an entry is "off for now".

### Body types

#### `json`
```yaml
body:
  type: json
  data: |-
    {
      "name": "{{newUserName}}",
      "tags": ["alpha", "beta"]
    }
```
`data` is a **string**, not a YAML map. Variables interpolate.

#### `text`
```yaml
body:
  type: text
  data: "Plain string body"
```

#### `xml`
```yaml
body:
  type: xml
  data: |-
    <user><name>Alice</name></user>
```

#### `form-urlencoded`
```yaml
body:
  type: form-urlencoded
  data:
    - name: grant_type
      value: client_credentials
    - name: scope
      value: read write
```

#### `multipart-form`
```yaml
body:
  type: multipart-form
  data:
    - name: file
      type: file
      value: ./fixtures/avatar.png
      contentType: image/png
    - name: caption
      type: text
      value: "Profile picture"
```
File paths are resolved relative to the request file.

#### `graphql`
```yaml
body:
  type: graphql
  query: |-
    query GetUser($id: ID!) {
      user(id: $id) { id name email }
    }
  variables: |-
    {"id": "42"}
```
Or use the dedicated `graphql:` top-level key — both work. Prefer the top-level key when the request is GraphQL through-and-through.

### `auth` (per request, folder, or collection)

```yaml
auth: inherit              # use parent's auth (most requests)
```
or one of:

```yaml
auth:
  type: none

auth:
  type: bearer
  token: "{{token}}"

auth:
  type: basic
  username: "{{user}}"
  password: "{{pass}}"

auth:
  type: apikey
  key: x-api-key
  value: "{{apiKey}}"
  placement: header        # header | query

auth:
  type: digest
  username: "{{user}}"
  password: "{{pass}}"

auth:
  type: oauth2
  grantType: client_credentials   # password | authorization_code | client_credentials
  accessTokenUrl: "{{authUrl}}/token"
  clientId: "{{clientId}}"
  clientSecret: "{{clientSecret}}"
  scope: "read write"

auth:
  type: awsv4
  accessKeyId: "{{awsKey}}"
  secretAccessKey: "{{awsSecret}}"
  sessionToken: "{{awsSession}}"
  service: execute-api
  region: us-east-1

auth:
  type: ntlm
  username: "{{user}}"
  password: "{{pass}}"
  domain: CORP

auth:
  type: wsse
  username: "{{user}}"
  password: "{{pass}}"
```

## `runtime`

### `scripts`
```yaml
runtime:
  scripts:
    - type: before-request
      code: |-
        req.setHeader("X-Idempotency-Key", crypto.randomUUID());
    - type: after-response
      code: |-
        if (res.status === 200) {
          bru.setVar("token", res.body.accessToken);
        }
    - type: tests
      code: |-
        test("status 200", () => expect(res.status).to.equal(200));
        test("has token",  () => expect(res.body.accessToken).to.be.a("string"));
```

Available globals inside scripts:
- `req` — outgoing request (`setHeader`, `setBody`, `getUrl`, etc.)
- `res` — response (`status`, `headers`, `body`, `responseTime`)
- `bru` — collection runtime (`getVar`, `setVar`, `getEnvVar`, `setEnvVar`, `cwd`)
- `expect`, `test`, `assert` — Chai-style assertions

### `assertions` (declarative — no JS needed)
```yaml
runtime:
  assertions:
    - expression: res.status
      operator: eq
      value: "200"
    - expression: res.body.id
      operator: isString
    - expression: res.responseTime
      operator: lt
      value: "500"
    - expression: res.headers.content-type
      operator: contains
      value: "application/json"
```

Operators: `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`, `notIn`, `contains`, `notContains`, `startsWith`, `endsWith`, `matches` (regex), `isString`, `isNumber`, `isBoolean`, `isArray`, `isObject`, `isNull`, `isUndefined`, `isDefined`, `isEmpty`, `isNotEmpty`, `isJson`.

Use `assertions` for simple shape checks (status, response time, types). Use `tests` scripts when assertions need logic (loops, computed values, conditional checks).

## `settings`

```yaml
settings:
  encodeUrl: true             # default true; set false if URL contains pre-encoded chars
  timeout: 0                  # ms; 0 = no limit
  followRedirects: true
  maxRedirects: 5
```

## `docs`

```yaml
docs: |-
  # Create User
  Returns 201 on success with a `{ id, name, email }` JSON body.
  Idempotent on email — duplicates return 409.
```
Pure Markdown. Shown in the Bruno UI's docs tab.

## `folder.yml` (per folder)

```yaml
info:
  name: Users
  type: folder
  seq: 20
  tags:
    - users

auth:
  type: bearer
  token: "{{userToken}}"      # override collection-level auth for this folder

vars:
  - name: defaultPageSize
    value: "25"

runtime:
  scripts:
    - type: before-request
      code: |-
        req.setHeader("X-Folder-Trace", "users");
```

## `opencollection.yml` (collection root)

```yaml
version: "1"
info:
  name: My API
  description: Customer-facing API
  version: "1.4.0"

auth:
  type: bearer
  token: "{{token}}"

vars:
  - name: apiVersion
    value: v1

runtime:
  scripts:
    - type: before-request
      code: |-
        req.setHeader("X-Client", "bruno-cli");
```

## Environment file (`environments/<name>.yml`)

```yaml
vars:
  - name: baseUrl
    value: https://api.example.com
  - name: token
    value: ""                 # leave blank, override with --env-var token=$TOKEN
    secret: true
  - name: traceId
    value: "{{$randomUUID}}"
```

## Built-in dynamic variables

Usable anywhere `{{…}}` interpolates:

- `{{$guid}}` / `{{$randomUUID}}`
- `{{$timestamp}}` (seconds), `{{$isoTimestamp}}`
- `{{$randomInt}}`, `{{$randomFirstName}}`, `{{$randomLastName}}`, `{{$randomEmail}}`
- `{{$processEnv.HOME}}` — read from process env at run time

## Inheritance order (for `auth: inherit` and vars)

Closest wins: **request → folder → collection → environment → CLI `--env-var`**. Each layer can fully override or partially extend the previous.
