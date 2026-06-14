---
name: openapi-doc
description: >
  Generate an OpenAPI 3.2 spec from Go source as a **split-YAML** document in
  `docs/openapi/` — a root `openapi.yaml` plus one Path Item file per URL path and one
  schema file per type, wired with `$ref` — or update/validate an existing spec against
  the current code. Business-logic steps live in `x-business-logic` and per-sentinel
  errors in `x-error-catalog`. Built-in **three-layer verify** (deterministic script +
  independent fresh-eyes agent + completeness sweep). Trigger on: "gen openapi",
  "generate openapi spec", "openapi from go", "swagger spec from code", "สร้าง openapi",
  "สร้าง openapi spec", "ทำ swagger spec", "อัปเดต openapi", "เช็ค openapi ตรงกับ code",
  "openapi 3.2 from code", "validate openapi against code". Also trigger when neo
  delegates OpenAPI spec generation. NOTE: this skill produces the **OpenAPI spec
  only** — the **Markdown** docs are the `api-doc` skill; a runnable Bruno OpenCollection
  is the `open-collection` skill; publishing to Confluence is `confluence-api-doc`. It
  is not a curl/Postman converter or an interactive editor.
compatibility:
  environment: claude-code
  tools:
    - Read
    - Glob
    - Grep
    - Bash
    - Edit
    - Write
    - Agent
    - AskUserQuestion
---

# OpenAPI Doc

Generate an **OpenAPI 3.2.0** spec from source as a **split-YAML** document under `docs/openapi/` — a root `openapi.yaml`, one Path Item file per URL path, and one schema file per Go type, wired with `$ref`. This is a **sibling generator** to `api-doc` (which emits Markdown): both read the same Go source, **Go is the single source of truth**, and each verifies its own output against Go independently — so the spec and the Markdown stay mutually consistent without a cross-check. Each spec is verified on **evidence (a deterministic script) + an independent fresh-eyes pass + a completeness sweep**, never on the writing agent's confidence.

`ASSET_DIR` = `<skill base dir>/assets`, `SKILL_DIR` = `<skill base dir>` (the skill-load message gives the "Base directory for this skill"). Currently optimized for Go (Fiber, Echo, Chi, Gin).

## Output structure

```
docs/openapi/
├── openapi.yaml                    ← root: openapi/info/servers/tags/paths-$refs/components
├── paths/
│   └── <group>/<path>.yaml         ← one Path Item Object per URL path (all its methods)
└── components/
    ├── schemas/<GoTypeName>.yaml    ← one schema per Go type
    └── responses/<CommonError>.yaml ← shared error responses (401/403/404/400/500)
```

- **Grouping** — each subdirectory under the handler base directory = one group = a `tags` entry + a `paths/<group>/` folder.
- **File granularity** — one Path Item file per **distinct URL path** (OpenAPI keys a path to one object, so all methods on a path share the file). Usually one endpoint per file; a path with two methods (`GET`+`DELETE`) shares one.
- **File naming** — kebab of the path within the group, params `by-<param>` (`/channels/{id}` → `channels-by-id.yaml`).
- **Path params** — native `{param}` form.
- **Root `openapi.yaml`** `$ref`s every path file and declares shared securitySchemes + common error responses.

## Mode

Auto-detect (user can override): no `docs/openapi/openapi.yaml` → **Generate**; request says "validate/check/เช็ค/ตรงกับ code ไหม" → **Validate**; otherwise → **Update**.

---

## Step 1 · Locate `docs/openapi/` + project context
- **Doc root** — default `docs/openapi/` at the repo root; in a monorepo scope it to the chosen service (e.g. `services/<name>/docs/openapi/`).
- Read `CLAUDE.md` / `AGENTS.md` / `README` for service name, framework, API version, and the `/api/v1/` versioning pattern (→ `info.version` + `servers[].url`).
- **Not a Go project** (no `go.mod` and no `references/<lang>-scan-patterns.md`) → **STOP**: Go only; do not guess patterns.
- **Monorepo** (multiple `go.mod`) → ask which service, then scope the scan + `docs/openapi/` to that one service.

