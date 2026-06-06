---
name: api-doc
description: >
  Generate API documentation from Go source as a runnable Bruno OpenCollection
  workspace, then publish it to Confluence — one skill, two commands, each with a
  built-in two-layer verify. Use the **gen** command to scan handler/router/usecase
  code and produce/update/validate an OpenCollection (opencollection.yml +
  environments/ + per-group folder.yml + one request .yml per endpoint, each with an
  embedded `docs:` markdown block). Use the **publish** command to sync that
  collection to Confluence pages (one endpoint = one page, grouped under domain
  parents; the collection-root overview becomes the parent page). Trigger on:
  "gen api doc", "สร้าง api doc", "อัปเดต api doc", "เช็ค api doc ตรงกับ code ไหม",
  "gen open collection", "สร้าง open collection", "อัปเดต bruno collection",
  "สร้าง bruno จาก code", "scaffold opencollection.yml from handlers",
  "document these endpoints", "api doc outdated"  →  gen; and
  "publish api doc", "sync api doc", "push doc to confluence",
  "sync open collection to confluence", "sync bruno to confluence",
  "อัปเดต api doc ไป confluence", "sync open-collection ไป confluence",
  "sync confluence pages"  →  publish. Also trigger when neo delegates API
  documentation tasks. NOTE: this skill is the code-to-collection
  generator + Confluence publisher, not an interactive editor or a
  curl/Postman/OpenAPI converter.
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

Generate API docs from source as a Bruno **OpenCollection** workspace (the single source of truth — runnable in Bruno, embeds per-endpoint `docs:` markdown), then publish that collection to **Confluence**. Two commands, each verified on **evidence (a deterministic script) + an independent second pass**, never on the writing agent's confidence.

`ASSET_DIR` = `<skill base dir>/assets`, `SKILL_DIR` = `<skill base dir>` (the skill-load message gives the "Base directory for this skill"). Currently optimized for Go (Fiber, Echo, Chi, Gin).

## Command Routing

Pick the command from the request; if genuinely ambiguous, ask once with `AskUserQuestion`.

| Signal | Command |
|--------|---------|
| `gen` / `generate` / "สร้าง" / "อัปเดต" / "validate" / "เช็ค … ตรงกับ code", a Go repo, "from code", "open collection", "bruno from code" | **gen** |
| `publish` / `sync` / "push to confluence" / "ไป confluence", a Confluence parent-page URL | **publish** |
| hand-authoring, curl/Postman/OpenAPI conversion, editing one request interactively | → out of scope (this skill is code-to-collection + publish, not an interactive editor) |

`gen` produces/updates the collection; `publish` ships an existing collection. They are independent — after a `gen`, offer to `publish` but don't assume it.

---

## Command: gen

Scan Go source → produce, update, or validate an OpenCollection workspace.

**Mode** (auto-detect; user can override): no `opencollection.yml` at the target → **Generate**; request says "validate/check/เช็ค/ตรงกับ code ไหม" → **Validate**; otherwise → **Update**.

### gen-0 · Locate root + project context
- **Collection root** (in order): explicit path from the user → walk **up** from cwd for an existing `opencollection.yml` → an existing `bruno/` | `bruno-collection/` | `open-collection/` at the repo root → else propose `<repo-root>/bruno/<service>/` and **confirm before writing**.
- Read `CLAUDE.md` / `AGENTS.md` / `README` for service name, framework, API version, and known environments (LOCAL/SIT/UAT/PROD).
- **Not a Go project** (no `go.mod` and no `references/<lang>-scan-patterns.md`) → **STOP**: Go only; do not guess patterns.
- **Monorepo** (multiple `go.mod`) → ask which service, then scope the scan + collection to that one service.

### gen-1 · Discover routes & groups
Read [`references/go-scan-patterns.md`](references/go-scan-patterns.md) (route registration patterns + § Handler Directory Scanning). Find every route (method, path, handler), its group, and middleware (auth). A route matched by a `.docignore` glob or carrying a `// apidoc:ignore` comment is intentionally undocumented — skip it in Generate/Update, treat it as expected-absent in Validate. (`gencheck.py` does not read `.docignore`, so an intentionally-skipped route surfaces as a coverage ERROR — confirm it and skip it as a known false positive per the Layer-1 loop below.)

