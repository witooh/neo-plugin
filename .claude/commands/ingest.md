---
description: Ingest an external source into docs/knowledge/ as curated, reusable context with provenance
---

Invoke the neo:markitdown skill.

Read the source the user names — a URL, JIRA/Confluence link, a file (PDF, Office doc, image, audio), or pasted text — and curate it into `docs/knowledge/<topic>.md` with provenance (source, fetched_at, validator). For binary or complex files, convert to Markdown first with `uvx markitdown <path>`.

Copy behaviour-constraining and contract clauses verbatim, in the source's original language — never paraphrase or translate them. Drop ephemeral state (a card's live status, a counter) and note where to read it live. Update `docs/knowledge/INDEX.md`. Refuse to ingest ephemeral noise — say so and skip.
