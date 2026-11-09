---
name: bruno
description: >-
  Authors, updates, validates and drift-checks the Bruno OpenCollection in a service repo's
  `bruno/`, the source of truth for every HTTP endpoint: each `<domain>/<endpoint>.yml` is a
  runnable request whose `docs:` markdown block holds the contract (field tables, error tables,
  examples). Six modes: Draft a contract from intent before code exists, Generate a collection,
  Update it (a requested delta or sync-back from built code), Validate it, report Go-vs-collection
  Drift, and Migrate a legacy `docs/api/*.yaml` spec into `bruno/`. Every mode ends in a
  three-layer verify (script, fresh-eyes, completeness sweep). Use when designing, authoring,
  updating, validating or drift-checking an HTTP API contract, or migrating `docs/api/`.
  Triggers: "สร้าง bruno", "อัปเดต bruno", "draft api", "เช็ค code ตรงกับ bruno ไหม",
  "api drift", "migrate docs/api", "validate bruno". Does not publish to Confluence, and is not
  an OpenAPI, Postman or curl converter.
---

# Bruno

The Bruno OpenCollection in the service repo's `bruno/` is the **source of truth** for every HTTP endpoint. One request file per endpoint holds the runnable request (`http`, a `runtime` status test) and the contract as a `docs:` Markdown block in a fixed layout. Every result rests on **evidence (a deterministic script) + an independent fresh-eyes pass + a completeness sweep**, never on the running agent's confidence.

`ASSET_DIR` = `<skill base dir>/assets`, `SKILL_DIR` = `<skill base dir>` (the skill-load message gives the "Base directory for this skill"). The scripts need PyYAML; run them as `python3 "$ASSET_DIR/<script>"`. Exit **2** with `<script>: needs PyYAML (pip install pyyaml)` means: install pyyaml or use an interpreter that has it, then re-run. Exit 2 is never a PASS and never a DRIFT.

## Audience (non-negotiable)

`docs:` is read by the teams that call this API (BFF, mobile, partner), not by the owning service's developers.

- Write the wire contract and caller-visible behaviour: wire names, types, Mandatory, examples, public error codes, rules a caller can observe.
- Never write ticket IDs (`GI-3467`), decision IDs (`D-07`), AC-IDs (`AC-001`), a `## Contract source` section, or repo-internal paths (`internal/…`, `docs/knowledge/…`, `handler.go:42`). Traceability lives in the ticket, the MR and the e2e test titles (`e2e-playwright`).
- `brunocheck.py` K10 ERRORs on those patterns. It NOTEs any `XX-NNNN` token not declared as an Error Code, because a regex cannot tell `GI-3467` from `ACC-1001`; L2 settles each NOTE.
- Full rules: [`references/docs-template.md`](references/docs-template.md) §Audience.

## Output location

```
bruno/
├── opencollection.yml       info.name + docs: (Overview, Field Information, Error Response Body, Common Error Responses)
├── environments/            local.yml · sit.yml
└── <domain>/
    ├── folder.yml           info{name, type: folder, seq} + request.auth/headers + optional docs:
    └── <endpoint>.yml       info → http → runtime → settings → docs
```

- **Collection root** (in order): an explicit path from the user → walk **up** from cwd for an `opencollection.yml` → `<repo-root>/bruno/`. In a monorepo, scope it to the chosen service. No `bruno/` yet → propose `<repo-root>/bruno/` and **confirm before creating it**.
- Read [`references/docs-template.md`](references/docs-template.md) (layout, table rules, full example) and [`references/yaml-reference.md`](references/yaml-reference.md) (Bruno keys) before writing any file.

## Mode

Selection order (the user can always override):

1. `docs/api/_meta.yaml` exists → **Migrate**. Confirm with the user before writing anything: every other mode would read a stale `bruno/`.
2. Request asks for a draft / design before code ("draft api", "ออกแบบ … ก่อน") → **Draft**
3. Request asks for drift / "does the code match" ("api drift", "เช็ค code ตรงกับ bruno ไหม") → **Drift**
4. Request asks to validate / check ("validate bruno") → **Validate**
5. No `bruno/opencollection.yml` → **Generate**
6. Otherwise → **Update**

