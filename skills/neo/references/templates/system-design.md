# System Design — [Usecase Name]

**Usecase folder:** `docs/design/[usecase]/`
**Version:** [version]
**Created Date:** [date]
**Created By:** Architect
**AC Document:** [path to acceptance criteria document, e.g., docs/design/[usecase]/acceptance-criteria.html]

---

## Output Format

The **system-design docs** here are emitted as **interactive HTML** — `system-design/*.html` (shared) + `traceability.html` (per usecase) — **not** markdown. **Build per [`html-output.md`](../html-output.md)** — the structure below is the CONTENT spec; the guide is the FORM. The **API spec is separate**: custom YAML under `docs/api/` (see [`api-spec.md`](api-spec.md)), authored spec-first, *not* part of this HTML site. Mapping:

- Entity / Domain Service / Repository / Usecase tables → `table.data-table[data-sortable]`. File Structure → `.code[data-lang="text"]`.
- ADRs → one `.card` per ADR. **Apply [`html-output.md`](../html-output.md) §5.1 before any `<callout-box>`** — version/changelog and doc-vs-code-gap notes do NOT belong on the page (they fail `docverify.py`).
- **Notes** (the `## Notes` section below) → a single **`<h2 id="notes">Notes</h2>` + `<ul>`** at the page end — the only home for cross-cutting spec notes (§5.1). `id="notes"` is load-bearing; omit when none.
- **AC Traceability → `table.trace-matrix`** (in `.matrix-wrap`; `tbody th` = AC-ID, click-highlights) on `traceability.html`; keep the coverage count. An endpoint design element traces to its `docs/api/<domain>/<endpoint>.yaml` file.
- Diagrams (sequence / flowchart / ER) → `.diagram` > `.mermaid` (raw mermaid; no HTML in labels — use `&lt;br/&gt;`).
- Create `system-design/index.html` overview and register links in `nav.js` (html-output.md §4, §9).
- **Verify:** `python3 <ASSET_DIR>/lint.py docs/design` then `python3 <ASSET_DIR>/docverify.py docs/design/<usecase>` until both `PASS`, then semantic self-check — every AC-ID from BA appears in the trace matrix. (The API spec has its own gate — `python3 <ASSET_DIR>/apispeccheck.py docs/api`; see [`api-spec.md`](api-spec.md).) Escape `<`/`>`/`&` in prose (§6).

---

## Overview

[1-2 sentences: what this design covers and why]

---

## API Spec (separate — `docs/api/`)

The API contract for every endpoint is **not** in this HTML doc — it is authored **spec-first** as custom YAML under `docs/api/<domain>/<endpoint>.yaml` (global, by-domain; see [`api-spec.md`](api-spec.md) for the schema + INDEX + VERSION rules). Reference the relevant endpoint file(s) from the AC Traceability table below — an endpoint design element → its `docs/api/.../*.yaml` file.

---

## Module Design

### Entity: [EntityName]

| Field | Type | Description | Business Rule |
|-------|------|-------------|---------------|
| [field] | [type] | [description] | [from AC] |

### Domain Service: [ServiceName]

Cross-entity business logic — calculations, validations, or coordination between entities. Not flow orchestration (that belongs to Usecase).

| Method | Signature | Description | Covers AC |
|--------|-----------|-------------|-----------|
| [method] | [input → output] | [business logic it performs] | AC-XXX |

### Repository: [RepositoryName]

| Method | Signature | Description |
|--------|-----------|-------------|
| [method] | [input → output] | [what it does] |

### Usecase: [UsecaseName]

Business flow orchestration — calls domain services and repositories in sequence. Usecase owns the flow, not the logic.

| Method | Signature | Description | Covers AC |
|--------|-----------|-------------|-----------|
| [method] | [input → output] | [what it does] | AC-XXX |

### File Structure

```
[module]/
├── entity.go (or .ts, .py, etc.)
├── repository.go
├── usecase.go
└── handler.go
```

---

## ADR (if applicable)

### ADR-001: [Decision Title]

**Context:** [why this decision is needed]

**Options Considered:**
1. [option 1] — [pros/cons]
2. [option 2] — [pros/cons]

**Decision:** [what was chosen and why]

**Consequences:** [trade-offs accepted]

---

## AC Traceability

| AC-ID | Design Element | Type |
|-------|----------------|------|
| AC-001 | [endpoint / entity field / usecase method / error response] | [API / Module / Validation / Error] |
| AC-002 | [design element] | [type] |

**Coverage:** [X/Y AC-IDs covered — if any AC is not covered, explain why as Open Question]

---

## Security Flags

- [anything that Security specialist should review — e.g., new auth flow, sensitive data handling, external API calls]

---

## Open Questions

- [anything unclear or technically infeasible from AC — needs user or BA clarification]

---

## Notes

_(Cross-cutting spec notes only — render as a single `<h2 id="notes">Notes</h2>` + `<ul>`. Per [`html-output.md`](../html-output.md) §5.1: NOT changelog (→ `VERSION.md`), NOT doc-vs-code gaps (→ `gap-analysis.md`). Element-specific notes fold into their section instead. Omit this section when there are none.)_

- [a cross-cutting design note — e.g. an orchestrator boundary, an out-of-scope statement]