### gen-2 · Extract per endpoint
For each route, trace handler → usecase → repository and extract: request/response shape (path/query/body, success status — read the actual `c.JSON(NNN, …)`, don't guess), business-logic steps, and error responses. Apply the **single sources**, do not restate them:
- Field extraction, error tracing, **step counting** (Priority 1 = `### Logical` / `Step N:` header comments verbatim; Priority 2 = code-derived: 1 step per repo/service/external call + per sentinel-returning `if`/`switch`; a repo call + its nil-check = 2 steps; not a step: error propagation, stdlib, struct construction, entity mutation without I/O, logging) → [`references/go-scan-patterns.md`](references/go-scan-patterns.md).
- M/O classification, field-description formulas, example values, error enumeration → [`references/api-doc-template.md`](references/api-doc-template.md).

### gen-3 · Generate / Update / Validate
Write using [`references/request-template.md`](references/request-template.md) (file templates) + [`references/yaml-reference.md`](references/yaml-reference.md) (schema):
- **opencollection.yml** — `info.name` + a collection-root **`docs:`** block = service **overview + Common Error Responses** (this replaces the old `index.md`; `publish` ships it to the parent page).
- **environments/** — one file per environment; `baseUrl` + a var per `{{name}}` seen; secret-looking vars → `value: ""` + `secret: true` (never write a literal secret).
- **`<group>/folder.yml`** — display name, `seq` (10,20,30…), shared headers + auth (`inherit`/`none`/explicit).
- **`<group>/<endpoint>.yml`** — `info → http → settings → docs` (no `runtime`/`examples`/tests). `docs:` is the per-endpoint markdown (the [`api-doc-template.md`](references/api-doc-template.md) per-endpoint template, no breadcrumb). Path params appear three ways: `:id` in `http.url`, `name:id type:path` in `params`, `{id}` in the documented path inside `docs:`.
- **Update** — diff against existing files; touch the minimum; **preserve** any user-added `runtime`/`scripts`/`examples` blocks and existing environment values (often hand-typed secrets); assign the next free `seq` for new requests.
- **Validate** — no writes; run the verify layers below as a pure check and produce a report.

### gen-verify · Layer 1 — script tripwire (always)
```
python3 <ASSET_DIR>/gencheck.py <collection-root> --src <project-root>
```
`<project-root>` = the repo root where `go.mod` lives (usually `.`). It mechanically checks route↔request-file coverage, collection-root `docs:` presence, per-`docs:`-table field count + M/O vs Go structs, `http.url`↔`params` path params, JSON validity (`http.body.data` + `docs:` fences), and seq uniqueness. **Tripwire, not ground truth** — a flag means "inspect this".
- **exit 0** → go to Layer 1.5.
- **exit 1** → for each ERROR, open the actual struct/route: real mismatch → fix → re-run; genuine false positive → skip + record under Warnings (never blindly "fix"). **Loop until exit 0, OR ~3 rounds with no progress → STOP and escalate** with the remaining ERRORs. Never fake a green run.
- Collect every **`NOTE`** line (each ends `needs fresh-eyes`) — they feed Layer 2; NOTEs don't fail the run.

### gen-verify · Layer 1.5 — offer fresh-eyes (default yes)
Ask once via `AskUserQuestion`: *"Run an independent fresh-eyes verify of the generated collection? (default: yes)"* — **no** → skip Layer 2 (mark "skipped by user"); **yes** → Layer 2.

### gen-verify · Layer 2 — fresh-eyes verifier (independent agent)
Dispatch a verifier that did **not** write the collection:
```
Agent(subagent_type: "general-purpose", description: "verify api doc", prompt: """
# Role: API Doc Verifier
Read first: <SKILL_DIR>/references/api-doc-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the OpenCollection just written. Check ONLY judgment-level
accuracy (not the script's mechanical checks). Read the Go source yourself.

## Files under review
<list the request .yml files just created/updated + opencollection.yml>

## gencheck NOTEs to focus on
<paste every NOTE line from Layer 1>

## Project conventions
CLAUDE.md (the relevant section)

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
""")
```
`SKILL_DIR` is mandatory — without it the verifier cannot read its role file and fails silently. The verifier is read-only → **you** fix the files → re-run `gencheck.py` to confirm nothing regressed. Do not auto-redispatch; if findings are deep, offer a second fresh-eyes round (default yes), then escalate.

### gen · Output
```
## API Doc — gen
**Mode:** Generate / Update / Validate   **Collection:** <root>
**Structure:** opencollection.yml · environments/(…) · <group>/(folder.yml + N requests) …
**Changes:** Created … / Updated … / Removed …
**Verification (two-layer):**
- L1 gencheck.py: ✅ PASS (0 ERROR) / ❌ ESCALATED (N ERROR after ~3 rounds) · loop rounds: 0-3
  · coverage ✅ · field count [X/Y] · M/O [X/Y] · path-params ✅ · JSON ✅ · root docs ✅
- L2 fresh-eyes: ✅ Clean / ⚠️ N findings fixed / ⏭ Skipped / ⏸ Not run
- Verdict: ✅ both green / ⚠️ warnings / ⏸ escalated
**Warnings:** false positives skipped, unresolved custom types, remaining discrepancies
```

---

## Command: publish

Sync an existing OpenCollection workspace to Confluence — one endpoint = one page, grouped under domain parents, with the collection-root `docs:` overview on the parent page. Input is an OpenCollection root only (markdown `docs/api/` is not a supported input).

Full procedure (auth, page-tree mapping, the markdown→storage conversion rules, REST calls, round-trip normalization) is the single source in [`references/publish-reference.md`](references/publish-reference.md) — follow it; the steps below are the spine.

1. **Gather** — collection root (must contain `opencollection.yml`; if not, STOP and suggest `gen`) + Confluence parent-page URL → page ID.
2. **Auth** — `acli auth status` → `CONFLUENCE_URL` + `EMAIL`; resolve the write token (`$CONFLUENCE_API_TOKEN` or ask once) at push time.
3. **Scan** — group pages from `folder.yml`; endpoint pages titled `<METHOD>: <path>` with body = each request's `docs:`; **parent page body = the collection-root `docs:`** (overview + common errors).
4. **Map** — fetch existing children (`curl GET …?expand=space,children.page`), match by exact title, plan create/update; create groups before endpoints.
5. **Versions** — `acli confluence page view --id <id> --include-version --json`.
6. **Convert** — markdown → Confluence storage per `publish-reference.md` (code blocks → code macro/CDATA **first**, then inline rules; mind the nested-list rule). Stage each page in the **gitignored** `.api-doc-publish/` as both a `<page>.json` manifest and a raw `storage/<page>.xml` (the latter feeds the L2 round-trip) — see `publish-reference.md`.
7. **Verify L1 — pre-flight (before any push):**
   ```
   python3 <ASSET_DIR>/pubcheck.py .api-doc-publish/
   ```
   Well-formedness · CDATA/table/list balance · bare `&`/`<` · **source↔storage element counts**. Loop fix→re-stage→re-run until exit 0, OR ~3 rounds → escalate. **Never push storage that failed pre-flight.**
8. **Sync** — REST create/update: domain-group pages → endpoint pages → parent page (version+1 on update; skip unchanged).
9. **Verify L2 — round-trip (after push):** re-fetch each page (`acli … --body-format storage --json`) and compare to the staged storage:
   ```
   python3 <ASSET_DIR>/pubcheck.py --roundtrip .api-doc-publish/storage/<page>.xml .api-doc-publish/refetched/<page>.xml
   ```
   Canonical compare (ignores Confluence's benign rewrites; CDATA must match exactly). Structural drift → review; **CDATA drift → a code example was mangled, investigate**. One round of fixes, then escalate.

### publish · Output
```
## API Doc — publish
**Collection:** <root>   **Parent page:** <id>
| Page | Type | Page ID | Status |
| --- | --- | --- | --- |
| (Service) Overview | Parent | … | Updated (v3→v4) |
| Consent | Domain group | … | Created |
| POST: /api/v1/consents | API page | … | Created |
**Totals:** N groups, M API pages — created K / updated U / skipped S / failed F
**Verification:** L1 pre-flight ✅/❌ · L2 round-trip: N/M clean, D drift (CDATA drift: …)
```

---

## What this skill is NOT
- **Not** a hand-authoring / curl-Postman-OpenAPI converter or interactive collection editor.
- **Not** a markdown `docs/api/` generator — the single source is the OpenCollection workspace (its `docs:` blocks carry the same field/error tables).
- The verify scripts are **tripwires**: a flag means inspect, a NOTE means a human/fresh-eyes call. Coverage of the full [Verification Checklist](references/api-doc-template.md#verification-checklist) comes from L1 (mechanical) + L2 (judgment) together.

## Expanding to other languages
Add `references/<language>-scan-patterns.md` (route/handler/usecase patterns), teach gen-0 to detect the language (`package.json` → Node, etc.), and the templates + verify are unchanged.