| Mode | Writes | Input | L1 | L2 fresh-eyes | L3 completeness |
| --- | --- | --- | --- | --- | --- |
| Draft | yes | intent only (ticket, `docs/knowledge/`, user); never code; no `## Business Logic` | `brunocheck.py` | skipped | every AC that needs an endpoint has one |
| Generate | yes | intent + existing code | `brunocheck.py` | offered, default yes | every intended endpoint exists |
| Update | yes | requested delta, or built code (sync-back) | `brunocheck.py` | offered | no endpoint dropped |
| Validate | no | `bruno/` | `brunocheck.py` | offered | as Update |
| Drift | no | Go source + `bruno/` | `driftcheck.py` | offered | both route and request inventories compared |
| Migrate | yes, then removes `docs/api/` | `docs/api/` + existing `bruno/` | `migrate.py` round-trip, then `brunocheck.py` | offered, sampled | every `docs/api` endpoint has a request with `docs:` |

## Step 1 · Locate the input

- **Draft**: intent **only**: the originating ticket (issue tracker / a user-passed path / a spec file under `docs/`, `specs/` or `.scratch/`), `docs/knowledge/` (ingested by `markitdown`), the user's description. **Never read code**, even if some exists. No locatable requirement → STOP and ask; never invent an endpoint surface.
- **Generate**: the same intent sources plus existing handler and struct code to document. No locatable intent at all → STOP and ask.
- **Update**: the existing `bruno/` is the baseline. The delta is the change request, or for **Update-from-code** (sync-back) the built Go source, usually via a Drift report.
- **Validate**: `bruno/` only.
- **Drift**: Go source with `go.mod`, plus `bruno/`. Not Go → STOP (Go only; do not guess patterns). Monorepo (several `go.mod`) → ask which service, then scope both `--src` and the collection root to it.
- **Migrate**: `docs/api/` plus the existing `bruno/`, if any.
- Read `CLAUDE.md` / `AGENTS.md` / `README` for the service name (`info.name`), the dev port (the `local` environment's `baseUrl`) and the environments.

## Step 2 · Author (Draft / Generate / Update)

Write per [`docs-template.md`](references/docs-template.md) + [`yaml-reference.md`](references/yaml-reference.md):

- **`opencollection.yml`**: `info.name` + root `docs:` with `## Overview`, optional `## Field Information`, `## Error Response Body` (the common-lib body, documented once) and `## Common Error Responses` (may hold zero rows).
- **`environments/`**: `local.yml` and `sit.yml`; `baseUrl` + one variable per `{{name}}` used; secret-looking names get `value: ""` + `secret: true`.
- **`<domain>/folder.yml`**: `info{name, type: folder, seq}` (10, 20, 30…); auth and headers that every request in the folder shares, with each request on `auth: inherit`; optional domain prose in `docs:`.
- **`<domain>/<endpoint>.yml`**: `info → http → runtime → settings → docs`. `http.url` uses `:param` with a `type: path` row per param; `http.body.data` has the same key paths as the `docs:` Body Example; `runtime.scripts` holds a `type: tests` script asserting the first success status; `settings.encodeUrl: true`.
- **Error rows**: Status follows Response Code per the common-lib table. The common-lib body is never repeated per endpoint; `### Error Responses` lists only that endpoint's errors. A partner contract's error body gets its own `### HTTP Status: <4xx/5xx>` section.
- **Draft**: the structural contract only (Purpose, Request, Response, Error Responses). **No `## Business Logic`**: the flow is pinned once the handler exists, in Update-from-code. A draft is still runnable and still meets every K-rule.
- **Update**: touch the minimum. **Preserve** the user-authored runnable parts: `http.headers`, `http.auth`, `runtime` and environment values (often hand-typed secrets). Change only the `docs:` sections and the `http` method / url / params / body that the delta changes. A new request takes the highest `seq` in its folder + 10.
- **Validate / Drift**: write nothing.

## Step 2M · Migrate (confirmed first)

1. Confirm with the user (Mode, rule 1). Nothing is written before the answer.
2. Run `python3 "$ASSET_DIR/migrate.py" docs/api bruno`. It matches each legacy endpoint to a request by method + normalized path and rewrites only `docs:` and the top-level order of a matched request. `http` and `runtime` keep their text, except that a request with no `http.body` gets the legacy request example and one with no `type: tests` script gets the default status test. It creates missing requests and `folder.yml` files, writes the root `docs:`, prints `updated` / `created` / `orphans` / `warnings`, then runs the round-trip. It never deletes a file. Exit 2 → no `docs/api/_meta.yaml` or no endpoint loaded (check the argument order); nothing was written.
3. Exit 1 → each `MISMATCH` line names a legacy file whose field set or error rows differ after the round-trip, that holds a key migrate does not render (`key <k> not migrated`), or that is unreadable or not an endpoint.
4. Read every warning. Orphan requests and `openapi*.yaml` files are left untouched; a request without a status test needs one by hand. If the root `## Error Response Body` reads `Not documented in the source spec.`, the legacy spec held no evidence of the error body: a human must fill it in; never invent it. `brunocheck.py` only NOTEs that sentence (K11), so this check is yours.
5. Run L1 `brunocheck.py` (Step 3).
6. Fix loop until **both** scripts exit 0. Every MISMATCH, and every brunocheck ERROR in a part migrate writes (request, root and folder `docs:`), is a source defect: fix `docs/api/*.yaml`, then re-run the full `migrate.py docs/api bruno`; it overwrites a hand edit to `docs:`. Fix in `bruno/` only what migrate preserves: `http`, `runtime`, environments and orphan requests. `--check` re-runs only the round-trip and writes nothing.
7. Only when **both** `migrate.py` and `brunocheck.py` exit 0: `git rm -r docs/api` in the same change, so the legacy spec stays recoverable from git. On any red run, leave `docs/api/` in place. Committing stays with the user.

## Step 3 · Three-layer verify

### verify-L1 · Script tripwire (always)

```
python3 "$ASSET_DIR/brunocheck.py" bruno                   # Draft / Generate / Update / Validate / Migrate
python3 "$ASSET_DIR/driftcheck.py" bruno --src <go-root>   # Drift; <go-root> is where go.mod lives
```

`brunocheck.py` prints `✓`/`✗ <request>` per request, then `ERROR K<n> <file>: <msg>` and `NOTE K<n> <file>: <msg> — needs fresh-eyes` lines, then `PASS: 0 error(s)` or `FAIL: N error(s)`. Its rules K1-K11 are tagged in brackets in [`docs-template.md`](references/docs-template.md). `driftcheck.py` reads Go per [`references/go-scan-patterns.md`](references/go-scan-patterns.md), prints per-file `DRIFT` / `NOTE` lines, then `PASS` or `DRIFT FOUND`. It exits 2 when the collection root or the Go source is missing and says so: report that as "not compared", never as in sync. **Tripwire, not ground truth.**

- **exit 0** → go to L1.5 (Draft → L3).
- **exit 1** → for each ERROR / DRIFT, open the actual file, fix the real defect, re-run. **Loop until exit 0, OR ~3 rounds with no progress → STOP and escalate.** Never fake a green run.
- **exit 2** → there is no result yet; fix the cause and re-run. Causes: missing PyYAML (all three scripts); a wrong argument count (`brunocheck.py`, `migrate.py`); a missing collection root or Go source (`driftcheck.py`); a first argument that is not a directory, no `_meta.yaml` in it, or no endpoint loaded (`migrate.py`).
- **Drift direction**: the code is right and the collection is stale → reconcile `bruno/` in Update-from-code, then re-run `brunocheck.py` and `driftcheck.py`. The collection is the intended contract → the code gets fixed (or escalate). A request documented before its handler exists, or an intentionally-undocumented route, is confirmed + recorded under Warnings, never silently "fixed".
- Collect every `NOTE` line (each ends `needs fresh-eyes`): they feed L2.

### verify-L1.5 · Offer fresh-eyes (default yes)

Draft skips L1.5 and L2: the semantic pass is deferred to the Update-from-code that reconciles the draft against built code. Otherwise ask once via `AskUserQuestion`: *"Run an independent fresh-eyes verify? (default: yes)"*, **no** → skip L2 (mark "skipped by user"); **yes** → L2. Migrate samples: at least one request per domain, plus every request with a NOTE or a migrate warning.

### verify-L2 · Independent verifier

Spawn a read-only sub-agent that did **not** write the files. Generate / Update / Validate / Migrate:

```
# Role: Bruno Contract Verifier
Read first: <SKILL_DIR>/references/bruno-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the Bruno requests below against their source-of-intent. Check ONLY semantic
fidelity, auth/header mapping, runnable body vs docs:, and Audience fitness (not brunocheck.py's
mechanical checks). For each K10 NOTE, decide: ticket key or error code? Read the sources yourself.

## Files under review
<request .yml + folder.yml + opencollection.yml + environments/*.yml paths>

## Source-of-intent
<ticket/spec / docs/knowledge/ / code paths; for Migrate, docs/api/>

## brunocheck NOTEs to focus on
<paste every NOTE line from L1>

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
```

Drift:

```
# Role: Bruno Drift Verifier
Read first: <SKILL_DIR>/references/drift-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the drift report just produced. Check ONLY the judgment-level drift the
script degraded to NOTE (not its mechanical checks). Read the Go source AND bruno/ yourself.

## Under review
bruno/<domain>/*.yml vs the Go implementation at <go-root>: list the endpoints whose fields or
routes the script could not confidently compare.

## driftcheck NOTEs to focus on
<paste every NOTE line from L1>

## Project conventions
CLAUDE.md (the relevant section)

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
```

`SKILL_DIR` is mandatory: without it the verifier cannot read its role file and fails silently. The verifier is read-only (no write, edit, or commit) → **you** reconcile the files → re-run L1. Do not auto-redispatch; offer a second round (default yes), then escalate.

### verify-L3 · Completeness sweep (omission critic)

L1/L2 inspect what is present; L3 catches what is **missing entirely**. Re-enumerate the inventory yourself:

- **Draft**: every AC that needs an endpoint has a request.
- **Generate**: every intended endpoint has a request with `docs:`.
- **Update / Validate**: no endpoint dropped: the request list matches the intent, and `git status` shows no request deleted by accident.
- **Drift**: both inventories re-derived, the full route list from the router-setup file and the full request list from `bruno/`; every route and request was compared, and every "no confident struct match" reached L2. See the [Drift Verification Checklist](references/drift-verifier.md#drift-verification-checklist).
- **Migrate**: every `docs/api/<domain>/*.yaml` endpoint, and every `_meta.yaml` `extra_endpoints` row, has a request with `docs:`.

Report any whole endpoint the pipeline silently dropped; fix → re-run L1.

### Output

```
## Bruno: <Draft / Generate / Update / Validate / Drift / Migrate>
**Collection:** bruno/ (N requests, M folders)   **Input:** <intent / code / docs/api>
**Changes:** Created … / Updated … / Removed …  (Validate / Drift: none)
**Verification (three-layer):**
- L1 <brunocheck.py | driftcheck.py | migrate.py round-trip + brunocheck.py>: ✅ PASS / ⚠️ N drift / ❌ ESCALATED (N after ~3 rounds) · loop rounds: 0-3
- L2 fresh-eyes: ✅ Clean / ⚠️ N findings fixed / ⏭ Skipped / ⏸ Not run (Draft)
- L3 completeness sweep: ✅ all covered / ⚠️ N silent omissions fixed
- Verdict: ✅ in sync / ⚠️ gaps to reconcile / ⏸ escalated
**Warnings:** migrate warnings, endpoints documented before they are built, confirmed false positives, open questions for a human
```

---

## What this skill is NOT

- **Not** a publisher: Confluence publishing and syncing into the central `bruno-api-documents` repo are out of scope.
- **Not** an OpenAPI / Postman / curl converter. `bruno/openapi*.yaml` files are left untouched and reported.
- **Not** the e2e suite: the `runtime` status test is a smoke check; AC-driven HTTP tests are `e2e-playwright`.
- **Drift writes nothing**: reconciliation happens in Update-from-code. **Draft never reads code.**
- **Not** an editor for the legacy `docs/api/*.yaml` spec: Migrate converts it once, then removes it.
