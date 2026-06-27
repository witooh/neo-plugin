# HTML Output Guide (shared by Business Analyst, Architect, QA)

All **design documents** in `docs/design/` are emitted as **interactive HTML**, not markdown. This guide is the single source of truth for HOW to produce them. Read it before generating or editing any design doc. Your role reference (`business-analyst.md` / `architect.md` / `qa.md`) defines WHAT content goes in each doc; this file defines the HTML form, the shared design system, and the verify step.

> **Why HTML:** humans don't read dense markdown. The HTML site is visual + interactive (collapsible cards, filters, sortable tables, dark/light, mermaid diagrams, clickable traceability). CSS/JS are **external** (shared `assets/`), so a page's HTML is lean semantic content — an AI/tool reading a doc reads only the content, not the styling (token cost ≈ markdown).

---

## 1. The design system (bundled with this skill)

The skill carries the canonical design system in its `assets/` directory. The Orchestrator passes you its absolute path as **`ASSET_DIR`** (e.g. `…/skills/neo/assets`). It contains:

| File | Role |
|------|------|
| `css/styles.css` | design tokens + every component + light/dark (keyed off `[data-theme]`) |
| `js/app.js` | theme toggle, sidebar render (`renderNav`), scroll-spy TOC, filters, tabs, collapsible cards, copy + JSON highlight, sortable tables, trace-matrix, mermaid init |
| `js/components.js` | defines the **`<ac-card>`** + **`<tc-card>`** + **`<callout-box>`** + **`<card-flow>`** + **`<status-badge>`** custom elements — expand compact authoring markup into the canonical `.card` / `.callout` / `.flow` / `.status-badge` — plus **`<trace-matrix>`** + **`<ac-summary>`** + **`<tc-summary>`** + **`<tc-deferred>`** + the **`<ac-total>`** / **`<tc-total>`** count lines, which derive the matrix / summary / deferred / totals from the page's `<ac-card>`/`<tc-card>`s. Classic script; loads BETWEEN `nav.js` and `app.js` (see §3). |
| `js/nav.js` | per-project sidebar registry template (`window.DOCS_NAV`) |
| `_shell.html` | the page skeleton template (placeholders) |
| `components.html` | **living style guide** — every component with a copy-paste HTML pattern + when-to-use |
| `lint.py` | structural HTML linter — per-file (your verify gate) |
| `docverify.py` | cross-document linter — resolves references BETWEEN docs (AC↔test-case traces, coverage, status/JIRA propagation) + execution evidence (every Ready AC has a PASSING test in `test-report.html` — X6) |
| `scaffold.sh` | idempotent installer that stamps the above into a project |

**mermaid** is loaded from a pinned CDN (no vendoring): `https://cdn.jsdelivr.net/npm/mermaid@11.4.1/dist/mermaid.min.js`.

---

## 2. First-gen: stamp the design system into the project

The very first HTML doc generated in a project needs the design system present in `docs/design/`. Before writing your first page, check and stamp:

```
# if docs/design/assets/ is missing → stamp it
bash <ASSET_DIR>/scaffold.sh <project>/docs/design
```

