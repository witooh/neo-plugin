# Publish Reference — api-spec → Confluence

Heavy detail for the `confluence-api-doc` skill: auth, page-tree mapping, page→Confluence storage conversion, REST sync, and the deterministic checks (pre-flight `pubcheck.py` + round-trip). The SKILL.md points here; it does not restate this.

**Principle:** one endpoint = one Confluence page, assembled directly from the api-spec. Input is the **`docs/api/*.yaml` custom-YAML api-spec** — `_meta.yaml` (service-level) + one `<domain>/<endpoint>.yaml` per endpoint (the `api-spec` skill authors it; `openapi-doc` drift-checks Go against it). The YAML is already in doc-table shape, so each endpoint file **assembles** into a logical page shape (§ Step P3), then is converted to storage (P6), checked by the deterministic checks, and read by fresh-eyes. Uses `acli` for auth + reads, and the Confluence REST API via `curl` for writes (acli only supports page *view*, not create/update).

```
docs/api/                       Confluence page tree
├── _meta.yaml             →    Parent page (overview · field info · common errors)
├── account/create.yaml    →    POST: /accounts/account
├── account/get.yaml       →    GET: /accounts/{accountId}
└── account/list.yaml      →    GET: /accounts
   (each endpoint's `domain` → its domain-group page)
```

---

## Step P1 — Gather inputs

1. **Source path** — the api-spec at `docs/api/*.yaml` (`_meta.yaml` + `<domain>/<endpoint>.yaml`); if absent, STOP (run `/spec` to author it).
2. **Parent page URL** — extract the numeric **page ID** from the URL (e.g. `…/pages/123456789/Title` → `123456789`).

## Step P2 — Auth + credentials

