---
name: open-collection
description: >
  Generate a **runnable** Bruno OpenCollection from a `bruno/openapi/` OpenAPI 3.1 spec —
  one request `.yml` per endpoint, grouped by domain, with `environments/` and `folder.yml`
  auth. The collection is **runnable-only** (URLs, params, bodies, headers,
  auth, envs); the documentation stays in the spec. Also update or validate an
  existing collection against the spec. Built-in **three-layer verify** (deterministic
  script + independent fresh-eyes agent + completeness sweep). Trigger on:
  "gen open collection", "สร้าง open collection", "สร้าง bruno จาก openapi spec",
  "อัปเดต bruno collection", "scaffold opencollection from spec",
  "make a runnable collection from the openapi spec", "bruno from openapi". Also trigger
  when neo delegates collection generation. NOTE: generating the OpenAPI spec from Go
  source is the `openapi-doc` skill; publishing to Confluence is
  `confluence-api-doc`. Input is the `bruno/openapi/` spec — if it does not exist, run
  `openapi-doc` first. Not a curl/Postman converter or an interactive editor.
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

Turn a `bruno/openapi/` OpenAPI 3.1 spec into a **runnable** Bruno OpenCollection — one request `.yml` per endpoint, grouped by domain, plus `environments/` and `folder.yml`. The spec is the **single source of truth** (already verified against Go by `openapi-doc`); this skill only produces the *runnable* artifact (method, URL, path/query params, request body, headers, auth, environments) and embeds **no `docs:`** blocks. The result is verified against the spec on **evidence (a deterministic script) + an independent fresh-eyes pass + a completeness sweep**.

`ASSET_DIR` = `<skill base dir>/assets`, `SKILL_DIR` = `<skill base dir>` (the skill-load message gives the "Base directory for this skill").

## Output structure

```
<collection-root>/
├── opencollection.yml          ← collection root config (info + ignore; no docs:)
├── environments/
│   ├── local.yml               ← baseUrl + one var per {{name}} seen
│   └── sit.yml
├── <group>/
│   ├── folder.yml              ← display name, seq, shared headers + auth
│   ├── <endpoint>.yml          ← one runnable request (info → http → settings)
│   └── ...
└── ...
```

