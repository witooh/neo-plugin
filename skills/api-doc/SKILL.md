---
name: api-doc
description: >
  Generate API documentation from Go source as structured Markdown in `docs/api/`
  — one file per endpoint grouped by handler domain, plus an `index.md` — or
  update/validate existing docs against the current code. Each endpoint file carries
  the field/error tables, business-logic steps, and request/response examples.
  Built-in **three-layer verify** (deterministic script + independent fresh-eyes
  agent + completeness sweep). Trigger on: "gen api doc", "สร้าง api doc",
  "อัปเดต api doc", "เช็ค api doc ตรงกับ code ไหม", "document these endpoints",
  "generate endpoint docs from code", "api doc outdated". Also trigger when neo
  delegates API documentation tasks. NOTE: this skill produces the **Markdown docs
  only** — generating a runnable Bruno OpenCollection *from* those docs is the
  `open-collection` skill; publishing them to Confluence is the `confluence-api-doc`
  skill; generating an **OpenAPI 3.2** spec from the same Go source is the `openapi-doc`
  skill. It is not a curl/Postman converter or an interactive editor.
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

# API Doc

Generate API documentation from source as structured **Markdown** under `docs/api/` — one file per endpoint, grouped by handler domain, plus an `index.md`. The markdown is the **single source of truth**: the `open-collection` skill derives a runnable Bruno collection from it, and `confluence-api-doc` publishes it. Each doc is verified on **evidence (a deterministic script) + an independent fresh-eyes pass + a completeness sweep**, never on the writing agent's confidence.

`ASSET_DIR` = `<skill base dir>/assets`, `SKILL_DIR` = `<skill base dir>` (the skill-load message gives the "Base directory for this skill"). Currently optimized for Go (Fiber, Echo, Chi, Gin).

## Output structure

```
docs/api/
├── index.md              ← service header, overview, endpoints table, common errors
├── <group>/
│   ├── <endpoint>.md     ← one endpoint per file
│   └── ...
└── ...
```

- **Grouping** — each subdirectory under the handler base directory = one group.
- **File naming** — handler function name → kebab-case (`AcceptConsent` → `accept-consent.md`).
- **Path params in docs** — always `{param}` form in the documented path, regardless of framework syntax (`:id` → `{id}`).
- **`index.md`** links to every endpoint file.

## Mode

Auto-detect (user can override): no `docs/api/index.md` → **Generate**; request says "validate/check/เช็ค/ตรงกับ code ไหม" → **Validate**; otherwise → **Update**.

---

## Step 1 · Locate `docs/api/` + project context
- **Doc root** — default `docs/api/` at the repo root; in a monorepo scope it to the chosen service (e.g. `services/<name>/docs/api/`).
- Read `CLAUDE.md` / `AGENTS.md` / `README` for service name, framework, API version, and the `/api/v1/` versioning pattern.
- **Not a Go project** (no `go.mod` and no `references/<lang>-scan-patterns.md`) → **STOP**: Go only; do not guess patterns.
- **Monorepo** (multiple `go.mod`) → ask which service, then scope the scan + `docs/api/` to that one service.

## Step 2 · Discover routes & groups
Read [`references/go-scan-patterns.md`](references/go-scan-patterns.md) (route registration patterns + § Handler Directory Scanning). Find every route (method, path, handler), its group, and middleware (auth). A route matched by a `docs/api/.docignore` glob or carrying a `// apidoc:ignore` comment above its registration is intentionally undocumented (internal/debug/health) — skip it in Generate/Update, treat it as expected-absent in Validate. (`doccheck.py` does not read `.docignore`, so an intentionally-skipped route surfaces as a coverage ERROR — confirm it and skip it as a known false positive per the Layer-1 loop below.)

