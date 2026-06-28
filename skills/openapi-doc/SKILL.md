---
name: openapi-doc
description: >
  Verify Go source against the custom-YAML **API spec** at `docs/api/` and emit a
  **drift report** — the sync-back detector for the api-doc chain. The api-spec (authored
  spec-first by the api-spec skill) is the source of truth; this skill **writes nothing** — it
  scans the Go code and diffs it against `docs/api/<domain>/*.yaml` (routes, request/response
  fields, M/O, types), reporting every place the implementation has drifted from the contract so
  the api-spec skill can reconcile the spec. Built-in **three-layer verify** (deterministic script +
  independent fresh-eyes agent + completeness sweep). Trigger on: "check go against api-spec",
  "api drift", "api drift report", "verify code against the api-spec", "sync-back api",
  "did the code drift from the spec", "เช็ค code ตรงกับ api-spec ไหม", "หา drift api",
  "api-spec ตรงกับ code ไหม", "ตรวจ drift api spec", "เช็ค code กับ spec". Also trigger when
  neo delegates the api-spec drift / sync-back check. NOTE: this skill READS
  `docs/api/*.yaml` (authored by the **`api-spec`** skill) and the Go code and writes nothing —
  authoring the api-spec is the **`api-spec`** skill; a runnable Bruno OpenCollection is
  `open-collection`; publishing to Confluence is `confluence-api-doc`. It is not a spec
  generator, an OpenAPI converter, or an interactive editor.
compatibility:
  environment: claude-code
  tools:
    - Read
    - Glob
    - Grep
    - Bash
    - Agent
    - AskUserQuestion
---

# API-Spec Drift Checker (openapi-doc)

Scan the Go source and report where the implementation has **drifted** from the custom-YAML **API spec** at `docs/api/` — the spec-first **source of truth**, authored by the **`api-spec`** skill (`api-spec` → `references/api-spec-template.md`). This skill **writes nothing**: the api-spec is the contract, Go is what gets measured, and the output is a **drift report** the `api-spec` skill uses to reconcile the YAML (sync-back). Every report rests on **evidence (a deterministic script) + an independent fresh-eyes pass + a completeness sweep**, never on the running agent's confidence.

`ASSET_DIR` = `<skill base dir>/assets`, `SKILL_DIR` = `<skill base dir>` (the skill-load message gives the "Base directory for this skill"). Currently optimized for Go (Fiber, Echo, Chi, Gin).

## What it compares (Go ↔ `docs/api/*.yaml`)

- **Routes** — every Go route (method + path) is documented by a spec endpoint, and every spec endpoint is implemented by a Go route. `_meta.yaml`'s `extra_endpoints` (e.g. a health probe with no spec file) count as documented.
- **Fields** — per matched endpoint, the spec's `request_body.fields` and each `responses[].objects.<Name>` are diffed against the Go struct (reverse-matched by json names): an **undocumented** Go field (serializable, no spec row), a **stale** spec field (no Go field), an **M/O** disagreement (`mandatory: M|O` vs the struct tags), and a confident **type** disagreement (`bool`/`[]T`/numeric vs `Boolean`/`Array`/`Number`).
- A difference the script cannot decide confidently (no struct match, the response envelope wrapper, handler-inline query/path params, error-status tracing) becomes a **NOTE** for the fresh-eyes pass — never a false drift.

## Required input

- **`docs/api/*.yaml`** — the api-spec must already exist. **Missing → STOP**: "no api-spec at `docs/api/` — run `/api-spec` to author it first." This skill never creates it.
- **Go source with `go.mod`.** Not a Go project (no `go.mod`, no `references/<lang>-scan-patterns.md`) → **STOP** (Go only; do not guess patterns). **Monorepo** (multiple `go.mod`) → ask which service, then scope `--src` *and* the `docs/api/` path to that one service.

## Step 1 · Locate the spec + Go root
- **Spec dir** — default `docs/api/` at the repo root; in a monorepo scope it to the chosen service (e.g. `services/<name>/docs/api/`).
- **Go root** (`--src`) — where `go.mod` lives (usually `.`).
- Read `CLAUDE.md` / `AGENTS.md` / `README` for service name, framework, and the route-base (`/api/v1/`) pattern — the drift check matches paths base-URL-suffix-tolerantly, so a `servers`-style prefix in the route is fine.

## Step 2 · Run the drift check

### verify-L1 · Script tripwire (always)
```
python3 <ASSET_DIR>/speccheck.py docs/api --src <project-root>
```
It reads the Go source + every `docs/api/<domain>/*.yaml` and mechanically checks **route coverage (both directions)** and **per-field presence / M-O / type** on confidently-matched endpoints. **Tripwire, not ground truth** — a `DRIFT` line means "inspect this".
- **exit 0** → no confident drift → go to L1.5.
- **exit 1** → for each `DRIFT`, open the actual struct / route / spec file and decide the **sync-back direction**: the spec is the intended contract and the code drifted → **reconcile the code** (or escalate); the code is correct and the spec is stale → the **`api-spec` skill reconciles `docs/api/<...>.yaml`** (re-run `apispeccheck.py` after) — then re-run this check. A genuine **false positive** — a spec-first endpoint not built yet, or an intentionally-undocumented route — is **confirmed + recorded under Warnings**, never silently "fixed". **Loop until exit 0, OR ~3 rounds with no progress → STOP and escalate** with the remaining drift. (This skill writes nothing — when run inside `neo`, the `api-spec` skill applies the YAML reconciliation; standalone, surface the report and let the author apply it.)
- Collect every **`NOTE`** line (each ends `needs fresh-eyes`) — they feed L2; NOTEs don't fail the run.

