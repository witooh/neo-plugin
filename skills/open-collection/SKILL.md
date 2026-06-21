---
name: open-collection
description: >
  Generate a **runnable** Bruno OpenCollection from a `bruno/openapi.yaml` OpenAPI 3.1 spec in one
  of two **source modes** — the skill **asks which mode** up front (smart-defaulted from the request; it no longer infers the mode silently). **Spec mode**: one request `.yml` per endpoint, grouped by
  domain, with `environments/` and `folder.yml` auth — **runnable-only** (URLs, params, bodies,
  headers, auth, envs); the documentation stays in the spec. **AC-scenario mode**: one request
  per Ready Acceptance-Criterion — a runnable **test-scenario** collection carrying
  `runtime.assertions` (expected HTTP status + stable error code), joining the spec (contract
  anchor) with neo's `docs/design/<usecase>/` (acceptance-criteria, optional test-cases). Also
  update or validate an existing collection. Built-in **three-layer verify** (deterministic
  script + independent fresh-eyes agent + completeness sweep). Trigger on:
  "gen open collection", "สร้าง open collection", "สร้าง bruno จาก openapi spec",
  "อัปเดต bruno collection", "make a runnable collection from the openapi spec",
  "bruno from openapi", "gen scenario collection", "สร้าง bruno ตาม AC",
  "open collection ตาม doc AC", "AC-based bruno collection",
  "runnable test scenarios from AC". Also trigger when neo delegates collection generation.
  NOTE: generating the OpenAPI spec from Go is the `openapi-doc` skill; generating the AC /
  test-case design docs is the `neo` skill (this skill only *reads* them); publishing to
  Confluence is `confluence-api-doc`. Spec mode needs the `bruno/openapi.yaml` spec; AC-scenario
  mode also needs `docs/design/<usecase>/` — if a required input is missing, run the upstream
  skill first. Not a curl/Postman converter or an interactive editor.
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

Turn a `bruno/openapi.yaml` OpenAPI 3.1 spec into a **runnable** Bruno OpenCollection in one of two **source modes** (see `## Source mode`): **Spec** — one request `.yml` per endpoint, grouped by domain, plus `environments/` and `folder.yml`; or **AC-scenario** — one request per Ready AC with `runtime.assertions`. The spec is the **single source of truth** for the contract (already verified against Go by `openapi-doc`); the collection embeds **no `docs:`** blocks. The result is verified against the source on **evidence (a deterministic script) + an independent fresh-eyes pass + a completeness sweep**.

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