The `<collection-root>` is normally `bruno/` itself — the read-only `openapi/` spec dir (written by `openapi-doc`, this skill's source) sits inside it alongside the `<group>/` folders. The directory mirrors the spec's path groups (operation `tags[0]` → `<group>/`). Path params appear two ways in a request — `:id` in `http.url` and `name:id type:path` in `params` (the native `{id}` form lives in the spec).

## Mode

Auto-detect (user can override): no `opencollection.yml` at the target → **Generate**; request says "validate/check/เช็ค/ตรงกับ doc ไหม" → **Validate**; otherwise → **Update**.

---

## Step 1 · Locate the source + collection root + context
- **Source** — the **OpenAPI spec** at `bruno/openapi/openapi.yaml`; if it does not exist → **STOP** (run `openapi-doc` first). In a monorepo, scope to the chosen service's `bruno/openapi/`.
- **Collection root** (in order): explicit path from the user → walk **up** from cwd for an existing `opencollection.yml` → an existing collection dir (one that holds an `opencollection.yml`) under `bruno/` | `bruno-collection/` | `open-collection/` → else propose `<repo-root>/bruno/` and **confirm before writing**. **Never** use `bruno/openapi/` as the collection root — it is the OpenAPI spec source (the `openapi-doc` output) this skill *reads*, not a collection it writes; the spec lives in the `openapi/` subdirectory **inside** the collection root (`bruno/openapi/` under `bruno/`), so set the root to `bruno/` — never to `bruno/openapi/`.
- Read `CLAUDE.md` / `AGENTS.md` / `README` for the service name (→ `info.name`), the dev port (→ `local` `baseUrl` — a small config peek, not a Go scan), and known environments (local/sit/uat/prod).

## Step 2 · Read the source endpoints
Read [`references/request-template.md`](references/request-template.md) — **§0** (OpenAPI spec source). **Do not re-scan Go** — the spec was already verified against the code by `openapi-doc`.
- **OpenAPI spec source** — **prefer Bruno's native importer**: `bru import openapi --source bruno/openapi/openapi.yaml --output <collection-root> --collection-name "<Service Name>" --collection-format=opencollection` (it resolves the internal `$ref`s), then post-process to this skill's conventions (`{{baseUrl}}` env var, secret masking, `seq`, folder auth) and **strip any `docs:`** Bruno adds. If `bru` is unavailable, hand-map per **§0**: each operation → one request (`parameters` → `params`; `requestBody…examples.default.value` → `http.body.data` verbatim; `security` → auth; `servers[].url` → `{{baseUrl}}`).

## Step 3 · Generate / Update / Validate
Write using [`references/request-template.md`](references/request-template.md) (per-file templates) + [`references/yaml-reference.md`](references/yaml-reference.md) (schema):
- **opencollection.yml** — `info.name` + ignore config. **No `docs:`.**
- **environments/** — one file per environment; `baseUrl` + a var per `{{name}}` referenced in any request; secret-looking names → `value: ""` + `secret: true` (never write a literal secret).
- **`<group>/folder.yml`** — display name, `seq` (10,20,30…), shared headers + auth derived from the operations' `security` (`inherit`/`none`/explicit).
- **`<group>/<endpoint>.yml`** — `info → http → settings` only. `http.body.data` is the operation's `requestBody…examples.default.value` JSON copied verbatim — never hand-assemble it from the schema. Omit `body` when the operation has no request body.
- **Update** — diff against existing files; touch the minimum; **preserve** any user-added `headers`/`auth`/env values (often hand-typed secrets); assign the next free `seq` for new requests.
- **Validate** — no writes; run the verify layers below as a pure check and produce a report.

### verify-L1 · Script tripwire (always)
```
python3 <ASSET_DIR>/colcheck.py <collection-root> --spec bruno/openapi/
```
It mechanically checks spec↔collection coverage (missing/orphan request files, folder.yml per group), `http.method`/`http.url` vs the spec, `http.body.data` == the spec's runnable example, `http.url` path-params ↔ `params`, `body.data` JSON validity, `seq` uniqueness, and that every `{{var}}` is defined in `environments/`. Coverage + body fidelity match the collection to the spec by (method, path); it needs PyYAML. **Tripwire, not ground truth** — a flag means "inspect this".
- **exit 0** → go to L1.5.
- **exit 1** → for each ERROR, open the actual `.yml`/`.md`: real mismatch → fix → re-run; genuine false positive → skip + record under Warnings. **Loop until exit 0, OR ~3 rounds with no progress → STOP and escalate.** Never fake a green run.
- Collect every **`NOTE`** line (each ends `needs fresh-eyes`) — they feed L2.

### verify-L1.5 · Offer fresh-eyes (default yes)
Ask once via `AskUserQuestion`: *"Run an independent fresh-eyes verify of the generated collection? (default: yes)"* — **no** → skip L2 (mark "skipped by user"); **yes** → L2.

### verify-L2 · Fresh-eyes verifier (independent agent)
Dispatch a verifier that did **not** write the collection — it re-reads the spec itself and checks the judgment-level accuracy the script cannot (auth semantic mapping, header completeness, that the runnable body truly corresponds field-for-field to the spec):
```
Agent(subagent_type: "general-purpose", description: "verify open collection", prompt: """
# Role: Open Collection Verifier
Read first: <SKILL_DIR>/references/col-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the collection just written against the bruno/openapi spec.
Check ONLY judgment-level accuracy (not the script's mechanical checks). Read the
spec yourself.

## Files under review
<list the request .yml + folder.yml files just created/updated> + the bruno/openapi spec

## colcheck NOTEs to focus on
<paste every NOTE line from L1>

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
""")
```
`SKILL_DIR` is mandatory — without it the verifier cannot read its role file and fails silently. The verifier is read-only → **you** fix the files → re-run `colcheck.py`. Do not auto-redispatch; offer a second round (default yes), then escalate.

### verify-L3 · Completeness sweep (omission critic)
L1/L2 inspect what is present; L3 catches what is **missing entirely**. Re-enumerate the **full inventory straight from the spec** (`bruno/openapi/`: every operation in the root `paths:`) plus every `{{var}}` referenced, and confirm: every endpoint/operation has a request `.yml`, every group has a `folder.yml`, every referenced variable has an `environments/` entry, and no request file is an orphan. Report any whole endpoint/group/variable the pipeline silently dropped; fix → re-run L1.

### Output
```
## Open Collection — <Generate / Update / Validate>
**Collection:** <root>   **Source:** bruno/openapi/ spec
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
- **Not** a source generator — producing the `bruno/openapi/` spec from Go is the **`openapi-doc`** skill (run it first; this skill reads its output).
- **Not** a Confluence publisher — that is the **`confluence-api-doc`** skill.
- **Not** a hand-authoring / curl-Postman-OpenAPI converter or interactive editor.
- **Not** a documentation carrier — the collection holds no `docs:`; the OpenAPI spec remains the single source of truth.