### verify-L1.5 · Offer fresh-eyes (default yes)
Ask once via `AskUserQuestion`: *"Run an independent fresh-eyes verify of the drift report? (default: yes)"* — **no** → skip L2 (mark "skipped by user"); **yes** → L2.

### verify-L2 · Fresh-eyes drift verifier (independent agent)
Dispatch a verifier that re-reads the Go source **and** the api-spec independently and judges only the drift the script could not decide (the `NOTE` spots): unconfident struct matches, the response envelope, inline query/path params, custom-type fields, and **error-status tracing** (is each spec `errors[]` row backed by a Go sentinel, and every traced sentinel documented? — `go-scan-patterns.md §Error Tracing`):
```
Agent(subagent_type: "general-purpose", description: "verify api-spec drift", prompt: """
# Role: API-Spec Drift Verifier
Read first: <SKILL_DIR>/references/openapi-doc-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently verify the drift report just produced. Check ONLY the judgment-level drift the
script degraded to NOTE (not its mechanical checks). Read the Go source AND docs/api/*.yaml yourself.

## Under review
docs/api/<domain>/*.yaml (the spec) vs the Go implementation — list the endpoints whose
fields/routes the script could not confidently compare.

## speccheck NOTEs to focus on
<paste every NOTE line from L1>

## Project conventions
CLAUDE.md (the relevant section)

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
""")
```
`SKILL_DIR` is mandatory — without it the verifier cannot read its role file and fails silently. The verifier is read-only → it reports drift findings; **reconciliation of `docs/api/*.yaml` is the `api-spec` skill's** (re-run `speccheck.py` to confirm nothing regressed). Do not auto-redispatch; if findings are deep, offer a second fresh-eyes round (default yes), then escalate.

### verify-L3 · Completeness sweep (omission critic)
L1/L2 inspect endpoints they *matched*; L3 catches what was **silently un-compared** on either side. Re-derive **both inventories yourself** — the full route list straight from the router-setup file, and the full endpoint-file list from `docs/api/` — then confirm:
- every registered route (minus `extra_endpoints` / intentionally-undocumented) has a `docs/api/<domain>/*.yaml` endpoint,
- every endpoint file maps to a real route (no orphan / spec-first-pending left unconfirmed),
- every endpoint the script reported as "no confident struct match" was actually reached by the fresh-eyes pass.
Report any whole route/endpoint the pipeline silently skipped; reconcile → re-run L1 to confirm.

### Output
```
## API-Spec Drift — <docs/api vs Go>
**Spec:** docs/api/ (N endpoints)   **Code:** <project-root> (M routes)
**Drift (by direction):** undocumented routes … / unimplemented endpoints … / field presence … / M-O … / type …
**Verification (three-layer):**
- L1 speccheck.py: ✅ PASS (0 drift) / ⚠️ N drift (sync-back needed) / ❌ ESCALATED (after ~3 rounds) · loop rounds: 0-3
  · route coverage ✅/[N] · field presence [N] · M/O [N] · type [N]
- L2 fresh-eyes: ✅ Clean / ⚠️ N findings / ⏭ Skipped / ⏸ Not run
- L3 completeness sweep: ✅ all routes + endpoints compared / ⚠️ N silent omissions
- Verdict: ✅ in sync / ⚠️ drift to reconcile / ⏸ escalated
**Reconciliation:** what the `api-spec` skill should change in docs/api/*.yaml (or in the code), per drift
**Warnings:** confirmed false positives skipped (spec-first-pending / intentionally-undocumented), unresolved matches
```

---

## What this skill is NOT
- **Not** a spec generator or editor — the api-spec at `docs/api/` is authored by the **`api-spec`** skill; this skill only **reads** it (and the Go code) and reports drift. It writes no file.
- **Not** a Bruno OpenCollection generator (**`open-collection`**) or a Confluence publisher (**`confluence-api-doc`**) — both also read `docs/api/*.yaml`.
- **Not** an OpenAPI / curl / Postman converter. (There is no `bruno/openapi.yaml` in this chain anymore — the custom-YAML api-spec is the single source of truth.)
- The verify script is a **tripwire**: a `DRIFT` means inspect + reconcile, a `NOTE` means a fresh-eyes call. Full coverage comes from L1 (mechanical) + L2 (judgment) + L3 (completeness) together — see the [Drift Verification Checklist](references/openapi-doc-template.md#drift-verification-checklist).

## Expanding to other languages
Add `references/<language>-scan-patterns.md` (route/handler/usecase + struct patterns), teach Step 1 to detect the language (`package.json` → Node, etc.); the drift rules + verify are unchanged.