```bash
acli auth status
```
- Not installed → `brew install atlassian/tap/acli` (or https://developer.atlassian.com/cloud/acli/install/).
- Not authenticated → `acli auth login`.
- From the output extract **CONFLUENCE_URL** (`Site:` → `https://<site>`) and **EMAIL** (`Email:`).

Resolve the write token at Step P7 (REST needs it; reads use acli's oauth).

## Step P3 — Assemble pages from the api-spec

There is no pre-rendered markdown page — **assemble** each page's body from the endpoint YAML, then feed it to the P6 conversion. The custom YAML is already in doc-table shape (explicit field tables, `mandatory: M|O`, multi-flow business logic, per-endpoint errors), so this is a direct mapping — no `$ref` resolution, no extension hacks. Read each `docs/api/<domain>/<endpoint>.yaml` and build the page (sections **in this order** — the same shape the human-readable api-spec markdown uses; omit a section whose source key is absent):

- **Page title** = `<METHOD>: <path>` ← the endpoint's `method` (uppercased) + `path` (keeping the `{id}` form). **Group** = `domain`. (`endpoint` is the display name — it identifies the file/index, but the Confluence page is titled by method+path for stable create/update matching, so it is not repeated in-body.) Skip `health`.
- **Domain-group page** (one per `domain` — the endpoint pages' parent): title = `_meta.domains.<domain>.title` (fallback: `domain` in Title Case); body = `_meta.domains.<domain>.description` when present (else an empty container); order the groups by `_meta.domains.<domain>.seq`.
- **Page body** — a logical page shape P6 can convert (no in-body H1; the title is held separately):
  - intro paragraph ← `description`;
  - a **Method / Path / Auth** bullet list ← `method` / `path` / `auth`;
  - **Path Parameters** table ← `path_params`, then **Query Parameters** table ← `query_params` — columns Field / Description / Type / **Mandatory** (the explicit `mandatory: M|O`) / Example / Remark; a field carrying `object: <Name>` shows an empty Example + "See `<Name>` Object below";
  - **Request Body** table ← `request_body.fields`; **Request Example** ← `request_body.example` (a JSON code block);
  - for each item in **`responses`**: a **Response (`status` `description`)** table ← its `fields`, then a **`<Name>` Object** sub-table for each entry in `objects`, then a **Response Example** ← its `example` (JSON code block);
  - **Business Logic** ← `business_logic` (prose; preserve its multi-flow sub-headers / lists);
  - **Error Responses** table ← `errors` — columns Status / Error Code / Error Message / Description, but **include the Error Code or Error Message column only when some entry carries that key** (`code` and `message` are both optional — e.g. create uses `code`, get/list use `message`);
  - **Notes** ← `notes` (cross-cutting only; omit when empty).
- **Parent page body** ← `_meta.yaml`: a **Version / Base URL** line ← `version` / `base_url`; **Overview** ← `overview`; **Field Information** ← `field_info` (a `###` sub-section per key, each a Code / Description table); **Common Error Responses** table ← `common_errors` (Status / Code / Error Message / Description).

The api-spec is the single source — assemble faithfully (every field row, every M/O, every error; standard OpenAPI tooling is not involved). Validate before converting: an endpoint YAML with no `responses` → skip + warn.

## Step P4 — Map to the page tree

```bash
# direct children of the parent (also yields space.key)
curl -s "${CONFLUENCE_URL}/wiki/rest/api/content/${PARENT_PAGE_ID}?expand=space,children.page" -u "${EMAIL}:${API_TOKEN}"
# children of each domain-group page
curl -s "${CONFLUENCE_URL}/wiki/rest/api/content/${GROUP_PAGE_ID}/child/page" -u "${EMAIL}:${API_TOKEN}"
```
Extract `space.key` (→ `SPACE_KEY`, needed to create pages) and the `{id, title}` children. Match scanned pages to existing pages **by exact title**; unmatched → create. The **parent page** is matched by the given ID (not by title).

**Create ordering:** domain-group pages first (so their IDs exist), then endpoint pages under them.

## Step P5 — Current versions (for updates)

```bash
acli confluence page view --id <PAGE_ID> --include-version --json   # → version.number
```

## Step P6 — Convert the assembled page (markdown-shaped) → Confluence storage (the risk area)

**Pre-processing (per page):** the assembled body (from P3) is already markdown-shaped at column 0, with the page title held separately (not in-body) — parse the body as-is.

**CRITICAL — processing order matters:**

### Phase 1 — extract code blocks FIRST (before any other conversion)
For each fenced ```` ``` ```` block: capture the language + ALL lines between fences **verbatim**, and replace with the code macro:
```xml
<ac:structured-macro ac:name="code">
  <ac:parameter ac:name="language">LANG</ac:parameter>
  <ac:plain-text-body><![CDATA[...entire code verbatim...]]></ac:plain-text-body>
</ac:structured-macro>
```
- Content inside `<![CDATA[...]]>` is raw — **never** wrap in `<p>`/`<br/>`/any tag; preserve indentation + newlines exactly.
- Language map: `sh`→`bash`, `js`→`javascript`; others use the name. No language → omit the `<ac:parameter>` line.

### Phase 2 — convert the remaining (non-code) markdown
| Markdown | Storage |
|---|---|
| `**bold**` | `<strong>bold</strong>` |
| `*italic*` | `<em>italic</em>` |
| `[[text](url)]` | `<a href="url">text</a>` — **process before normal links** (type columns like `array[[Type](#x)]`) |
| `[text](url)` | `<a href="url">text</a>` |
| `## Heading` | `<h2>Heading</h2>` |
| `\| col \| col \|` table | `<table><tbody><tr><td>…</td></tr></tbody></table>` |
| blank-line-separated paragraph | `<p>text</p>` |
| `- item` / `* item` | `<ul><li>item</li></ul>` |
| `1. item` | `<ol><li>item</li></ol>` |
| `` `inline code` `` | `<code>inline code</code>` |
| `&`, `<`, `>` in text | escape as `&amp;` `&lt;` `&gt;` (outside code macros) |

**Nested list handling (the subtle bug):** when an ordered item has indented sub-bullets, the sub-list is a `<ul>` **inside** that `<li>`, and the `<li>` then closes. Subsequent numbered items continue as siblings in the **same parent `<ol>`** — do NOT nest them inside the previous item's sub-list.

Correct:
```html
<ol>
  <li>Validate collection point
    <ul><li>Check active status</li><li>Check purpose mapping</li></ul>
  </li>
  <li>Create consent record</li>
  <li>Return response</li>
</ol>
```

## Verify L1a — pre-flight (`pubcheck.py`), BEFORE any push

Stage each converted page in a **gitignored** scratch dir `.api-doc-publish/` as **two** artifacts — a `<page>.json` manifest for this pre-flight, and the raw storage at `storage/<page>.xml` so the L1b round-trip has a standalone file to diff later:
```
.api-doc-publish/<page>.json          {"title": "POST: /api/v1/consents", "source": "<the assembled page body>", "storage": "<converted XHTML>"}
.api-doc-publish/storage/<page>.xml   <converted XHTML>   (raw — byte-identical to the manifest's "storage")
```
Then run pre-flight on the manifests (the non-recursive glob ignores the `storage/` subdir, so each page is checked once):
```bash
python3 <ASSET_DIR>/pubcheck.py .api-doc-publish/
```
It checks: well-formedness · CDATA balance · code-macro integrity · table/list balance · bare `&`/`<` · non-empty title · **source↔storage element-count** (a markdown table that vanished from the storage = a broken conversion that would still POST 200). Loop: fix the conversion → re-stage → re-run until exit 0, **OR ~3 rounds stall → escalate** (never push storage that failed pre-flight).

## Step P7 — Sync via REST

Resolve the token: `echo $CONFLUENCE_API_TOKEN` (use silently if set; else ask once — https://id.atlassian.com/manage-profile/security/api-tokens). Use `EMAIL` from P2.

**Order:** (1) domain-group pages, (2) endpoint pages, (3) the parent page (overview + common errors). Skip a page whose normalized content is unchanged (avoid version churn).

```bash
# create
curl -s -X POST "${CONFLUENCE_URL}/wiki/rest/api/content" -u "${EMAIL}:${API_TOKEN}" \
  -H "Content-Type: application/json" -d '{"type":"page","title":"…","ancestors":[{"id":"…"}],"space":{"key":"…"},"body":{"storage":{"value":"…","representation":"storage"}}}'
# update (version = current + 1)
curl -s -X PUT "${CONFLUENCE_URL}/wiki/rest/api/content/${PAGE_ID}" -u "${EMAIL}:${API_TOKEN}" \
  -H "Content-Type: application/json" -d '{"version":{"number":N},"title":"…","type":"page","body":{"storage":{"value":"…","representation":"storage"}}}'
```
Group page ancestor = parent ID; endpoint page ancestor = its group page ID; parent page is updated by its own ID. HTTP 200 = accepted (but NOT proof the content is right — that is the round-trip's job).

## Verify L1b — round-trip, AFTER push

For each pushed page, re-fetch the stored storage and compare to what we sent:
```bash
acli confluence page view --id <PAGE_ID> --body-format storage --json   # → .body.storage.value
```
Write the re-fetched value to `.api-doc-publish/refetched/<page>.xml`, then compare it against the staged storage file written in L1a:
```bash
python3 <ASSET_DIR>/pubcheck.py --roundtrip .api-doc-publish/storage/<page>.xml .api-doc-publish/refetched/<page>.xml
```
`--roundtrip` **canonicalizes** both (drops the volatile attrs Confluence injects on store — `ac:macro-id`, `ac:schema-version`, `ac:local-id` — sorts attributes, collapses inter-tag whitespace) and compares **CDATA payloads exactly** (code must survive verbatim). A clean result is evidence the page rendered what we intended. Confluence rewrites storage benignly, so treat reported structural drift as "review this," not an automatic failure — but **CDATA drift is real** (a code example was mangled). One round of fixes, then escalate.

## Step P8 — Report

```
| Page Title | Type | Page ID | Status |
| --- | --- | --- | --- |
| (Service) Overview | Parent | 123456 | Updated (v3 → v4) |
| Consent | Domain group | 456789 | Updated (v2 → v3) |
| POST: /api/v1/consents | API page | 567890 | Created |
```
Then: N groups, M API pages (K created / U updated / S skipped / F failed); **pre-flight:** ✅/❌; **round-trip:** N/M clean, D drift.

## Error reference
| Scenario | Action |
|---|---|
| no `docs/api/*.yaml` at source | STOP — run `/spec` first to author the api-spec |
| an endpoint YAML with no `responses` | skip + list in warnings; don't abort |
| HTTP 401 | check `$CONFLUENCE_API_TOKEN` / re-ask |
| HTTP 404 on a page | verify page ID (may be deleted) |
| HTTP 409 version conflict | re-fetch version with acli, retry |
| pre-flight ERROR | fix the conversion, re-stage, re-run — never push failed storage |
| round-trip CDATA drift | a code block was altered on store — investigate before declaring done |
