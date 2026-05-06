# Bruno Auth Types — YAML Examples

Auth can be set at three scopes: **collection** (`opencollection.yml`), **folder** (`folder.yml`), or **request** (`*.yml`). Requests with `auth: inherit` walk up to the nearest defined `auth`. Set auth as high as it applies — putting bearer at the collection level means individual requests stay clean.

## Why this matters

Picking the right scope is what keeps the collection maintainable:

- Same token everywhere → set on collection. Every request is one line: `auth: inherit`.
- One folder uses a different identity (admin endpoints, third-party callbacks) → override at folder.
- One specific request needs a one-off (the login endpoint itself, an OAuth refresh) → override at request, often with `type: none`.

## `none`
```yaml
auth:
  type: none
```
Used on the very first request in an auth flow (e.g. `POST /login`) so the parent's bearer doesn't leak into a request that should reject it.

## `bearer` — the common case
```yaml
auth:
  type: bearer
  token: "{{token}}"
```
Pair with an env var named `token`. The cleanest pattern is to leave the env value blank and pass it at runtime: `bru run --env ci --env-var token=$CI_TOKEN`.

## `basic`
```yaml
auth:
  type: basic
  username: "{{basicUser}}"
  password: "{{basicPass}}"
```
Bruno builds the `Authorization: Basic <base64>` header for you. Don't compute it manually.

## `apikey`
```yaml
auth:
  type: apikey
  key: x-api-key            # header or query param name
  value: "{{apiKey}}"
  placement: header         # header | query
```

## `digest`
```yaml
auth:
  type: digest
  username: "{{user}}"
  password: "{{pass}}"
```
Bruno handles the challenge/response handshake. Two round-trips per request.

## `oauth2` — client credentials (the simplest grant)
```yaml
auth:
  type: oauth2
  grantType: client_credentials
  accessTokenUrl: "{{authUrl}}/oauth/token"
  clientId: "{{clientId}}"
  clientSecret: "{{clientSecret}}"
  scope: "read write"
```
Bruno fetches and caches the token automatically.

## `oauth2` — password grant
```yaml
auth:
  type: oauth2
  grantType: password
  accessTokenUrl: "{{authUrl}}/oauth/token"
  username: "{{user}}"
  password: "{{pass}}"
  clientId: "{{clientId}}"
  clientSecret: "{{clientSecret}}"
  scope: "openid profile"
```

## `oauth2` — authorization code (browser-based, dev-only)
```yaml
auth:
  type: oauth2
  grantType: authorization_code
  authorizationUrl: "{{authUrl}}/authorize"
  accessTokenUrl: "{{authUrl}}/token"
  callbackUrl: http://localhost:3000/callback
  clientId: "{{clientId}}"
  clientSecret: "{{clientSecret}}"
  scope: "openid email"
  pkce: true
```
This grant type opens a browser, so it works in the Bruno desktop app but **not** in `bru run` (CI). For CI, use client_credentials or pre-fetch a token and inject via `--env-var`.

## `awsv4` — AWS SigV4
```yaml
auth:
  type: awsv4
  accessKeyId: "{{awsKey}}"
  secretAccessKey: "{{awsSecret}}"
  sessionToken: "{{awsSession}}"     # optional, for STS
  service: execute-api               # or s3, lambda, etc.
  region: us-east-1
  profileName: ""                    # optional, for ~/.aws/credentials profile
```

## `ntlm`
```yaml
auth:
  type: ntlm
  username: "{{user}}"
  password: "{{pass}}"
  domain: CORP
  workstation: ""                    # optional
```

## `wsse` — WS-Security
```yaml
auth:
  type: wsse
  username: "{{user}}"
  password: "{{pass}}"
```

## Pattern: log in once, reuse the token

For E2E suites where you need to log in then use that token everywhere:

`scenarios/setup/01-login.yml`:
```yaml
info:
  name: Login
  type: http
  seq: 1
http:
  method: POST
  url: "{{baseUrl}}/auth/login"
  body:
    type: json
    data: |-
      {"email": "{{testEmail}}", "password": "{{testPassword}}"}
  auth:
    type: none                        # don't send the (yet-empty) bearer
runtime:
  scripts:
    - type: after-response
      code: |-
        bru.setVar("token", res.body.accessToken);
  assertions:
    - expression: res.status
      operator: eq
      value: "200"
```

Every subsequent request stays `auth: inherit` and reads the bearer set at the collection level — which now resolves `{{token}}` to whatever the login wrote.

## Pattern: rotate tokens between scenarios

If two scenarios need different identities (admin vs. customer), don't try to multiplex one variable. Use two:
- `{{adminToken}}`, `{{customerToken}}`
- Folder-level auth in each scenario folder pointing at the right variable.

## Anti-patterns

- **Bearer literal in YAML committed to git.** Always `{{token}}` + env var.
- **Building `Authorization: Basic …` header manually.** Use `auth: { type: basic }` — Bruno does the base64.
- **OAuth2 authorization_code in CI.** It needs a browser; CI doesn't have one. Pre-fetch a token instead.
- **Setting auth on every request.** If you're typing `auth:` more than once in a folder, lift it to `folder.yml`.
