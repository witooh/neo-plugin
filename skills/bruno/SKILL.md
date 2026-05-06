---
name: bruno
description: Author and maintain Bruno API collections in OpenCollection YAML format (opencollection.yml + per-request .yml files). Use this skill whenever the user mentions Bruno, .bru files, OpenCollection YAML, API collections, or asks to scaffold/edit/convert API requests, environments, folders, auth, scripts, or assertions for Bruno. Trigger even when the user only says "API collection", "REST request file", "Postman → Bruno", or pastes a curl/OpenAPI/Postman export and wants it organized into a Bruno collection. Default to YAML format (Bruno 3.0+) unless the existing collection clearly uses .bru.
---

# Bruno OpenCollection YAML

Bruno is a Git-friendly API client. Collections are plain folders of YAML files that humans diff and machines run. This skill helps you:

1. Scaffold a new collection (`opencollection.yml` + folders + requests).
2. Add or edit requests, environments, auth, and scripts inside an existing collection.
3. Convert curl, Postman, OpenAPI, or `.bru` snippets into OpenCollection YAML.

The default request body and auth in this skill are **JSON + Bearer token** because that covers the majority of REST APIs. Other shapes (multipart, OAuth2, GraphQL, AWSv4) live in `references/`.

## Before you write anything

Resolve these three questions first — they shape every file you produce:

1. **Where does the collection live?** Look for an existing `opencollection.yml` upward from the working directory. If found, treat it as the root and add into it. If not, ask the user where to create one (default: a new folder in the repo root named after the API).
2. **Format?** If existing files are `.bru`, ask before mixing in YAML — the two coexist but mixing inside one folder is confusing. For brand-new collections, default to YAML.
3. **What is the auth model?** Bearer in a `{{token}}` env var is the default. If the user shows a curl with `Authorization: Bearer …`, lift the literal into an environment variable rather than hardcoding it. Hardcoded secrets in committed YAML is the most common mistake — flag it if you see it.

## Anatomy of a collection

```
my-api/
├── opencollection.yml          # root: name, version, collection-level auth/vars
├── environments/
│   ├── local.yml
│   └── production.yml
├── auth/
│   ├── folder.yml              # folder metadata (seq, name, optional auth/vars)
│   ├── login.yml               # individual request
│   └── refresh.yml
└── users/
    ├── folder.yml
    ├── list-users.yml
    └── create-user.yml
```

Folders nest freely. Each folder *can* carry its own `folder.yml` to set auth/vars that requests inside inherit via `auth: inherit`.

## Request file template (JSON + Bearer — the common case)

```yaml
info:
  name: Create User
  type: http
  seq: 2
  tags:
    - users

http:
  method: POST
  url: "{{baseUrl}}/users"
  headers:
    - name: Content-Type
      value: application/json
  body:
    type: json
    data: |-
      {
        "name": "{{newUserName}}",
        "email": "{{newUserEmail}}"
      }
  auth: inherit          # use collection-level bearer

runtime:
  scripts:
    - type: tests
      code: |-
        test("status is 201", function () {
          expect(res.status).to.equal(201);
        });
        test("returns id", function () {
          expect(res.body.id).to.be.a("string");
        });
  assertions:
    - expression: res.status
      operator: eq
      value: "201"
    - expression: res.body.email
      operator: eq
      value: "{{newUserEmail}}"

settings:
  encodeUrl: true
```

Notes that catch people out:

- `body.data` is a **string** (use `|-` for multi-line JSON). It is not a YAML map.
- Variables interpolate as `{{name}}` — they work inside strings, including inside `body.data`.
- `auth: inherit` reads from the nearest enclosing `folder.yml` then `opencollection.yml`. Only override per request when that request truly needs different credentials.
- `seq` controls run order inside a folder. Reserve gaps (10, 20, 30…) so you can insert later without renumbering everything.

## Environments

`environments/local.yml`:

```yaml
vars:
  - name: baseUrl
    value: http://localhost:3000
  - name: token
    value: dev-token-abc123
    secret: true            # masked in logs/UI
  - name: newUserName
    value: Test User
  - name: newUserEmail
    value: test+{{$randomInt}}@example.com
```

Mark anything you wouldn't paste in Slack as `secret: true`. For real credentials, prefer leaving `value: ""` so the user can supply them at run time rather than committing them to git.

## Root `opencollection.yml`

```yaml
version: "1"
info:
  name: My API
  description: Internal customer API
auth:
  type: bearer
  token: "{{token}}"
vars:
  - name: apiVersion
    value: v1
```

Putting the bearer at the root means every request can stay `auth: inherit` and you swap tokens by switching environments.

## Scripts: pre-request, after-response, tests

Three script types run at well-defined moments:

- **`before-request`** — mutate `req` (set headers, sign payloads, log).
- **`after-response`** — read `res`, stash values into vars (`bru.setVar`) for later requests.
- **`tests`** — assertions using a Mocha-like `test(name, fn)` + `expect(...)`.

Use `after-response` to chain a flow: a login request stashes `token` → subsequent requests pick it up via `{{token}}`.

For complex sequences, prefer many small `tests` blocks with descriptive names over one giant block — each name shows up as its own pass/fail line, which is what makes test failures readable.

## Converting from other formats

If the user pastes a curl, Postman export, or OpenAPI snippet, infer the YAML directly — don't ask follow-up questions you can answer by reading. Specifically:

- **curl** → method, URL, headers, body map straightforwardly. Lift any `Authorization: Bearer` into env `{{token}}`.
- **Postman v2.1 collection** → each `item` becomes one request file; folders become folders; `event.script` blocks become `runtime.scripts` (`prerequest` → `before-request`, `test` → `tests`).
- **OpenAPI** → one request file per operation, grouped by tag into folders. Use the operation's `summary` as `info.name`. Pull example bodies from `requestBody.content.application/json.example`.

See `references/migration.md` for line-by-line mappings and gotchas (Postman's `pm.*` API → Bruno's `bru.*` / `req` / `res`).

## Reference files

Read these on demand, not upfront:

- `references/structure.md` — full schema: every key, every body type, every operator.
- `references/auth.md` — all auth types (basic, bearer, apikey, digest, oauth2, awsv4, ntlm, wsse) with YAML examples.
- `references/migration.md` — curl / Postman / OpenAPI → Bruno YAML, with the common pitfalls.

## Things to avoid

- **Hardcoded secrets in committed YAML.** Use env vars + `secret: true`, or leave the value blank.
- **Mixing `.bru` and `.yml` inside one folder** without asking. They coexist at the collection level, but inside a single folder it makes diffs noisy.
- **One giant `tests` block.** Multiple small `test("…", …)` blocks give you per-assertion pass/fail — the entire reason you wrote the test in the first place.
- **Inventing fields.** The schema is small; if you're tempted to add a field that "feels right," check `references/structure.md` first. The actual key is probably named something close but different.
