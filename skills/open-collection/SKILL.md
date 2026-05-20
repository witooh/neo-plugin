---
name: open-collection
description: >
  Generate and validate Bruno OpenCollection YAML (https://www.opencollection.com/)
  from Go source code. Scans handler/router files to produce a runnable collection —
  opencollection.yml + environments/ + per-group folder.yml + one .yml file per request,
  grouped by handler domain. Each request file embeds a `docs:` markdown section with the
  same field/error tables as api-doc-gen. Use this skill whenever the user wants to
  generate, update, or validate an OpenCollection / Bruno collection from code, or says
  things like "gen open collection", "สร้าง open collection", "อัปเดต bruno collection",
  "สร้าง bruno จาก code", "scaffold opencollection.yml from handlers", "เช็ค bruno
  ตรงกับ code ไหม", or "open-collection". Also trigger when neo-team delegates collection
  generation tasks. This is the *code-to-collection generator*; for hand-authoring or
  curl/Postman conversion use the `bruno` skill instead.
compatibility:
  environment: claude-code
  tools:
    - Read
    - Glob
    - Grep
    - Bash
    - Edit
    - Write
---

# Open Collection Generator

Generate or validate a Bruno OpenCollection YAML workspace (v1.0.0) by scanning Go source. The output is a fully runnable collection — one `.yml` file per request, grouped by handler domain — so each endpoint is easy to find, run, diff, and maintain independently.

This skill is the **code-to-collection** counterpart of [`../api-doc-gen`](../api-doc-gen/SKILL.md). They share the same scanning logic and the same field/error documentation rules; the difference is the output:

| Skill | Output |
|-------|--------|
| `api-doc-gen` | `docs/api/<group>/<endpoint>.md` — pure Markdown docs |
| `open-collection` | `<collection>/<group>/<request>.yml` — runnable Bruno requests with `docs:` markdown embedded |

If the user wants to **author by hand**, convert curl/Postman, or edit individual requests interactively, use the `bruno` skill instead. This skill is for **bulk generating from source code**.

To **publish the generated docs to Confluence**, hand the collection root off to the [`confluence-api-doc`](../confluence-api-doc/SKILL.md) skill — it auto-detects an `opencollection.yml` at the source path and syncs each request's `docs:` block as one Confluence page (no extra extraction step or duplicate markdown files needed).

## Output Structure

CoreTeam2 full-folder style (one `folder.yml` per group, shared headers + `auth: inherit`):

```
<collection-root>/
├── opencollection.yml              ← collection root config
├── environments/
│   ├── LOCAL.yml                   ← env vars for local dev
│   └── SIT.yml                     ← env vars for SIT (one per known environment)
├── <group>/
│   ├── folder.yml                  ← group metadata + inherited headers/auth
│   ├── <endpoint>.yml              ← one request per file
│   └── ...
└── ...
```

- **Grouping:** each subdirectory under the handler base directory = one folder/group
- **File naming:** handler function name → kebab-case (`AcceptConsent` → `accept-consent.yml`)
- **Path params in URL:** Bruno uses `:param` style in URL strings and a `params` block with `type: path` to document them
- **`seq`:** request files are numbered 10, 20, 30… inside each folder so the user can insert later without renumbering everything

## Modes

| Mode | When to use | What it does |
|------|-------------|--------------|
| **Generate** | No `opencollection.yml` at the target location | Create the full collection from scratch |
| **Update** | `opencollection.yml` exists, code has changed | Diff against existing files → add/update/remove individual request files + refresh `folder.yml` and `index` |
| **Validate** | User wants to check consistency | Compare every `.yml` request in the collection against code; report mismatches without modifying |

Detect the mode automatically:
1. If no `opencollection.yml` is found at the target → **Generate**
2. If user says "validate", "check", "เช็ค", "ตรงกับ code ไหม" → **Validate**
3. Otherwise → **Update**

The user can override the mode explicitly.

## Workflow

### Step 0: Locate the Collection Root and Read Project Context

**Locate the collection root** (in order):
1. If user gave an explicit path, use it.
2. Walk **upward** from the working directory looking for `opencollection.yml`. If found, that file's directory is the collection root.
3. Otherwise look for an existing folder named `bruno/`, `bruno-collection/`, or `open-collection/` at the repo root.
4. If still not found, propose a new root at `<repo-root>/bruno/<service-name>/` and confirm with the user before writing.

Then read `CLAUDE.md` (or `AGENTS.md`, `CONTRIBUTING.md`) to understand:
- Service name (becomes `info.name` in `opencollection.yml`)
- Framework used (Fiber, Echo, Chi, Gin)
- API versioning pattern (`/api/v1/`)
- Known environments (`local`, `sit`, `uat`, `prod`) — used to generate environment files

If no convention file exists, infer from the code.

### Step 1: Discover Routes

Reuse the existing scan patterns — open [`../api-doc-gen/references/go-scan-patterns.md`](../api-doc-gen/references/go-scan-patterns.md) and follow it as-is. You need to find:

- All registered routes (method + path)
- The handler function each route maps to
- Route groups and prefixes
- Middleware applied (auth, validation) — used to decide `auth: inherit` vs explicit auth per folder

Where to look (in order):
1. Router setup file — often `cmd/api/main.go`, `internal/router.go`, `routes.go`
2. Route group files — `internal/<domain>/routes.go`
3. Handler files — `internal/<domain>/handler/*.go`

### Step 1b: Discover Handler Groups

Same logic as `api-doc-gen` § Step 1b. Read [`../api-doc-gen/references/go-scan-patterns.md`](../api-doc-gen/references/go-scan-patterns.md) § Handler Directory Scanning. Build the group map:

```
{ group: "consent", endpoints: [
    { function: "AcceptConsent", file: "accept-consent.yml", method: "POST", path: "/api/v1/consents" },
    ...
] }
```

If the handler directory is flat (no subdirectories), fall back to grouping by route prefix.

### Step 2: Extract Endpoint Details

For each route, trace handler → usecase → repository and extract the same details `api-doc-gen` extracts:

1. **Request shape** — path params, query params, request body struct
2. **Response shape** — success response (struct + status code), plus any response wrapper
3. **Business logic steps** — using the same Priority 1 (header comments) / Priority 2 (code-derived) rules
4. **Error responses** — usecase typed errors + domain service typed errors + handler-level errors
5. **Auth** — middleware on the route group → `Bearer token`, `API Key`, or `None`

For every detail above use the **same rules** as `api-doc-gen`:
- Field/error extraction patterns: [`../api-doc-gen/references/go-scan-patterns.md`](../api-doc-gen/references/go-scan-patterns.md)
- M/O classification, field descriptions, example values, error enumeration: [`../api-doc-gen/references/api-doc-template.md`](../api-doc-gen/references/api-doc-template.md)
- Deterministic text rules and step counting: see `api-doc-gen/SKILL.md` § Step 2

The output of this step is the same in-memory representation as `api-doc-gen`. What changes is **how it gets written**, in Step 3.

### Step 3: Generate, Update, or Validate

Open [`references/yaml-reference.md`](references/yaml-reference.md) for the exact OpenCollection YAML schema (frontmatter, `info`, `http`, `runtime`, `settings`, `examples`, `docs`).

Open [`references/request-template.md`](references/request-template.md) for the per-file templates: `opencollection.yml`, `environments/*.yml`, `folder.yml`, and the request `.yml` (including the embedded `docs:` markdown structure, which mirrors the api-doc-gen per-endpoint template).

#### Generate Mode

Create the collection from scratch:

1. **`opencollection.yml`** at the collection root — name, version, no top-level auth (auth lives on folders so different groups can carry different middleware).

2. **`environments/<ENV>.yml`** — one file per environment found in CLAUDE.md / config. Include placeholder variables: `baseUrl`, plus one variable per `{{var}}` reference seen in route paths or middleware (e.g., `auth_token`, `device_id`). Mark secrets as `secret: true` and leave their values blank.

3. **`<group>/folder.yml`** — full CoreTeam2 style:
   ```yaml
   info:
     name: <Group Display Name>
     type: folder
     seq: <N>
   request:
     headers:
       - name: Content-Type
         value: application/json
       # + any shared headers from middleware
     auth: <inherit | bearer | apikey | none>
   ```
   - `seq` is assigned in the order groups appear in the route registration file (10, 20, 30…).
   - `auth` reflects the actual middleware on the group: bearer for JWT middleware, apikey for API key middleware, `none` for unprotected, `inherit` only when the parent already sets the same auth.

4. **`<group>/<endpoint>.yml`** — one per route. Section order:
   ```
   info → http → settings → docs
   ```
   No `runtime` section. No tests. No assertions. No scripts. The user said no test code — do not add any.

   The `docs:` value is a block scalar (`|-`) containing markdown formatted like the api-doc-gen per-endpoint template: H1 name, one-line description, Method/Path/Auth bullets, Path/Query/Body/Response tables, Business Logic numbered list, Error Responses table. See [`references/request-template.md`](references/request-template.md) for the exact structure.

#### Update Mode

1. Walk the existing collection root and build a map of existing request files (group → list of files).
2. Scan code and build the current endpoint map (same as Generate).
3. Diff and apply:
   - **New endpoint** → create new `<group>/<endpoint>.yml`. Assign the next free `seq` (10, 20, 30…). If the group folder doesn't exist, create `folder.yml` too.
   - **Removed endpoint** → delete the orphaned `.yml`. If the group folder ends up empty, remove the folder and its `folder.yml`.
   - **Changed endpoint** — update only the request file. Touch the minimum set of fields (e.g., method, url, body, headers, docs); do not rewrite the file unless every section has changed.
   - **Moved group** — if a handler moved between groups, move the request file. Preserve its `seq` if the target group has the slot free; otherwise assign the next free `seq`.
   - **Environment changes** — never overwrite existing environment values (they often hold secrets the user typed by hand). Only add missing variables; leave existing values untouched.
4. Preserve any **user-added** runtime/scripts/assertions blocks if they were added by hand. This skill never writes those, but a user may have added them later — keep them on update.
5. Preserve any user-added `examples:` blocks.

#### Validate Mode

Compare every `.yml` in the collection against discovered routes **at the same depth as Step 2** — open the actual struct files and ALL usecase methods, not just check surface presence.

Run **every applicable item** in [`../api-doc-gen/references/api-doc-template.md`](../api-doc-gen/references/api-doc-template.md) § Verification Checklist (those that apply to fields/errors/business logic). On top of that, run the checks specific to OpenCollection YAML:

- [ ] Every route in code has a request `.yml` and vice versa (no missing or orphan files)
- [ ] Each request file has `info.name`, `info.type: http`, and `info.seq`
- [ ] URL is quoted (`url: "{{baseUrl}}/path"`) when it contains template variables
- [ ] Path parameters appear both in the URL string (`:id` style) and in `http.params` with `type: path`
- [ ] Body uses `|-` block scalar when JSON
- [ ] `settings.encodeUrl: true` is present
- [ ] `auth: inherit` is used unless the request truly needs different auth than the folder
- [ ] `seq` values are unique inside a folder
- [ ] No hardcoded secrets — PIN/token-like values must use `{{process.env.*}}` via `runtime.variables` (handled by the user, not by this skill, but flag any literal-looking secrets you see)
- [ ] `docs:` block exists and contains the standard sections (Method/Path/Auth, params, request body, response, business logic, errors)

Produce a report identical in spirit to `api-doc-gen` validate output, scoped to YAML files:

```
## Open Collection Validation Report

**Status:** [In Sync / Out of Sync]
**Collection root:** <path>
**Structure:** [N] groups, [M] request files

### Missing Files (routes in code but no request file)
- POST /api/v1/consents → expected at consent/accept-consent.yml
  handler: AcceptConsent (internal/delivery/http/handler/consent/accept_consent.go:12)

### Orphan Files (request files with no matching route)
- consent/old-revoke.yml → no matching route found

### Field Mismatches (per file)
- consent/get-consent.yml
  - Body: struct has 8 fields, request body has 6 — MISSING: revoked_at, revoked_by
  - URL path uses :consent_id but params block declares :id

### Error/Docs Mismatches (per file)
- consent/accept-consent.yml
  - docs.Error Responses table: 3 rows; usecase has 5 typed error returns — MISSING ErrPurposeExpired (422)

### Schema Mismatches
- consent/folder.yml is missing required `info.type: folder`
- channel/create-channel.yml uses unquoted URL with template variable

### Summary
| Category | Count |
|----------|-------|
| Groups in code | X |
| Folders in collection | Y |
| Routes in code | X |
| Request files | Y |
| Missing files | Z |
| Orphan files | W |
| Field mismatches | N |
| Error response mismatches | E |
| Schema issues | S |
```

### Step 4: Verify (mandatory after every Generate/Update)

Every time you create or modify files, run a verification pass before reporting completion. Skipping this step ships silent errors.

For each request file created/changed:
1. Re-open the source structs and re-check the body / response field count vs the doc tables.
2. Re-open ALL usecase methods and ALL domain service methods called by the usecase; re-check the error rows in the `docs:` Error Responses table.
3. Confirm M/O classification per the table in [`../api-doc-gen/references/api-doc-template.md`](../api-doc-gen/references/api-doc-template.md) § M/O Classification — `bool` without `binding:"required"` → O, pointer → O, `binding:"required"` → M.
4. Confirm the URL string contains the right path parameters and that they appear in the `http.params` block with `type: path`.
5. Confirm `seq` values are unique inside each folder.

**Fix or report:**
- Mismatches found → fix the file, then re-run the checklist on the fixed file.
- Maximum 2 fix-and-recheck cycles. If issues remain after 2 rounds, report them as warnings in the final output.

## Conventions and Gotchas

- **`body.data` is a string, not a map.** Use `|-` block scalar so JSON formatting is preserved.
- **Quote URLs that contain `{{vars}}`.** YAML treats unquoted `{` as a flow-style mapping start.
- **Path parameters appear twice.** Once in the URL string (`:id` style), and once in `params` with `type: path`. Both are needed — Bruno reads the URL for routing and the `params` block for documentation/runner-input.
- **Headers shared across a folder belong in `folder.yml`, not duplicated in every request.** The skill must dedup: if every request in a folder carries `Accept-Language: TH`, lift it into `folder.yml` and use `auth: inherit` style header inheritance.
- **Never write secrets to YAML.** If middleware or routes hint at sensitive values (PIN, biometrics, national ID), emit a variable reference like `"{{process.env.NATIONAL_ID}}"` and add the variable to environment files with an empty value.
- **No tests, no assertions, no scripts.** The user explicitly opted out. Do not generate `runtime.scripts` or `runtime.assertions` even when the source code makes it obvious what the tests should say. Preserve any user-added blocks on Update.
- **Bruno's `seq` is per-folder, not global.** Two folders can both have `seq: 10` for their first request — that's fine. Don't try to make `seq` globally unique.
- **PascalCase → kebab-case for filenames.** `GetConsentsByCitizen` → `get-consents-by-citizen.yml`. Strip trailing `Handler` suffix if present (`CreateUserHandler` → `create-user.yml`).
- **Endpoint display name (`info.name`) uses space-separated PascalCase.** `AcceptConsent` → `Accept Consent`. Same rule as the `# <Name>` heading in api-doc-gen.

## Output

After completion, report:

```
## Open Collection Generator

**Mode:** [Generate / Update / Validate]
**Collection root:** <path>
**Structure:**
  - opencollection.yml
  - environments/ (LOCAL.yml, SIT.yml)
  - consent/ (folder.yml + 5 request files)
  - channel/ (folder.yml + 6 request files)
  - purpose/ (folder.yml + 12 request files)

**Changes:**
- Created: consent/accept-consent.yml, consent/get-consent.yml, ...
- Updated: channel/create-channel.yml (added query param `category`)
- Removed: legacy/old-endpoint.yml (route removed from code)

**Verification:** [✅ Passed — collection matches code / ⚠️ Passed with warnings / ❌ Issues remain]
- File coverage: X routes in code, Y request files — Match: ✅/❌
- Field accuracy: [X/Y request files — body/response struct field count matches docs table]
- Error response accuracy: [X/Y request files — usecase error count matches docs error rows]
- Schema validity: [X/Y files — all required keys present, URLs quoted, path params declared]
- Fix cycles used: [0/1/2]

**Warnings:** [any remaining issues — missing structs, unresolvable types, hardcoded-looking secrets, etc.]
```
