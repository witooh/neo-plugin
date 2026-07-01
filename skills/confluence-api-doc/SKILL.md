---
name: confluence-api-doc
description: >
  Publish API docs to Confluence — from the `docs/api/*.yaml` custom-YAML api-spec — one endpoint
  = one page under domain-group parent pages, with the service overview on the parent page.
  Assembles each page directly from the api-spec's doc-table shape, converts to Confluence storage, and syncs
  via acli (auth/reads) + REST (writes), with a
  built-in **three-layer verify**: a deterministic pre-flight + round-trip check, an
  independent fresh-eyes pass, and a completeness sweep. Trigger on: "publish api doc",
  "sync api doc", "push doc to confluence", "publish api spec to confluence",
  "อัปเดต api doc ไป confluence", "sync api spec to confluence". Also
  trigger when the using-neo Ship flow needs API-doc publishing. NOTE: the api-spec is authored by the
  `api-spec` skill; `openapi-doc` drift-checks Go against it; a runnable Bruno
  OpenCollection is the `open-collection` skill. Input is the
  `docs/api/*.yaml` api-spec — if it does not exist, run
  `/spec` first. Not a general Confluence editor.
compatibility:
  environment: claude-code
  tools:
    - Read
    - Glob
    - Grep
    - Bash
    - Write
    - Agent
    - AskUserQuestion
---

# Confluence API Doc

Publish API docs to **Confluence** — from the `docs/api/*.yaml` custom-YAML api-spec — one endpoint = one page, grouped under domain parents, with the service overview on the parent page. The full procedure (auth, source-select, page-tree mapping, the source→storage conversion rules, REST calls, round-trip normalization) is the single source in [`references/publish-reference.md`](references/publish-reference.md) — follow it; the steps below are the spine. Every push is gated on **deterministic checks (pre-flight + round-trip) + an independent fresh-eyes pass + a completeness sweep**, never on an HTTP 200.

`ASSET_DIR` = `<skill base dir>/assets`, `SKILL_DIR` = `<skill base dir>` (the skill-load message gives the "Base directory for this skill"). Input is the `docs/api/*.yaml` custom-YAML api-spec (authored by the `api-spec` skill).

## The spine

1. **Gather** — the source is the **api-spec** at `docs/api/*.yaml` (`_meta.yaml` + `<domain>/<endpoint>.yaml`); if it does not exist → STOP (run `/spec` to author it). Then take the Confluence parent-page URL → page ID.
2. **Auth** — `acli auth status` → `CONFLUENCE_URL` + `EMAIL`; resolve the write token (`$CONFLUENCE_API_TOKEN` or ask once) at push time.
3. **Scan** — endpoint pages titled `<METHOD>: <path>`, one per group; parent page = the service overview. Title from the endpoint's `method` + `path`; **assemble** the page body from the endpoint YAML — `description` → intro, `path_params`/`query_params`/`request_body.fields`/`responses[].fields` → field tables, `request_body.example` / `responses[].example` → example blocks, `business_logic` → its own section, `errors[]` → the Error Responses table; parent body = `_meta.overview` + `_meta.field_info` + `_meta.common_errors`. Skip `health/`. (Full rules: `publish-reference.md` § Step P3.)
4. **Map** — fetch existing children (`curl GET …?expand=space,children.page`), match by exact title, plan create/update; create groups before endpoints.
5. **Versions** — `acli confluence page view --id <id> --include-version --json`.
6. **Convert** — markdown → Confluence storage per `publish-reference.md` § P6 (code blocks → code macro/CDATA **first**, then inline rules; mind the nested-list rule). Stage each page in the **gitignored** `.api-doc-publish/` as both a `<page>.json` manifest and a raw `storage/<page>.xml` (the latter feeds the round-trip).