`scaffold.sh` is **idempotent and safe to run every time**: it always refreshes the framework files (`styles.css`, `app.js`, `components.js`, `components.html`) but **never overwrites `nav.js`** (which holds this project's navigation). It creates:

```
docs/design/
├── assets/css/styles.css
├── assets/js/app.js
├── assets/js/components.js  ← defines <ac-card>/<tc-card>/… custom elements (loads before app.js)
├── assets/js/nav.js        ← edit this to register usecases (see §4)
└── components.html         ← live style guide (viewable in-project)
```

> BA has `Bash` for this. Architect writes via Bash too. QA has Bash. If you genuinely cannot run Bash, copy the same files from `<ASSET_DIR>` with Read+Write (framework files always, `nav.js` only if absent).

On first stamp, open `docs/design/assets/js/nav.js` and set `DOCS_BRAND.sub` to the project name (replace the `"<project>"` placeholder). **After running `scaffold.sh`, always `Read` `docs/design/assets/js/nav.js` before `Edit`** — scaffold just created a new file the tool hasn't tracked yet (otherwise Edit fails with "file has not been read yet").

---

## 3. Build a page from `_shell.html`

Every page starts from `<ASSET_DIR>/_shell.html`. Read it, copy the skeleton, and replace the placeholders:

| Placeholder | Fill with |
|-------------|-----------|
| `{{LANG}}` | `th` (or project language) |
| `{{ASSET_PREFIX}}` | relative path from THIS page up to `docs/design/` (see depth table). Use the SAME value in the `<link>`, both `<script src>`, and `data-asset-prefix`. |
| `{{DOC_TITLE}}` | `<title>` text, e.g. `Acceptance Criteria · <Usecase> — Design Docs` |
| `{{TOPBAR_TITLE}}` | short mobile label, e.g. `Acceptance Criteria` |
| `{{DOC_HEADER}}` | the `<header class="doc-header">` block (crumbs + `h1` + `.lede` + `.doc-meta`) |
| `{{CONTENT}}` | the page body, built from components (§5) |

**ASSET_PREFIX by depth** (load-bearing — wrong prefix = broken CSS/JS):

| Page location | `ASSET_PREFIX` |
|---------------|----------------|
| `docs/design/index.html` | `` (empty) |
| `docs/design/{usecase}/*.html` | `../` |
| `docs/design/system-design/*.html` | `../` |

The sidebar `<aside class="sidebar">` is left **EMPTY** — do not fill it (see §4). Keep the script load order exactly: **mermaid CDN → nav.js → components.js → app.js** (`components.js` MUST load before `app.js` so `<ac-card>`/`<tc-card>` upgrade before app.js scans — see §1). Keep the FOUC inline script key as `ds-theme`.

> `_shell.html` is a template — never copy `_shell.html` itself into `docs/design/`; only copy the *filled* result to its real page path.

---

## 4. Sidebar = `nav.js` only (never hardcode)

`app.js` builds the sidebar on every page from `window.DOCS_NAV` in `docs/design/assets/js/nav.js`, prepending each page's `data-asset-prefix`. **Do not hardcode `.nav-group` markup into pages.**

To register a usecase, append ONE group to `DOCS_NAV` (hrefs are root-relative to `docs/design/`):

```js
{ group: "<Usecase Name>", links: [
  { href: "<usecase>/index.html",               label: "Overview",            ico: "▸" },
  { href: "<usecase>/acceptance-criteria.html", label: "Acceptance Criteria", ico: "✓" },
  { href: "<usecase>/test-cases.html",          label: "Test Cases",          ico: "⚗" },
  { href: "<usecase>/traceability.html",        label: "Traceability",        ico: "⛓" }
]},
```

*(The API spec is **not** in this sidebar — it lives in the separate global tree `docs/api/`, see `templates/api-spec.md`.)*

Add only links for docs that exist (or will exist this run). BA owns the usecase group when creating the usecase; Architect/QA add their doc's link if BA didn't.

---

## 5. Section → component mapping

Build `{{CONTENT}}` from these components. `docs/design/components.html` is the **live, copy-paste reference** for every one — open it when unsure. Verified mapping:

| Doc element | Component / markup |
|-------------|--------------------|
| Each **AC** | **`<ac-card>`** custom element (see exemplar below): `<ac-card id="AC-NNN" status priority traces subop jira label>` + child `<g>/<w>/<t>` (+ `<a>`), `<rule>`, optional `<blocker>`. Expands to the canonical `.card` with badge / chips / chevron / GWT-labels / field-rows all **derived** (status written once → can't drift). |
| Each **Test Case** | **`<tc-card>`** custom element (see exemplar below): `<tc-card id="TC-NNN" status priority traces jira endpoint label>` + child `<g>/<a>/<w>/<t>` (G-A-W-T order), `<req>`/`<res>` (JSON), `<steps><step>…`, `<expected>`/`<tdata>`/`<precond>`, optional `<blocker>`. Expands to the canonical `.card` with badge / chips / chevron / GWT-labels / field-rows / Request-Response `.tabs` all **derived** (status written once → can't drift; `data-tags="blocked"` + the AC-Status row appear automatically for blocked TCs). |
| Given/When/Then | `.gwt` > `.gwt__k[data-k="given\|when\|then\|and"]` + `.gwt__v` |
| **Business Rule, Priority/Status** (inside a card) | **`dl.field-row` > `dt` + `dd`** — NOT a callout |
| AC Summary table | **`<ac-summary>`** > **`<ac ref subop rule [blocker]>`** per AC — derives Scenario/Priority/Status/JIRA from the matching `<ac-card>` (can't drift); author supplies the `subop` name + `rule` short-ref. Renders `.table-wrap > table.data-table[data-sortable]`. |
| TC Summary table | **`<tc-summary>`** > **`<tc ref suite precond>`** per TC — derives Description(=`label`)/Traces/JIRA/Status from the matching `<tc-card>` (can't drift); author supplies `suite` (→"—") + `precond` (→"None"). Renders `.table-wrap > table.data-table[data-sortable]`. |
| Deferred Test Cases table | **`<tc-deferred>`** > **`<tc ref blocker upstream>`** (blocked TCs only) — derives TC-ID/Traces/JIRA from the card; author supplies the `blocker` reason + `upstream` ref. Renders `.table-wrap > table.data-table[data-sortable]`. |
| AC / TC "Total …" line | **`<ac-total></ac-total>`** / **`<tc-total></tc-total>`** (empty) — counts the page's `<ac-card>`/`<tc-card>`s by status → "Total …: N (Ready: R / Blocked: B)" (can't go stale). Renders `.doc-total`. |
| Status pill | **`<status-badge status="ready\|blocked\|pending">`** — label derived from `status` (capitalized; can't drift from `data-status`). Non-empty content overrides the label (e.g. `<status-badge status="blocked">Deferred</status-badge>`). |
| Priority / JIRA / tag | `span.chip[data-tone="p0\|p1\|jira"]` — **only `p0`, `p1`, `jira` tones exist**; P2 (or any other tag) = plain `span.chip` (no `data-tone`) |
| Blocker / note / scope / warning | **`<callout-box kind="note\|success\|warning\|pending\|blocked">`** prose `</callout-box>` (optional `ico=` overrides the glyph) — derives `.callout__ico` (icon from kind, can't drift) + wraps `.callout__body`. *(Cards emit their own blocked callout; this element is for hand-authored callouts.)* **FIRST apply §5.1 — most "notes" (changelog / doc-vs-code gap) do NOT belong on the page; `docverify.py` fails the gate on them.** |
| JSON request/response | `div.code[data-lang="json"]` > `pre` > `code`; group request/200/error in `.tabs` (`.tabs__nav` > `.tab[data-tab]`) + `.tab-panel[data-tab]` |
| API error table | `table.data-table[data-sortable]` |
| Gate / validation chain | **`<card-flow>`** > `<step status="ready\|blocked" href tag detail>title</step>` — derives `.flow__step.is-<status>` + the **step number** (auto) + the **`.flow__arrow` between** steps (auto). |
| Diagram (sequence/flow/ER) | `div.diagram` > optional `.diagram__cap` + `div.mermaid` (raw mermaid source) |
| Traceability matrix | **`<trace-matrix></trace-matrix>`** (empty) — derives the whole matrix from the page's `<ac-card>`s: one row per AC (`tbody th` = AC id, click-highlights row), a `.chip` per traced TC, and the AC's `.status-badge`, all from card `id`/`traces`/`status` (**can't drift**). Renders `.matrix-wrap > table.trace-matrix`. |
| Coverage stats | `.stat-grid` > `.stat-card` (+ `.bar` > `.bar__seg.ready\|.blocked`) |
| Landing / nav cards | `.card-grid` > `a.link-card` |
| Page chrome (from `_shell`) | `.topbar`, `.nav-scrim`, `.layout`, `.doc-header`(`.crumbs`, `h1`, `.lede`, `.doc-meta` > `.meta-chip`), `.toc` |

**Filtering:** wrap a card list and add `.filter-bar[data-target="#list > .card"]` with `.pill[data-group][data-value]` + a `<input type="search">`. Items filter on their `data-<group>` attributes (space-separated multi-values supported, e.g. `data-traces`).

**AC-card exemplar** — author the compact `<ac-card>`; the element derives the head (status badge, priority/JIRA chips, chevron), the GWT labels, and the Business Rule / JIRA Ref / Priority-Status field-rows. Prose goes in `<g>/<w>/<t>` children where inline `<b>`/`<code>` are real markup (**no `&lt;` escaping needed there**) — but **bare `&` still → `&amp;`** (see §6). Optional `<blocker>…</blocker>` renders a blocked `.callout`.

```html
<ac-card id="AC-001" status="ready" priority="p0" traces="TC-001" jira="GI-90" label="happy path">
  <g>initial condition</g>
  <w>the event that occurs</w>
  <t>system responds HTTP <b>200</b></t>
  <rule>BR-01 — …</rule>
</ac-card>
```

Renders to the canonical `div.card.is-ready` > `.card__head`(`.card__id` + `.card__title` + `.card__meta`(`.status-badge` + `.chip` + `.card__chev`)) + `.card__body`(`.gwt` + `dl.field-row`×N [+ `.callout` if `<blocker>`]).

**TC-card exemplar** — author the compact `<tc-card>`; the element derives the same head + field-rows as `<ac-card>`, plus the Endpoint row, the Request/Response `.tabs` (a single `.code` when only one JSON is given), and the Test Steps `<ol>`. **Write GWT children in G-A-W-T order** (`<a>` = AND); `<req>/<res>/<steps>/<expected>/<tdata>/<precond>/<blocker>` are all optional. Inline `<b>`/`<code>` are real markup inside prose children (**no `&lt;` escaping**), but JSON inside `<req>/<res>` and any **bare `&` still → `&amp;`** (see §6).

```html
<tc-card id="TC-002" status="ready" priority="p1" traces="AC-002"
         jira="PROJ-123, PROJ-456" endpoint="POST /v1/accounts" label="open account">
  <g>a bank offers a savings product</g>
  <a>the primary denomination is configured as THB</a>
  <w>an account is opened with denomination = THB</w>
  <t>the account is opened successfully in Vault</t>
  <req>{ "product_id": "PROD-001", "denomination": "THB" }</req>
  <res>HTTP 200
{ "account_id": "ACC-001", "status": "OPEN" }</res>
  <steps><step>call <code>POST /v1/accounts</code></step><step>assert status = 200</step></steps>
  <expected>HTTP 200, account status = OPEN</expected>
  <tdata><code>denomination: "THB"</code></tdata>
  <precond>TC-001 must pass</precond>
</tc-card>
```

A **blocked** TC adds `status="blocked"` + a `<blocker>…</blocker>` child; the element then derives `data-tags="blocked"`, an **AC Status: Blocked** field-row, and a blocked `.callout` — you never write those by hand.

---

## 5.1 Callout discipline — most "notes" do NOT belong on the page (READ before authoring any `<callout-box>`)

A design doc states the **current desired state** — what the system *should* be, now. It is **not** a changelog and **not** a doc-vs-code drift log. Before you hand-author a `<callout-box>`, route its content:

| The note is… | Where it goes | On the HTML page? |
|--------------|---------------|-------------------|
| a **version / changelog** entry ("v1.4.0 — re-aligned…", "now Ready since GI-117") | `VERSION.md` + the Version History table in `index.html` (§9) | **NO** — `docverify.py` fails the gate (C1) |
| **code doesn't match the spec** (gap / drift / "pending because the field isn't in code yet" / "verified against `X` — not implemented") | `gap-analysis.md` (§8) **and** report it in your chat output back to the orchestrator | **NO** — `docverify.py` fails the gate (C2) |
| **spec-relevant, tied to ONE element** (an error-code taxonomy for an error-responses section, a field's mapping rule) | **fold it INTO that element** — a `dl.field-row`, a table row/cell, or a sentence in that section. Not a callout. | yes, as content |
| **spec-relevant, cross-cutting** (an orchestrator boundary, an out-of-scope statement) | a single **`<h2 id="notes">Notes</h2>` + `<ul>`** at the end of the page | yes, in the Notes section only |

The `id="notes"` is load-bearing: `docverify.py` exempts callouts inside that region (a cross-cutting note placed there is correct routing), and the density check (C3, warns at >6) counts only callouts **outside** it. A card's own `<blocker>` callout is element-emitted (not hand-authored) and is never counted. **Net rule:** if a `<callout-box>` survives this routing, it is a genuine cross-cutting spec note → it lives in the Notes section, nowhere else.

---

## 6. HTML-safety rules (so lint passes) — READ THIS

The linter flags raw `<` as an "unknown tag" and a bare `&` as a non-entity. In **prose / text content** you MUST escape:

- `<` → `&lt;`   `>` → `&gt;`   (e.g. `count &lt; userCap`, `field &lt;name&gt; is required`)
- bare `&` → `&amp;` (e.g. `Terms &amp; Conditions`)

Other invariants:
- **Every `.card` MUST have a `data-status`** (filters + coverage break silently otherwise). For **`<ac-card>` / `<tc-card>`** write `status=` instead — the element derives `data-status` from it (lint warns if missing). Inside prose children (`<g>/<w>/<t>/<rule>`, and TC's `<expected>/<tdata>/<precond>/<step>`) real inline tags (`<b>`, `<code>`) are fine — no `&lt;` escaping there — but **bare `&` is still `&amp;`** everywhere.
- **JSON inside `<req>/<res>` is text** — escape `<`/`>`/`&` (`&lt;`/`&gt;`/`&amp;`) just like prose. The element re-emits it into `<pre><code>`; app.js then highlights and copies the **decoded raw JSON** (the escape round-trips correctly).
- **Raw mermaid source goes ONLY inside `div.mermaid`** — the linter skips that region. Don't put HTML tags inside mermaid labels; for a line break use `&lt;br/&gt;`.
- Keep block tags balanced (`div`/`section`/`table`/`a`/`span`/`code`/…). A dropped `</div>` is the most common lint failure.

---

## 7. Verify (ALWAYS — this is your gate)

After writing or editing ANY page, run BOTH bundled linters and fix until clean:

```
python3 <ASSET_DIR>/lint.py docs/design                 # per-file structure
python3 <ASSET_DIR>/docverify.py docs/design/<usecase>  # cross-document refs + (once test-report.html exists) X6 execution evidence
# expect (each): PASS — 0 error(s)
```

`lint.py` is **syntax-level** (tag balance, unescaped `<`, bad `&`, `.card` missing `data-status`), one file at a time. `docverify.py` is **cross-document** — it mechanically enforces the reference-level items of the self-check below (every id in the Summary matches a card; every `<tc-card traces=>` resolves to a real AC; every AC is covered; Blocked→Blocked status + verbatim JIRA propagation) across the AC and test-case docs — and, once `test-report.html` exists, that every Ready AC is traced by a test case that **PASSED** there (X6, execution evidence) — so you need not hand-verify those. It does NOT check meaning beyond references. Still eyeball the rest of the **semantic self-check**:
- every `.card` `data-status` matches the `.status-badge` it shows (**automatic for `<ac-card>` / `<tc-card>`**, a standalone `<status-badge status="…">` derives its own label, and **`<trace-matrix>`** + **`<ac-summary>`** + **`<tc-summary>`** derive each table row's status from its card — all from one `status=`; only hand-written `.card` / `span.status-badge` / hand summary+matrix tables can drift);
- every AC/TC id in the body also appears in the Summary table (and vice-versa) — **`<ac-summary>`** / **`<tc-summary>`** / **`<tc-deferred>`** derive each row from the matching card (can't drift; a `<ac>`/`<tc ref>` pointing at no card shows blank cells);
- every `.gwt` has given/when/then (in G-A-W-T order for `<tc-card>` AND clauses);
- each `.tab[data-tab="x"]` has a matching `.tab-panel[data-tab="x"]` (**automatic inside `<tc-card>`** when both `<req>` + `<res>` are given);
- the trace-matrix lists every AC (**automatic with `<trace-matrix>`** — one row per `<ac-card>`; only a hand-built `table.trace-matrix` can miss one).

Occasionally (when layout/diagrams changed) eyeball a screenshot. Do not return `DONE` until BOTH `lint.py` and `docverify.py` report `PASS`.

---

## 8. What stays markdown (do NOT convert)

- **Ephemeral `docs/open-questions-*.md`** — throwaway Q&A, deleted after fold-back (per your Cleanup Invariant). Never HTML.
- **`docs/design/INDEX.md` + `docs/design/VERSION.md`** — the machine-readable registry/changelog the Orchestrator reads. Keep as markdown. The **human-facing** registry is the generated `docs/design/index.html` (§9), built FROM them.
- **`docs/design/gap-analysis.md`** — the **doc-vs-code drift ledger**: where §5.1's "code doesn't match the spec" notes go so they never pollute the spec pages. **Markdown**, never HTML; out of scope of `lint.py` / `docverify.py`; sibling of `INDEX.md` / `VERSION.md`. One append-only table, newest row first:
  `| Date | Doc element | Spec says | Code currently does | AC/ID | Status (open/closed) |`
  **Who/when:** any doc-role (BA / Architect / QA) in Doc-Review or adversarial-verify mode appends a row when it finds drift **and** surfaces the same gap in its chat output (so the orchestrator/user sees it without opening the file). Exclusions: a version/changelog entry → `VERSION.md`; a gap that is really a *desired spec change* → update the spec itself, not this ledger.
- **`docs/tasks/<card-id>/plan.md`** — the per-card **task-tracking / resume index** (`shared/task-tracking.md`): a `## Build Plan` (the developer work-breakdown) + the AC task table + card-keyed `Build` progress, which the Orchestrator reads to resume. **Markdown**, never HTML; out of scope of `lint.py` / `docverify.py`; lives under `docs/tasks/` (not `docs/design/`). Written only by BA (`roles/business-analyst.md` § Card Task-File). Card-keyed work only.
- **`docs/knowledge/`** (per-topic digests + `INDEX.md` + `VERSION.md`) — the **ingested knowledge base** (`shared/knowledge-base.md`): curated, topic-named markdown digests with portable provenance + a source manifest, ingested once and reused by roles. **Markdown**, never HTML; out of scope of `lint.py` / `docverify.py`; lives under `docs/knowledge/` (not `docs/design/`). Written only by the Librarian (`roles/librarian.md`). KB content mirrors its source and **may be non-English** (the language-neutral rule binds skill files only).
- **`docs/api/`** (custom-YAML **API spec** + generated `index.md` + `VERSION.md`) — the **source-of-truth API contract** (`templates/api-spec.md`): one endpoint per YAML file, **global by-domain**, authored spec-first and read by the api-doc chain (`openapi-doc` / `open-collection` / `confluence-api-doc`). **YAML + markdown, never HTML**; out of scope of `lint.py` / `docverify.py` — it has its own gate `apispeccheck.py`; lives under `docs/api/` (not `docs/design/`). Written only by the Architect.
- E2E test code (`.ts`) is out of scope here.

---

## 9. Two kinds of `index.html`

1. **Per-folder overview** — `docs/design/{usecase}/index.html` and `docs/design/system-design/index.html`. The sidebar "Overview" links point here, so they MUST exist. Build from `_shell.html`; body is a short summary + a `.card-grid` of `a.link-card`s to the folder's docs. BA creates the usecase overview when creating the usecase; Architect creates `system-design/index.html`.
2. **Top registry landing** — `docs/design/index.html`. Human-facing view of `INDEX.md` + `VERSION.md`: usecase `.link-card`s + a Version History `table.data-table[data-sortable]`. Regenerate it whenever you update `INDEX.md`/`VERSION.md`.

> Missing a per-folder `index.html` = the sidebar "Overview" link 404s. Always create it alongside the usecase's first doc.
