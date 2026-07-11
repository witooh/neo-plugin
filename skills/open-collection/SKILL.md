---
name: open-collection
description: >
  Generate a **runnable, self-documenting** Bruno OpenCollection from the custom-YAML **API spec**
  at `docs/api/*.yaml` — one request `.yml` per endpoint, grouped by domain, with `environments/`
  + `folder.yml` auth and a generated `docs:` block per request (rendered from the api-spec, so the
  collection documents itself). Also update or validate an existing collection. Built-in three-layer
  verify (deterministic script + independent fresh-eyes agent + completeness sweep). Trigger on:
  "gen open collection", "สร้าง open collection", "สร้าง bruno จาก api spec", "อัปเดต bruno collection",
  "bruno from docs/api". Also runs at the using-neo Ship phase as a runnable API-collection
  deliverable. NOTE: the `docs/api/*.yaml`
  api-spec is authored by the **`api-spec`** skill (via `/spec`) and drift-checked against Go by
  `openapi-doc`; this skill only reads it — if missing, run `/spec` first. Publishing to Confluence
  is `confluence-api-doc`. Not a curl/Postman/OpenAPI converter or an editor.
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

Turn the custom-YAML **API spec** at `docs/api/*.yaml` into a **runnable** Bruno OpenCollection — one request `.yml` per endpoint, grouped by domain, plus `environments/` and `folder.yml`. The api-spec is the **single source of truth** for the contract (the `api-spec` skill authors it via `/spec`; `openapi-doc` drift-checks it against Go). The collection is **self-documenting** — each request carries a generated `docs:` rendered from the api-spec endpoint, and the collection/folder carry the `_meta` overview. The result is verified against the source on **evidence (a deterministic script) + an independent fresh-eyes pass + a completeness sweep**.

`ASSET_DIR` = `<skill base dir>/assets`, `SKILL_DIR` = `<skill base dir>` (the skill-load message gives the "Base directory for this skill").

## Output structure

```
<collection-root>/                 ← normally bruno/ (the api-spec source lives elsewhere, under docs/api/)
├── opencollection.yml          ← collection root config (info + ignore + docs: from _meta)
├── environments/
│   ├── local.yml               ← baseUrl + one var per {{name}} seen
│   └── sit.yml
├── <group>/
│   ├── folder.yml              ← display name, seq, shared headers + auth (+ docs: group prose)
│   ├── <endpoint>.yml          ← one runnable request (info → http → docs → settings)
│   └── ...
└── ...
```

The `<collection-root>` is normally `bruno/`. The **api-spec source is separate** — it lives under `docs/api/` (authored by the `api-spec` skill), not inside the collection root; this skill **reads** it and never writes there. The directory mirrors the api-spec's domain groups (each endpoint's `domain` → `<group>/`). Path params appear two ways in a request — `:id` in `http.url` and `name:id type:path` in `params` (the native `{id}` form lives in the api-spec `path`).

## Mode

Auto-detect (user can override): no `opencollection.yml` at the target → **Generate**; request says "validate/check/เช็ค/ตรงกับ doc ไหม" → **Validate**; otherwise → **Update**.

---