### verify-L1 · Deterministic (pre-flight + round-trip)
**L1a — pre-flight (before any push):**
```
python3 <ASSET_DIR>/pubcheck.py .api-doc-publish/
```
Well-formedness · CDATA/table/list balance · bare `&`/`<` · **source↔storage element counts**. Loop fix→re-stage→re-run until exit 0, OR ~3 rounds → escalate. **Never push storage that failed pre-flight.**

Then **Sync** (REST create/update: domain-group pages → endpoint pages → parent page; version+1 on update; skip unchanged).

**L1b — round-trip (after push):** re-fetch each page (`acli … --body-format storage --json`) and compare to the staged storage:
```
python3 <ASSET_DIR>/pubcheck.py --roundtrip .api-doc-publish/storage/<page>.xml .api-doc-publish/refetched/<page>.xml
```
Canonical compare (ignores Confluence's benign rewrites; CDATA must match exactly). Structural drift → review; **CDATA drift → a code example was mangled, investigate**. One round of fixes, then escalate.

### verify-L1.5 · Offer fresh-eyes (default yes)
Ask once via `AskUserQuestion`: *"Run an independent fresh-eyes verify of the published pages? (default: yes)"* — **no** → skip L2 (mark "skipped by user"); **yes** → L2.

### verify-L2 · Fresh-eyes verifier (independent agent)
The pre-flight + round-trip prove the storage is well-formed and survived Confluence verbatim; they cannot judge whether the **conversion preserved meaning**. Dispatch a verifier that reads a sample of (source markdown ↔ converted storage) pairs:
```
Agent(subagent_type: "general-purpose", description: "verify confluence publish", prompt: """
# Role: Publish Verifier
Read first: <SKILL_DIR>/references/pub-verifier.md
SKILL_DIR = <skill base dir>

## Task
Independently judge conversion fidelity for a sample of pages — semantic preservation
the pre-flight counts and round-trip cannot see. Read the source markdown + the staged
storage in .api-doc-publish/ yourself.

## Pages under review
<list a representative sample: the most table-heavy, code-heavy, and nested-list pages>

End with Status: DONE | DONE_WITH_CONCERNS | BLOCKED
""")
```
`SKILL_DIR` is mandatory. The verifier is read-only → **you** fix the conversion → re-stage → re-run L1a (and re-push + L1b if already pushed).

### verify-L3 · Completeness sweep (omission critic)
L1/L2 inspect the pages that *were* converted; L3 catches a whole page **missing entirely**. Re-enumerate every `docs/api/<domain>/<endpoint>.yaml` endpoint + every domain group, and confirm each maps to a created/updated Confluence page in the report, and that the parent overview (`_meta.overview`) was synced. Report any group/endpoint silently skipped; fix → re-sync.

### Output
```
## Confluence API Doc — publish
**Source:** docs/api api-spec   **Parent page:** <id>
| Page | Type | Page ID | Status |
| --- | --- | --- | --- |
| (Service) Overview | Parent | … | Updated (v3→v4) |
| Consent | Domain group | … | Created |
| POST: /api/v1/consents | API page | … | Created |
**Totals:** N groups, M API pages — created K / updated U / skipped S / failed F
**Verification (three-layer):**
- L1 pre-flight ✅/❌ · round-trip: N/M clean, D drift (CDATA drift: …)
- L2 fresh-eyes: ✅ Clean / ⚠️ N findings fixed / ⏭ Skipped / ⏸ Not run
- L3 completeness sweep: ✅ all pages synced / ⚠️ N silent omissions fixed
```

---

## What this skill is NOT
- **Not** a source generator — the `docs/api/*.yaml` api-spec is authored by the **`api-spec`** skill; **`openapi-doc`** only drift-checks Go against it. This skill reads the api-spec.
- **Not** a Bruno OpenCollection generator — that is the **`open-collection`** skill.
- **Not** a general Confluence page editor — it publishes the API-doc tree, nothing else.
- An HTTP 200 is **not** proof the content is right — that is the round-trip + fresh-eyes job.
