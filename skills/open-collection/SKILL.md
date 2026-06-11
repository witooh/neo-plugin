---
name: open-collection
description: >
  Generate a **runnable** Bruno OpenCollection from existing `docs/api/` Markdown API
  docs — one request `.yml` per endpoint, grouped by domain, with `environments/` and
  `folder.yml` auth. The collection is **runnable-only** (URLs, params, bodies, headers,
  auth, envs); the documentation stays in the Markdown. Also update or validate an
  existing collection against the Markdown. Built-in **three-layer verify** (deterministic
  script + independent fresh-eyes agent + completeness sweep). Trigger on:
  "gen open collection", "สร้าง open collection", "สร้าง bruno จาก api doc",
  "อัปเดต bruno collection", "scaffold opencollection.yml from docs",
  "make a runnable collection from the api docs", "bruno from markdown". Also trigger
  when neo delegates collection generation. NOTE: generating the Markdown docs themselves
  from Go source is the `api-doc` skill; publishing the docs to Confluence is the
  `confluence-api-doc` skill. Input is `docs/api/` Markdown — if it does not exist, run
  `api-doc` first. Not a curl/Postman/OpenAPI converter or an interactive editor.
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

Turn `docs/api/` Markdown API docs into a **runnable** Bruno OpenCollection — one request `.yml` per endpoint, grouped by domain, plus `environments/` and `folder.yml`. The Markdown is the **single source of truth**; this skill only produces the *runnable* artifact (method, URL, path/query params, request body, headers, auth, environments) and embeds **no `docs:`** blocks. The result is verified against the Markdown on **evidence (a deterministic script) + an independent fresh-eyes pass + a completeness sweep**.

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

## Step 1 · Locate the Markdown source + collection root + context
- **Markdown source** — default `docs/api/` (the `api-doc` skill's output). **No `docs/api/index.md`** → **STOP**: there is nothing to convert; run the `api-doc` skill first. In a monorepo, scope to the chosen service's `docs/api/`.
- **Collection root** (in order): explicit path from the user → walk **up** from cwd for an existing `opencollection.yml` → an existing `bruno/` | `bruno-collection/` | `open-collection/` at the repo root → else propose `<repo-root>/bruno/<service>/` and **confirm before writing**.
- Read `CLAUDE.md` / `AGENTS.md` / `README` for the service name (→ `info.name`), the dev port (→ `LOCAL` `baseUrl` — a small config peek, not a Go scan), and known environments (LOCAL/SIT/UAT/PROD).

## Step 2 · Read the Markdown endpoints
Read [`references/request-template.md`](references/request-template.md) **§0 — the input contract**. For each `docs/api/<group>/<endpoint>.md` (skip `index.md`), extract only the runnable bits: `**Method**` → `http.method`; `**Path**` (`{id}` form) → `http.url` (`:id`) + a `params` row per path param; `**Auth**` → folder/request auth; `## Path Parameters` / `## Query Parameters` tables → `params`; the `## Request Example` ` ```json ` block → `http.body.data` **verbatim**. **Do not re-scan Go** — the Markdown was already verified against the code by `api-doc`.

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
python3 <ASSET_DIR>/colcheck.py <collection-root> --md docs/api/
```
It mechanically checks Markdown↔collection coverage (missing/orphan request files, folder.yml per group), `http.method`/`http.url` vs the Markdown `**Method**`/`**Path**`, `http.body.data` == the Markdown `## Request Example`, `http.url` path-params ↔ `params`, `body.data` JSON validity, `seq` uniqueness, and that every `{{var}}` is defined in `environments/`. **Tripwire, not ground truth** — a flag means "inspect this".
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
L1/L2 inspect what is present; L3 catches what is **missing entirely**. Re-enumerate the **full inventory straight from `docs/api/`** (every group folder, every endpoint `.md`, every `{{var}}` referenced) and confirm: every endpoint has a request `.yml`, every group has a `folder.yml`, every referenced variable has an `environments/` entry, and no request file is an orphan. Report any whole endpoint/group/variable the pipeline silently dropped; fix → re-run L1.

### Output
```
## Open Collection — <Generate / Update / Validate>
**Collection:** <root>   **Source:** docs/api/
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
- **Not** the Markdown generator — producing `docs/api/` from Go is the **`api-doc`** skill (run it first; this skill reads its output).
- **Not** a Confluence publisher — that is the **`confluence-api-doc`** skill.
- **Not** a hand-authoring / curl-Postman-OpenAPI converter or interactive editor.
- **Not** a documentation carrier — the collection holds no `docs:`; the Markdown remains the single source of truth.
