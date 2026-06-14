---
name: open-collection
description: >
  Generate a **runnable** Bruno OpenCollection from existing `docs/api/` Markdown API
  docs **or** a `docs/openapi/` OpenAPI 3.2 spec — one request `.yml` per endpoint, grouped
  by domain, with `environments/` and `folder.yml` auth. The collection is **runnable-only** (URLs, params, bodies, headers,
  auth, envs); the documentation stays in the Markdown. Also update or validate an
  existing collection against the Markdown. Built-in **three-layer verify** (deterministic
  script + independent fresh-eyes agent + completeness sweep). Trigger on:
  "gen open collection", "สร้าง open collection", "สร้าง bruno จาก api doc",
  "อัปเดต bruno collection", "scaffold opencollection.yml from docs",
  "make a runnable collection from the api docs", "bruno from markdown",
  "bruno from openapi", "สร้าง bruno จาก openapi spec". Also trigger when neo delegates
  collection generation. NOTE: generating the Markdown docs from Go source is the `api-doc`
  skill; generating the OpenAPI spec is `openapi-doc`; publishing to Confluence is
  `confluence-api-doc`. Input is the `docs/api/` Markdown or the `docs/openapi/` spec
  (auto-prefers the spec when both exist) — if neither exists, run `api-doc` / `openapi-doc`
  first. Not a curl/Postman converter or an interactive editor.
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

# Open Collection

Turn the `docs/api/` Markdown API docs **or** a `docs/openapi/` OpenAPI 3.2 spec into a **runnable** Bruno OpenCollection — one request `.yml` per endpoint, grouped by domain, plus `environments/` and `folder.yml`. The chosen source is the **single source of truth** (already verified against Go by `api-doc`/`openapi-doc`); this skill only produces the *runnable* artifact (method, URL, path/query params, request body, headers, auth, environments) and embeds **no `docs:`** blocks. The result is verified against that source on **evidence (a deterministic script) + an independent fresh-eyes pass + a completeness sweep**.

`ASSET_DIR` = `<skill base dir>/assets`, `SKILL_DIR` = `<skill base dir>` (the skill-load message gives the "Base directory for this skill").

## Output structure

```
<collection-root>/
├── opencollection.yml          ← collection root config (info + ignore; no docs:)
├── environments/
│   ├── LOCAL.yml               ← baseUrl + one var per {{name}} seen
│   └── SIT.yml
├── <group>/
│   ├── folder.yml              ← display name, seq, shared headers + auth
│   ├── <endpoint>.yml          ← one runnable request (info → http → settings)
│   └── ...
└── ...
```

The directory mirrors `docs/api/`: `docs/api/<group>/<endpoint>.md` → `<group>/<endpoint>.yml`. Path params appear two ways in a request — `:id` in `http.url` and `name:id type:path` in `params` (the human `{id}` form lives only in the Markdown).

## Mode

Auto-detect (user can override): no `opencollection.yml` at the target → **Generate**; request says "validate/check/เช็ค/ตรงกับ doc ไหม" → **Validate**; otherwise → **Update**.

---

## Step 1 · Locate the source + collection root + context
- **Source (auto, prefer openapi)** — if `docs/openapi/openapi.yaml` exists → source = the **OpenAPI spec**; else if `docs/api/index.md` exists → source = the **Markdown**; else **STOP** (run `openapi-doc` or `api-doc` first). When **both** exist, prefer the spec. An explicit user request ("from the markdown" / "use the openapi spec") overrides the auto-pick — then run `colcheck.py` with the matching `--md` / `--spec` flag. **State the chosen source** in the run output. In a monorepo, scope to the chosen service.
- **Collection root** (in order): explicit path from the user → walk **up** from cwd for an existing `opencollection.yml` → an existing `bruno/` | `bruno-collection/` | `open-collection/` at the repo root → else propose `<repo-root>/bruno/<service>/` and **confirm before writing**.
- Read `CLAUDE.md` / `AGENTS.md` / `README` for the service name (→ `info.name`), the dev port (→ `LOCAL` `baseUrl` — a small config peek, not a Go scan), and known environments (LOCAL/SIT/UAT/PROD).

## Step 2 · Read the source endpoints
Read [`references/request-template.md`](references/request-template.md) — **§0** (Markdown source) or **§0b** (OpenAPI spec source), per the source chosen in Step 1. **Do not re-scan Go** — the source was already verified against the code by `api-doc`/`openapi-doc`.
- **Markdown source** — for each `docs/api/<group>/<endpoint>.md` (skip `index.md`), extract the runnable bits: `**Method**` → `http.method`; `**Path**` (`{id}` form) → `http.url` (`:id`) + a `params` row per path param; `**Auth**` → folder/request auth; the Path/Query tables → `params`; the `## Request Example` ` ```json ` block → `http.body.data` **verbatim**.
- **OpenAPI spec source** — **prefer Bruno's native importer**: `bru import openapi --source <bundled-spec> --output <collection-root> --collection-name "<service>" --collection-format=opencollection` (it resolves `$ref`s), then post-process to this skill's conventions (`{{baseUrl}}` env var, secret masking, `seq`, folder auth) and **strip any `docs:`** Bruno adds. If `bru` is unavailable, hand-map per **§0b**: each operation → one request (`parameters` → `params`; `requestBody…examples.default.value` → `http.body.data` verbatim; `security` → auth; `servers[].url` → `{{baseUrl}}`).

## Step 3 · Generate / Update / Validate
Write using [`references/request-template.md`](references/request-template.md) (per-file templates) + [`references/yaml-reference.md`](references/yaml-reference.md) (schema):
- **opencollection.yml** — `info.name` + ignore config. **No `docs:`.**
- **environments/** — one file per environment; `baseUrl` + a var per `{{name}}` referenced in any request; secret-looking names → `value: ""` + `secret: true` (never write a literal secret).
- **`<group>/folder.yml`** — display name, `seq` (10,20,30…), shared headers + auth derived from the endpoints' `**Auth**` bullet (`inherit`/`none`/explicit).
- **`<group>/<endpoint>.yml`** — `info → http → settings` only. `http.body.data` is the Markdown `## Request Example` JSON copied verbatim — never hand-assemble it from the field table. Omit `body` when the endpoint has no Request Example.
- **Update** — diff against existing files; touch the minimum; **preserve** any user-added `headers`/`auth`/env values (often hand-typed secrets); assign the next free `seq` for new requests.
- **Validate** — no writes; run the verify layers below as a pure check and produce a report.

