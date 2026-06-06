# Publish Reference — OpenCollection → Confluence

Heavy detail for the `api-doc` skill's **`publish`** command: auth, page-tree mapping, markdown→Confluence storage conversion, REST sync, and the two-layer verify (pre-flight `pubcheck.py` + round-trip). The SKILL.md `publish` section points here; it does not restate this.

**Principle:** one endpoint = one Confluence page, mirroring the collection's folder tree. Input is an **OpenCollection workspace only** (`opencollection.yml` at the root). Uses `acli` for auth + reads, and the Confluence REST API via `curl` for writes (acli only supports page *view*, not create/update).

```
<collection>/                          Confluence page tree
├── opencollection.yml  (docs:)   →    Parent page (overview + common errors)   ← NEW vs old skill
├── consent/
│   ├── folder.yml                →    Consent (domain group page)
│   ├── accept-consent.yml        →    POST: /api/v1/consents
│   └── revoke-consent.yml        →    DELETE: /api/v1/consents/:id/revoke
└── channel/
    ├── folder.yml                →    Channel (domain group page)
    └── create-channel.yml        →    POST: /api/v1/channels
```

---

## Step P1 — Gather inputs

1. **Source path** — a collection root containing `opencollection.yml`. If it is missing, STOP: `publish` only takes an OpenCollection workspace (run `gen` first).
2. **Parent page URL** — extract the numeric **page ID** from the URL (e.g. `…/pages/123456789/Title` → `123456789`).

## Step P2 — Auth + credentials

```bash
acli auth status
```
- Not installed → `brew install atlassian/tap/acli` (or https://developer.atlassian.com/cloud/acli/install/).
- Not authenticated → `acli auth login`.
- From the output extract **CONFLUENCE_URL** (`Site:` → `https://<site>`) and **EMAIL** (`Email:`).

Resolve the write token at Step P7 (REST needs it; reads use acli's oauth).

## Step P3 — Scan the collection

Skip `opencollection.yml` and `environments/`. For each group subdirectory:
- **Group display name** ← that folder's `folder.yml` `info.name`; fall back to the directory name → Title Case. Skip `health/`.
- For each `*.yml` request file (exclude `folder.yml`):
  - `info.type` must be `http` (skip + warn otherwise).
  - `http.method` (e.g. `POST`) and `http.url` — strip the leading `{{…}}` token (e.g. `{{baseUrl}}`) to get the path. Path params keep their `:id` form.
  - Page title = `<METHOD>: <path>` (e.g. `POST: /api/v1/consents`).
  - Page body = the request's `docs:` block (markdown).
- **Collection-root overview (the fix):** read `opencollection.yml`'s top-level `docs:` block — this is the **parent page** body (service overview + Common Error Responses). The old confluence-api-doc skill left the parent untouched; `publish` now syncs it.

### YAML extraction (pick the most reliable available)
1. `yq -r '.info.type' f.yml` … `yq -r '.docs' f.yml` (decodes block scalars cleanly) — preferred.
2. `python3 -c "import yaml,sys; print(yaml.safe_load(open(sys.argv[1]))['docs'])" f.yml` — fallback.
3. Manual: find `docs: |-` (or `|`,`>-`,`>`), take subsequent lines indented ≥2 spaces, dedent; stop at the first non-indented non-empty line.

Validate before converting: empty `docs:` → skip + warn; missing `http.method`/`http.url` → skip + warn.

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

## Step P6 — Convert markdown → Confluence storage (the risk area)

**Pre-processing (per page):** strip the H1 heading (it becomes the page title, not in-body). OpenCollection emits no breadcrumb, so there is none to strip. Decode the `docs:` block scalar and dedent to column 0 before parsing.

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

## Verify L1 — pre-flight (`pubcheck.py`), BEFORE any push

Stage each converted page in a **gitignored** scratch dir `.api-doc-publish/` as **two** artifacts — a `<page>.json` manifest for this pre-flight, and the raw storage at `storage/<page>.xml` so the L2 round-trip has a standalone file to diff later:
```
.api-doc-publish/<page>.json          {"title": "POST: /api/v1/consents", "source": "<the docs: markdown>", "storage": "<converted XHTML>"}
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
Group page ancestor = parent ID; endpoint page ancestor = its group page ID; parent page is updated by its own ID. HTTP 200 = accepted (but NOT proof the content is right — that is L2's job).

## Verify L2 — round-trip, AFTER push

For each pushed page, re-fetch the stored storage and compare to what we sent:
```bash
acli confluence page view --id <PAGE_ID> --body-format storage --json   # → .body.storage.value
```
Write the re-fetched value to `.api-doc-publish/refetched/<page>.xml`, then compare it against the staged storage file written in L1:
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
| no `opencollection.yml` at source | STOP — `publish` needs a collection; run `gen` first |
| request `.yml` unparseable / missing `info.type`/`http.method`/`http.url` | skip + list in warnings; don't abort |
| empty/missing `docs:` block | skip + warn (no content to publish) |
| HTTP 401 | check `$CONFLUENCE_API_TOKEN` / re-ask |
| HTTP 404 on a page | verify page ID (may be deleted) |
| HTTP 409 version conflict | re-fetch version with acli, retry |
| pre-flight ERROR | fix the conversion, re-stage, re-run — never push failed storage |
| round-trip CDATA drift | a code block was altered on store — investigate before declaring done |