## Step 1 · Locate the source + collection root + context
- **Source** — the **api-spec** at `docs/api/*.yaml`; if it does not exist → **STOP** (run `/spec` — the api-spec skill authors it). In a monorepo, scope to the chosen service's `docs/api/`.
- **Collection root** (in order): explicit path from the user → walk **up** from cwd for an existing `opencollection.yml` → an existing collection dir (one that holds an `opencollection.yml`) under `bruno/` | `bruno-collection/` | `open-collection/` → else propose `<repo-root>/bruno/` and **confirm before writing**. The api-spec source (`docs/api/`) is **outside** the collection root — never confuse the two.
- Read `CLAUDE.md` / `AGENTS.md` / `README` for the service name (`info.name`), the dev port (the `local` environment's `baseUrl` — a small config peek, not a Go scan), and known environments (local/sit/uat/prod).

## Step 2 · Read the source endpoints
Read [`references/request-template.md`](references/request-template.md) — **§0** (api-spec source). **Do not scan Go** — the api-spec was already drift-checked against the code by `openapi-doc`.
- **Hand-map** each endpoint YAML → one request (`path_params`/`query_params` populate `params`; `request_body.example` → `http.body.data` verbatim; `auth` → request/folder auth; `_meta.base_url` + `path` → the `{{baseUrl}}` URL). Render each endpoint's `docs:` with `yaml2md.py` (see Step 3). *(There is no `bru import openapi` — the custom YAML is not OpenAPI; always hand-map.)*

## Step 3 · Generate / Update / Validate
Write using [`references/request-template.md`](references/request-template.md) (per-file templates) + [`references/yaml-reference.md`](references/yaml-reference.md) (schema):
- **opencollection.yml** — `info.name` + ignore config + `docs:` = the `_meta` index rendered by `python3 <ASSET_DIR>/yaml2md.py --index docs/api/_meta.yaml docs/api`.
- **environments/** — one file per environment; `baseUrl` + a var per `{{name}}` referenced in any request; secret-looking names → `value: ""` + `secret: true` (never write a literal secret).
- **`<group>/folder.yml`** — display name, `seq` (10,20,30…), shared headers + auth derived from the endpoints' `auth`; `docs:` = the domain group prose from `_meta.domains.<group>`.
- **`<group>/<endpoint>.yml`** — `info → http → docs → settings`. `http.body.data` is the endpoint's `request_body.example` JSON copied verbatim — never hand-assemble it. Omit `body` when the endpoint has no request body. **`docs:`** = `python3 <ASSET_DIR>/yaml2md.py docs/api/<group>/<endpoint>.yaml` (the rendered endpoint Markdown — `colcheck.py` K7 enforces it matches exactly).
- **Update** — diff against existing files; touch the minimum; **preserve** any user-added `headers`/`auth`/env values (often hand-typed secrets); re-render `docs:` from the api-spec; assign the next free `seq` for new requests.
- **Validate** — no writes; run the verify layers below as a pure check and produce a report.

### verify-L1 · Script tripwire (always)
```
python3 <ASSET_DIR>/colcheck.py <collection-root> --spec docs/api
```
It mechanically checks api-spec↔collection coverage (missing/orphan request files, folder.yml per group), `http.method`/`http.url` vs the endpoint, `http.body.data` == the endpoint's `request_body.example`, `http.url` path-params ↔ `params`, `body.data` JSON validity, `seq` uniqueness, every `{{var}}` defined in `environments/`, and **K7 — each request's `docs:` equals `yaml2md`'s render of the endpoint**. Needs PyYAML. **Tripwire, not ground truth** — a flag means "inspect this".
- **exit 0** → go to L1.5.
- **exit 1** → for each ERROR, open the actual `.yml`/`.yaml`: real mismatch → fix → re-run; genuine false positive → skip + record under Warnings. **Loop until exit 0, OR ~3 rounds with no progress → STOP and escalate.** Never fake a green run.
- Collect every **`NOTE`** line (each ends `needs fresh-eyes`) — they feed L2.

### verify-L1.5 · Offer fresh-eyes (default yes)
Ask once via `AskUserQuestion`: *"Run an independent fresh-eyes verify of the generated collection? (default: yes)"* — **no** → skip L2 (mark "skipped by user"); **yes** → L2.

### verify-L2 · Fresh-eyes verifier (independent agent)
Dispatch a verifier that did **not** write the collection — it re-reads the api-spec itself and checks the judgment-level accuracy the script cannot (auth semantic mapping, header completeness, that the runnable body truly corresponds field-for-field to the api-spec, and that the rendered `docs:` reads faithfully):
```
Agent(subagent_type: "general-purpose", description: "verify open collection", prompt: """
# Role: Open Collection Verifier
Read first: <SKILL_DIR>/references/col-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the collection just written against the docs/api/*.yaml api-spec.
Check ONLY judgment-level accuracy (not the script's mechanical checks). Read the
source yourself.

## Files under review
<list the request .yml + folder.yml files just created/updated> + the docs/api/*.yaml api-spec

## colcheck NOTEs to focus on
<paste every NOTE line from L1>

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
""")
```
`SKILL_DIR` is mandatory — without it the verifier cannot read its role file and fails silently. The verifier is read-only → **you** fix the files → re-run `colcheck.py`. Do not auto-redispatch; offer a second round (default yes), then escalate.

### verify-L3 · Completeness sweep (omission critic)
L1/L2 inspect what is present; L3 catches what is **missing entirely**. Re-enumerate the **full inventory straight from the api-spec** (every `docs/api/<domain>/*.yaml` endpoint) plus every `{{var}}` referenced, and confirm: every endpoint has a request `.yml` (with a `docs:`), every group has a `folder.yml`, every referenced variable has an `environments/` entry, and no request file is an orphan. Report any whole endpoint/group/variable the pipeline silently dropped; fix → re-run L1.

### Output
```
## Open Collection — <Generate / Update / Validate>
**Collection:** <root>   **Source:** docs/api/*.yaml api-spec
**Structure:** opencollection.yml · environments/(…) · <group>/(folder.yml + N requests) …
**Changes:** Created … / Updated … / Removed …
**Verification (three-layer):**
- L1 colcheck.py: ✅ PASS (0 ERROR) / ❌ ESCALATED (N ERROR after ~3 rounds) · loop rounds: 0-3
  · coverage ✅ · method/path [X/Y] · body↔example [X/Y] · docs: K7 [X/Y] · path-params ✅ · env vars ✅ · seq ✅
- L2 fresh-eyes: ✅ Clean / ⚠️ N findings fixed / ⏭ Skipped / ⏸ Not run
- L3 completeness sweep: ✅ all endpoints/groups/vars covered / ⚠️ N silent omissions fixed
- Verdict: ✅ all green / ⚠️ warnings / ⏸ escalated
**Warnings:** false positives skipped, multipart/oauth flagged for manual review, remaining discrepancies
```

---

## What this skill is NOT
- **Not** a source generator — the `docs/api/*.yaml` api-spec is authored by the **`api-spec`** skill and drift-checked against Go by **`openapi-doc`**; this skill reads it.
- **Not** a Confluence publisher — that is the **`confluence-api-doc`** skill.
- **Not** a hand-authoring / curl-Postman-OpenAPI converter or interactive editor (there is no OpenAPI intermediate in this chain).