### verify-L1 · Script tripwire (always)
```
python3 <ASSET_DIR>/colcheck.py <collection-root> --md docs/api/        # markdown source
python3 <ASSET_DIR>/colcheck.py <collection-root> --spec docs/openapi/  # openapi spec source
```
Pass the flag for the source chosen in Step 1 (with neither, it auto-prefers the spec when `docs/openapi/openapi.yaml` exists). It mechanically checks source↔collection coverage (missing/orphan request files, folder.yml per group), `http.method`/`http.url` vs the source, `http.body.data` == the source's runnable example, `http.url` path-params ↔ `params`, `body.data` JSON validity, `seq` uniqueness, and that every `{{var}}` is defined in `environments/`. In `--spec` mode coverage + body fidelity match the collection to the spec by (method, path); the structural + env checks are identical (and `--spec` needs PyYAML). **Tripwire, not ground truth** — a flag means "inspect this".
- **exit 0** → go to L1.5.
- **exit 1** → for each ERROR, open the actual `.yml`/`.md`: real mismatch → fix → re-run; genuine false positive → skip + record under Warnings. **Loop until exit 0, OR ~3 rounds with no progress → STOP and escalate.** Never fake a green run.
- Collect every **`NOTE`** line (each ends `needs fresh-eyes`) — they feed L2.

### verify-L1.5 · Offer fresh-eyes (default yes)
Ask once via `AskUserQuestion`: *"Run an independent fresh-eyes verify of the generated collection? (default: yes)"* — **no** → skip L2 (mark "skipped by user"); **yes** → L2.

### verify-L2 · Fresh-eyes verifier (independent agent)
Dispatch a verifier that did **not** write the collection — it re-reads the Markdown itself and checks the judgment-level accuracy the script cannot (auth semantic mapping, header completeness, that the runnable body truly corresponds field-for-field to the Markdown):
```
Agent(subagent_type: "general-purpose", description: "verify open collection", prompt: """
# Role: Open Collection Verifier
Read first: <SKILL_DIR>/references/col-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the collection just written against the docs/api markdown.
Check ONLY judgment-level accuracy (not the script's mechanical checks). Read the
markdown yourself.

## Files under review
<list the request .yml + folder.yml files just created/updated> + the docs/api markdown

## colcheck NOTEs to focus on
<paste every NOTE line from L1>

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
""")
```
`SKILL_DIR` is mandatory — without it the verifier cannot read its role file and fails silently. The verifier is read-only → **you** fix the files → re-run `colcheck.py`. Do not auto-redispatch; offer a second round (default yes), then escalate.

### verify-L3 · Completeness sweep (omission critic)
L1/L2 inspect what is present; L3 catches what is **missing entirely**. Re-enumerate the **full inventory straight from the chosen source** (`docs/api/` markdown: every group folder + endpoint `.md`; or `docs/openapi/` spec: every operation in the root `paths:`) plus every `{{var}}` referenced, and confirm: every endpoint/operation has a request `.yml`, every group has a `folder.yml`, every referenced variable has an `environments/` entry, and no request file is an orphan. Report any whole endpoint/group/variable the pipeline silently dropped; fix → re-run L1.

### Output
```
## Open Collection — <Generate / Update / Validate>
**Collection:** <root>   **Source:** <docs/api/ markdown | docs/openapi/ spec>
**Structure:** opencollection.yml · environments/(…) · <group>/(folder.yml + N requests) …
**Changes:** Created … / Updated … / Removed …
**Verification (three-layer):**
- L1 colcheck.py: ✅ PASS (0 ERROR) / ❌ ESCALATED (N ERROR after ~3 rounds) · loop rounds: 0-3
  · coverage ✅ · method/path [X/Y] · body↔example [X/Y] · path-params ✅ · env vars ✅ · seq ✅
- L2 fresh-eyes: ✅ Clean / ⚠️ N findings fixed / ⏭ Skipped / ⏸ Not run
- L3 completeness sweep: ✅ all endpoints/groups/vars covered / ⚠️ N silent omissions fixed
- Verdict: ✅ all green / ⚠️ warnings / ⏸ escalated
**Warnings:** false positives skipped, multipart/oauth flagged for manual review, remaining discrepancies
```

---

## What this skill is NOT
- **Not** a source generator — producing the `docs/api/` Markdown from Go is the **`api-doc`** skill, and the `docs/openapi/` spec is **`openapi-doc`** (run one first; this skill reads their output).
- **Not** a Confluence publisher — that is the **`confluence-api-doc`** skill.
- **Not** a hand-authoring / curl-Postman-OpenAPI converter or interactive editor.
- **Not** a documentation carrier — the collection holds no `docs:`; the Markdown remains the single source of truth.