The `<collection-root>` is normally `bruno/` itself — the read-only `openapi.yaml` spec (this skill's source, written by `openapi-doc`) and its generated `openapi.deref.yaml` view both sit inside it alongside the `<group>/` folders; neither `openapi.*` file is a request. The directory mirrors the spec's path groups (operation `tags[0]` → `<group>/`). Path params appear two ways in a request — `:id` in `http.url` and `name:id type:path` in `params` (the native `{id}` form lives in the spec).

## Mode

Auto-detect (user can override): no `opencollection.yml` at the target → **Generate**; request says "validate/check/เช็ค/ตรงกับ doc ไหม" → **Validate**; otherwise → **Update**.

## Source mode

Orthogonal to **Mode** above, and **always chosen by asking** — never inferred silently. After the spec is confirmed to exist (Step 1), ask once via `AskUserQuestion` (header "Source mode"):
- **Spec** — one runnable request per endpoint (the full API surface).
- **AC-scenario** — one runnable request per Ready AC, carrying assertions (a test-scenario collection that joins the spec with neo's `docs/design/<usecase>/`).

**Smart default** — list the likely option first and mark it `(Recommended)`: the request says "ตาม AC / ตาม doc / scenario / AC-based", or names a usecase or a `docs/design/<usecase>/` folder → default **AC-scenario**; otherwise → default **Spec**.

**No `docs/design/` anywhere** → still ask, but the AC-scenario option's description must flag "needs `docs/design/<usecase>/` — run `neo` first", and the default stays **Spec**. If the user picks AC-scenario anyway → **STOP** and point to `neo`.

AC-scenario needs **both** the spec **and** `docs/design/<usecase>/acceptance-criteria.html` (required; `test-cases.html` = optional enrichment). After AC-scenario is chosen, if the usecase is ambiguous (several `docs/design/*/`, none named) → a second `AskUserQuestion` for the usecase. A required input missing → **STOP** (spec → `openapi-doc`; design docs → `neo`). Full join + file conventions: [`references/request-template.md`](references/request-template.md) **§8**.

---

## Step 1 · Locate the source + collection root + context
- **Source** — the **OpenAPI spec** at `bruno/openapi.yaml`; if it does not exist → **STOP** (run `openapi-doc` first). In a monorepo, scope to the chosen service's `bruno/openapi.yaml`.
- **Source mode** — with the spec confirmed, **ask now** via `AskUserQuestion` (see `## Source mode`): **Spec** or **AC-scenario**, smart-defaulted from the request. Resolve this before the collection root.
- **Collection root** (in order): explicit path from the user → walk **up** from cwd for an existing `opencollection.yml` → an existing collection dir (one that holds an `opencollection.yml`) under `bruno/` | `bruno-collection/` | `open-collection/` → else propose `<repo-root>/bruno/` and **confirm before writing**. **Never** point the collection root at the spec — `bruno/openapi.yaml` is the OpenAPI spec source (the `openapi-doc` output) this skill *reads*, not a collection it writes; it lives **inside** the collection root (`bruno/openapi.yaml` under `bruno/`, alongside its generated `openapi.deref.yaml` view), so set the root to `bruno/` — both `openapi.*` files are excluded from request collection, never emitted or treated as a request.
- Read `CLAUDE.md` / `AGENTS.md` / `README` for the service name (→ `info.name`), the dev port (→ `local` `baseUrl` — a small config peek, not a Go scan), and known environments (local/sit/uat/prod).
- **AC-scenario mode** — also resolve the **usecase dir** under `docs/design/` (explicit path → request names a usecase → the only `docs/design/*/` → else `AskUserQuestion`) and read its `acceptance-criteria.html` (+ `test-cases.html` if present). Collection root defaults to a **separate** `bruno-scenarios/` when a general `bruno/` collection already exists (the two collection shapes must not share one root) — **confirm before writing**.

## Step 2 · Read the source endpoints
Read [`references/request-template.md`](references/request-template.md) — **§0** (OpenAPI spec source). **Do not re-scan Go** — the spec was already verified against the code by `openapi-doc`.
- **OpenAPI spec source** — **prefer Bruno's native importer**: `bru import openapi --source bruno/openapi.yaml --output <collection-root> --collection-name "<Service Name>" --collection-format=opencollection` (it resolves the internal `$ref`s), then post-process to this skill's conventions (`{{baseUrl}}` env var, secret masking, `seq`, folder auth) and **strip any `docs:`** Bruno adds. If `bru` is unavailable, hand-map per **§0**: each operation → one request (`parameters` → `params`; `requestBody…examples.default.value` → `http.body.data` verbatim; `security` → auth; `servers[].url` → `{{baseUrl}}`).
- **AC-scenario mode** — ignore the importer; read [`references/request-template.md`](references/request-template.md) **§8** and hand-map per the AC→request join: parse the AC inventory (`<ac-card id status>`), pull each AC's endpoint + scenario body + expected outcome from a tracing `<tc-card>` when present (else derive from the AC prose), and resolve the endpoint contract against the spec. `bru import openapi` is endpoint-driven and **must not** be used here.

## Step 3 · Generate / Update / Validate
Write using [`references/request-template.md`](references/request-template.md) (per-file templates) + [`references/yaml-reference.md`](references/yaml-reference.md) (schema):
- **opencollection.yml** — `info.name` + ignore config. **No `docs:`.**
- **environments/** — one file per environment; `baseUrl` + a var per `{{name}}` referenced in any request; secret-looking names → `value: ""` + `secret: true` (never write a literal secret).
- **`<group>/folder.yml`** — display name, `seq` (10,20,30…), shared headers + auth derived from the operations' `security` (`inherit`/`none`/explicit).
- **`<group>/<endpoint>.yml`** — `info → http → settings` only. `http.body.data` is the operation's `requestBody…examples.default.value` JSON copied verbatim — never hand-assemble it from the schema. Omit `body` when the operation has no request body.
- **Update** — diff against existing files; touch the minimum; **preserve** any user-added `headers`/`auth`/env values (often hand-typed secrets); assign the next free `seq` for new requests.
- **Validate** — no writes; run the verify layers below as a pure check and produce a report.
- **AC-scenario mode** — per **Ready** AC write one `<usecase>/ac-<nnn>-<slug>.yml` (`info.name: "AC-NNN — <scenario>"`), section order `info → http → runtime → settings`: `http` from the resolved spec op, `body` from the TC `<req>` verbatim or the spec example adjusted to the AC, `runtime.assertions` = `res.status` (+ a stable `res.body.<code>` only when one exists) per §8.2. **Blocked** ACs → list + skip. **Update** keys files by AC-ID; a vanished AC-ID is flagged for removal, never auto-deleted if hand-edited.

### verify-L1 · Script tripwire (always)
```
# Spec mode
python3 <ASSET_DIR>/colcheck.py <collection-root> --spec bruno/openapi.yaml
# AC-scenario mode (--mode scenario is implied by --design)
python3 <ASSET_DIR>/colcheck.py <collection-root> --spec bruno/openapi.yaml --design docs/design/<usecase>
```
In **Spec mode** it mechanically checks spec↔collection coverage (missing/orphan request files, folder.yml per group), `http.method`/`http.url` vs the spec, `http.body.data` == the spec's runnable example, `http.url` path-params ↔ `params`, `body.data` JSON validity, `seq` uniqueness, and that every `{{var}}` is defined in `environments/`. In **AC-scenario mode** it instead checks **AC coverage** (every Ready AC has a request; no Blocked/orphan AC-ID), the `res.status` **assertion presence**, endpoint existence (N:1), plus the same path-param / JSON / env / seq checks — body↔example equality is **off** (scenario bodies vary by design → NOTE). Needs PyYAML. **Tripwire, not ground truth** — a flag means "inspect this".
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
SOURCE_MODE = <Spec | AC-scenario>

## Task
Independently verify the collection just written — in Spec mode against the bruno/openapi.yaml
spec; in AC-scenario mode against the AC docs + spec (per col-verifier.md's mode branch).
Check ONLY judgment-level accuracy (not the script's mechanical checks). Read the
source yourself.

## Files under review
<list the request .yml + folder.yml files just created/updated> + the bruno/openapi.yaml spec
+ (AC-scenario mode) docs/design/<usecase>/acceptance-criteria.html (+ test-cases.html)

## colcheck NOTEs to focus on
<paste every NOTE line from L1>

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
""")
```
`SKILL_DIR` is mandatory — without it the verifier cannot read its role file and fails silently. The verifier is read-only → **you** fix the files → re-run `colcheck.py`. Do not auto-redispatch; offer a second round (default yes), then escalate.

### verify-L3 · Completeness sweep (omission critic)
L1/L2 inspect what is present; L3 catches what is **missing entirely**. In **Spec mode** re-enumerate the **full inventory straight from the spec** (`bruno/openapi.yaml`: every operation in the root `paths:`) plus every `{{var}}` referenced, and confirm: every endpoint/operation has a request `.yml`, every group has a `folder.yml`, every referenced variable has an `environments/` entry, and no request file is an orphan. In **AC-scenario mode** re-enumerate the **AC inventory** instead (every Ready `<ac-card>` in `acceptance-criteria.html`) — confirm every Ready AC has a request, every Blocked AC is listed-and-skipped (never emitted), every referenced var has an env entry, and no request maps to an unknown AC. Report any whole endpoint/AC/group/variable the pipeline silently dropped; fix → re-run L1.

### Output
```
## Open Collection — <Generate / Update / Validate> · <Spec | AC-scenario>
**Collection:** <root>   **Source:** bruno/openapi.yaml spec  (+ docs/design/<usecase>/ in AC-scenario mode)
**Structure:** opencollection.yml · environments/(…) · <group>/(folder.yml + N requests) …
**Changes:** Created … / Updated … / Removed …
**Verification (three-layer):**
- L1 colcheck.py: ✅ PASS (0 ERROR) / ❌ ESCALATED (N ERROR after ~3 rounds) · loop rounds: 0-3
  · *(Spec)* coverage ✅ · method/path [X/Y] · body↔example [X/Y] · path-params ✅ · env vars ✅ · seq ✅
  · *(AC-scenario)* AC coverage [Ready R / matched M] · assertions [status X/Y · code Z] · skipped Blocked […] · body↔example off
- L2 fresh-eyes: ✅ Clean / ⚠️ N findings fixed / ⏭ Skipped / ⏸ Not run
- L3 completeness sweep: ✅ all endpoints/ACs/groups/vars covered / ⚠️ N silent omissions fixed
- Verdict: ✅ all green / ⚠️ warnings / ⏸ escalated
**Warnings:** false positives skipped, multipart/oauth flagged for manual review, remaining discrepancies
```

---

## What this skill is NOT
- **Not** a source generator — producing the `bruno/openapi.yaml` spec from Go is the **`openapi-doc`** skill (run it first; this skill reads its output).
- **Not** a Confluence publisher — that is the **`confluence-api-doc`** skill.
- **Not** a hand-authoring / curl-Postman-OpenAPI converter or interactive editor.
- **Not** a documentation carrier — the collection holds no `docs:`; the OpenAPI spec remains the single source of truth.
- **Not** a test-case generator — the AC / test-case design docs come from **`neo`**; **AC-scenario mode** only turns *existing* Ready ACs into runnable assertion-carrying requests (it reads `docs/design/<usecase>/`, never writes it).