## Step 3 · Extract per endpoint
For each route, trace handler → usecase → repository and extract: request/response shape (path/query/body, success status — read the actual `c.JSON(NNN, …)`, don't guess), business-logic steps, and error responses. Apply the **single sources**, do not restate them:
- Field extraction, error tracing, **step counting** (Priority 1 = `### Logical` / `Step N:` header comments verbatim; Priority 2 = code-derived: 1 step per repo/service/external call + per sentinel-returning `if`/`switch`; a repo call + its nil-check = 2 steps; not a step: error propagation, stdlib, struct construction, entity mutation without I/O, logging) → [`references/go-scan-patterns.md`](references/go-scan-patterns.md).
- M/O classification, field-description formulas, example values, error enumeration → [`references/api-doc-template.md`](references/api-doc-template.md).

## Step 4 · Generate / Update / Validate
Write using [`references/api-doc-template.md`](references/api-doc-template.md) (Index Template + Per-Endpoint Template):
- **`index.md`** — service header, overview paragraph, an endpoints table per group (each row links to the endpoint file), and a Common Error Responses section (generic 401/403 etc. live here only, not repeated per endpoint).
- **`<group>/<endpoint>.md`** — breadcrumb back to `index.md`, then one endpoint: Method/Path/Auth, Path/Query/Body tables, Request Example (runnable JSON), Response + Response Example, Business Logic steps, Error Responses. H1 = endpoint name; H2 = sub-sections.
- **Update** — diff against existing files; touch the minimum; create/update/remove individual files; move a file if its handler changed group; regenerate `index.md`. Preserve any manually-added prose that isn't auto-generated.
- **Validate** — no writes; run the verify layers below as a pure check and produce a report.

### verify-L1 · Script tripwire (always)
```
python3 <ASSET_DIR>/doccheck.py docs/api/ --src <project-root>
```
`<project-root>` = the repo root where `go.mod` lives (usually `.`). It mechanically checks index-link integrity + endpoint↔file coverage, per-table field count + M/O vs Go structs, Method/Path/example presence, and JSON validity. **Tripwire, not ground truth** — a flag means "inspect this".
- **exit 0** → go to L1.5.
- **exit 1** → for each ERROR, open the actual struct/route: real mismatch → fix → re-run; genuine false positive (e.g. a `.docignore`'d route) → skip + record under Warnings (never blindly "fix"). **Loop until exit 0, OR ~3 rounds with no progress → STOP and escalate** with the remaining ERRORs. Never fake a green run.
- Collect every **`NOTE`** line (each ends `needs fresh-eyes`) — they feed L2; NOTEs don't fail the run.

### verify-L1.5 · Offer fresh-eyes (default yes)
Ask once via `AskUserQuestion`: *"Run an independent fresh-eyes verify of the generated docs? (default: yes)"* — **no** → skip L2 (mark "skipped by user"); **yes** → L2.

### verify-L2 · Fresh-eyes verifier (independent agent)
Dispatch a verifier that did **not** write the docs — it re-reads the Go source itself and checks only the judgment-level accuracy the script cannot (error-row tracing, step counting, M/O edge cases, custom types, text formulas):
```
Agent(subagent_type: "general-purpose", description: "verify api doc", prompt: """
# Role: API Doc Verifier
Read first: <SKILL_DIR>/references/api-doc-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the docs just generated. Check ONLY judgment-level accuracy
(not the script's mechanical checks). Read the Go source yourself.

## Docs under review
docs/api/<group>/<file>.md   (list the files just created/updated) + index.md

## doccheck NOTEs to focus on
<paste every NOTE line from L1>

## Project conventions
CLAUDE.md (the relevant section)

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
""")
```
`SKILL_DIR` is mandatory — without it the verifier cannot read its role file and fails silently. The verifier is read-only → **you** fix the files → re-run `doccheck.py` to confirm nothing regressed. Do not auto-redispatch; if findings are deep, offer a second fresh-eyes round (default yes), then escalate.

### verify-L3 · Completeness sweep (omission critic)
L1/L2 inspect what is *present*; L3 catches what is **missing entirely** — a whole endpoint or group that silently never got a file, which L1's best-effort route regex can miss (dynamic registration, unusual patterns). Re-derive the **full endpoint inventory straight from the router-setup file yourself** (read it, don't lean on the script), then confirm:
- every registered route (minus `.docignore` / `// apidoc:ignore`) has a `docs/api/` file,
- every `docs/api/` file maps to a real route (no orphan),
- `index.md` lists every endpoint and every group folder is represented.
Report any whole endpoint/group that the pipeline silently dropped; fix → re-run L1 to confirm.

### Output
```
## API Doc — <Generate / Update / Validate>
**Doc root:** docs/api/   **Structure:** index.md · <group>/(N files) …
**Changes:** Created … / Updated … / Removed …
**Verification (three-layer):**
- L1 doccheck.py: ✅ PASS (0 ERROR) / ❌ ESCALATED (N ERROR after ~3 rounds) · loop rounds: 0-3
  · coverage ✅ · field count [X/Y] · M/O [X/Y] · index links ✅ · JSON ✅
- L2 fresh-eyes: ✅ Clean / ⚠️ N findings fixed / ⏭ Skipped / ⏸ Not run
- L3 completeness sweep: ✅ all routes covered / ⚠️ N silent omissions fixed
- Verdict: ✅ all green / ⚠️ warnings / ⏸ escalated
**Warnings:** false positives skipped, unresolved custom types, remaining discrepancies
```

---

## What this skill is NOT
- **Not** the OpenAPI-spec generator — emitting an OpenAPI 3.2 spec to `docs/openapi/` from the same Go source is the **`openapi-doc`** skill (its sibling).
- **Not** a Bruno OpenCollection generator — deriving a runnable collection from `docs/api/` is the **`open-collection`** skill.
- **Not** a Confluence publisher — pushing `docs/api/` to Confluence is the **`confluence-api-doc`** skill.
- **Not** a hand-authoring / curl-Postman converter or interactive editor.
- The verify script is a **tripwire**: a flag means inspect, a NOTE means a human/fresh-eyes call. Full coverage of the [Verification Checklist](references/api-doc-template.md#verification-checklist) comes from L1 (mechanical) + L2 (judgment) + L3 (completeness) together.

## Expanding to other languages
Add `references/<language>-scan-patterns.md` (route/handler/usecase patterns), teach Step 1 to detect the language (`package.json` → Node, etc.); the templates + verify are unchanged.