## Step 2 · Discover routes & groups
Read [`references/go-scan-patterns.md`](references/go-scan-patterns.md) (route registration patterns + § Handler Directory Scanning). Find every route (method, path, handler), its group, and middleware (auth). A route matched by a `docs/openapi/.docignore` glob or carrying a `// apidoc:ignore` comment above its registration is intentionally undocumented (internal/debug/health) — skip it in Generate/Update, treat it as expected-absent in Validate. (`speccheck.py` does not read `.docignore`, so an intentionally-skipped route surfaces as a coverage ERROR — confirm it and skip it as a known false positive per the Layer-1 loop below.)

## Step 3 · Extract per endpoint
For each route, trace handler → usecase → repository and extract: request/response shape (path/query/body, success status — read the actual `c.JSON(NNN, …)`, don't guess), business-logic steps, and error responses. Apply the **single sources**, do not restate them:
- Field extraction, error tracing, **step counting** (Priority 1 = `### Logical` / `Step N:` header comments verbatim; Priority 2 = code-derived: 1 step per repo/service/external call + per sentinel-returning `if`/`switch`; a repo call + its nil-check = 2 steps; not a step: error propagation, stdlib, struct construction, entity mutation without I/O, logging) → [`references/go-scan-patterns.md`](references/go-scan-patterns.md).
- M/O → `required[]`, type mapping, nullability (union types), `x-business-logic`, `x-error-catalog`, example values, `$ref` wiring → [`references/openapi-doc-template.md`](references/openapi-doc-template.md).

## Step 4 · Generate / Update / Validate
Write using [`references/openapi-doc-template.md`](references/openapi-doc-template.md) (Root + Path Item + Schema Component templates):
- **`openapi.yaml`** — `openapi: 3.2.0`, `info` (title/version/overview), `servers`, `tags` (one per group), `paths` as a `$ref` map, and `components` (securitySchemes + shared error responses).
- **`paths/<group>/<path>.yaml`** — one Path Item: each method's `summary`/`description`/`operationId`/`security`/`x-business-logic`/`parameters`/`requestBody`/`responses`; schemas referenced via `$ref`; the runnable JSON body kept verbatim in `examples.default.value`.
- **`components/schemas/<Type>.yaml`** — one schema per Go type; `required[]` from M/O; properties in struct order; embedded structs via `allOf`; nested types via `$ref`; per-sentinel errors via `x-error-catalog`.
- **Byte-stable YAML** — fixed key order + 2-space block style (template § Byte-stable YAML rules) so Update diffs stay clean.
- **Update** — diff against existing files; touch the minimum; create/update/remove individual files; move a path file if its handler changed group; regenerate the root `paths:`/`tags:`. Preserve any manually-added `description` prose that isn't auto-generated.
- **Validate** — no writes; run the verify layers below as a pure check and produce a report.

### verify-L1 · Script tripwire (always)
```
python3 <ASSET_DIR>/speccheck.py docs/openapi/ --src <project-root>
```
`<project-root>` = the repo root where `go.mod` lives (usually `.`). It mechanically checks root/operation well-formedness, `$ref` resolution, route↔path-file coverage, per-schema property count + `required[]` vs Go structs, status/security sanity, and — **if a real OpenAPI validator (`redocly`/`spectral`/`openapi-spec-validator`) is on PATH** — runs it for structural validation. **Tripwire, not ground truth** — a flag means "inspect this".
- **exit 0** → go to L1.5.
- **exit 1** → for each ERROR, open the actual struct/route/spec file: real mismatch → fix → re-run; genuine false positive (e.g. a `.docignore`'d route, or an `openapi-spec-validator` complaint about split `$ref`s) → skip + record under Warnings (never blindly "fix"). **Loop until exit 0, OR ~3 rounds with no progress → STOP and escalate** with the remaining ERRORs. Never fake a green run.
- Collect every **`NOTE`** line (each ends `needs fresh-eyes`) — they feed L2; NOTEs don't fail the run.

### verify-L1.5 · Offer fresh-eyes (default yes)
Ask once via `AskUserQuestion`: *"Run an independent fresh-eyes verify of the generated spec? (default: yes)"* — **no** → skip L2 (mark "skipped by user"); **yes** → L2.

### verify-L2 · Fresh-eyes verifier (independent agent)
Dispatch a verifier that did **not** write the spec — it re-reads the Go source itself and checks only the judgment-level accuracy the script cannot (error tracing + `x-error-catalog`, `x-business-logic` step counting, `required[]` edge cases, custom-type enums, `description`/`examples`/nullability, success status, security mapping, example shape, `$ref` semantics):
```
Agent(subagent_type: "general-purpose", description: "verify openapi spec", prompt: """
# Role: OpenAPI Doc Verifier
Read first: <SKILL_DIR>/references/openapi-doc-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the spec just generated. Check ONLY judgment-level accuracy
(not the script's mechanical checks). Read the Go source yourself.

## Spec under review
docs/openapi/openapi.yaml + docs/openapi/paths/<group>/<file>.yaml + the
docs/openapi/components/schemas/*.yaml they $ref (list the files just created/updated)

## speccheck NOTEs to focus on
<paste every NOTE line from L1>

## Project conventions
CLAUDE.md (the relevant section)

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
""")
```
`SKILL_DIR` is mandatory — without it the verifier cannot read its role file and fails silently. The verifier is read-only → **you** fix the files → re-run `speccheck.py` to confirm nothing regressed. Do not auto-redispatch; if findings are deep, offer a second fresh-eyes round (default yes), then escalate.

### verify-L3 · Completeness sweep (omission critic)
L1/L2 inspect what is *present*; L3 catches what is **missing entirely** — a whole path that silently never got a file, which L1's best-effort route regex can miss. Re-derive the **full endpoint inventory straight from the router-setup file yourself** (read it, don't lean on the script), then confirm:
- every registered route (minus `.docignore` / `// apidoc:ignore`) has a `paths/<group>/` operation,
- every path file maps to a real route (no orphan), and is `$ref`'d from the root `paths:`,
- the `$ref` graph has no dangling or orphan schema (every `$ref` resolves; every `components/schemas` file is referenced),
- `tags` covers every group.
Report any whole path/group/schema the pipeline silently dropped; fix → re-run L1 to confirm.

### Output
```
## OpenAPI Doc — <Generate / Update / Validate>
**Doc root:** docs/openapi/   **Structure:** openapi.yaml · paths/(N files) · components/schemas/(M files)
**Changes:** Created … / Updated … / Removed …
**Verification (three-layer):**
- L1 speccheck.py: ✅ PASS (0 ERROR) / ❌ ESCALATED (N ERROR after ~3 rounds) · loop rounds: 0-3
  · $ref ✅ · coverage ✅ · property/required [X/Y] · status/security ✅ · validator <redocly|spectral|none>
- L2 fresh-eyes: ✅ Clean / ⚠️ N findings fixed / ⏭ Skipped / ⏸ Not run
- L3 completeness sweep: ✅ all routes + $refs covered / ⚠️ N silent omissions fixed
- Verdict: ✅ all green / ⚠️ warnings / ⏸ escalated
**Warnings:** false positives skipped, unresolved custom types, remaining discrepancies
```

---

## What this skill is NOT
- **Not** the Markdown generator — producing `docs/api/` Markdown from Go is the **`api-doc`** skill (its sibling; same Go source, different output).
- **Not** a Bruno OpenCollection generator (**`open-collection`**) — though `open-collection` can read this spec.
- **Not** a Confluence publisher (**`confluence-api-doc`**) — though it too can read this spec.
- **Not** a hand-authoring / curl-Postman converter or interactive editor.
- The verify script is a **tripwire**: a flag means inspect, a NOTE means a human/fresh-eyes call. Full coverage of the [Verification Checklist](references/openapi-doc-template.md#verification-checklist) comes from L1 (mechanical) + L2 (judgment) + L3 (completeness) together.

> **Maintenance note.** `references/go-scan-patterns.md` is a deliberate **copy** of `api-doc`'s — the Go-reading rules are shared between the two sibling generators, but each skill is self-contained. When either copy changes (a new framework, an error-tracing rule), **edit both** (`skills/api-doc/references/go-scan-patterns.md` and `skills/openapi-doc/references/go-scan-patterns.md`) to keep them in sync.

## Expanding to other languages
Add `references/<language>-scan-patterns.md` (route/handler/usecase patterns), teach Step 1 to detect the language (`package.json` → Node, etc.); the templates + verify are unchanged.
