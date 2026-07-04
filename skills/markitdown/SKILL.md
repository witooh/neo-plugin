---
name: markitdown
description: >
  Ingest an external source (JIRA card, Confluence page, URL, image, HTML,
  text, or a verbal brief) once into `docs/knowledge/` as curated, reusable
  context — with provenance (source url, fetched_at, version/etag when
  available). The memory primitive that neo's ingest-first step depends on.
  Standalone — call it directly (`/ingest <url>`) to pre-warm
  the knowledge base, or neo triggers it when a task needs context that is not
  yet ingested. Triggers: "/ingest", "ingest <source>", "remember this",
  "add <url> to the knowledge base", or neo routing here during the
  ingest-first gate.
---

# markitdown — ingest a source into `docs/knowledge/`

Curate, don't cache. Each ingestion produces one topic-scoped entry that a
future agent or human can re-read with full provenance.

## What you produce

One file at `docs/knowledge/<topic>.md` (or `<topic>-<n>.md` if the topic
already has entries) containing:

```markdown
---
source: <original url or "verbal:<date>" / "image:<name>" / "text">
fetched_at: <ISO date>
version: <etag / Last-Modified / commit sha / "n/a">
topic: <short slug this entry belongs to>
---

# <title from the source>

<curated body — the stable facts an agent needs>
- keep domain knowledge, decisions, constraints, enums, schemas
- **copy behaviour-constraining and contract clauses verbatim, in the source's
  original language** — never paraphrase or translate them (Fidelity below)
- drop ephemeral state (a Jira card's current status, a live counter)
  and note where to read it live instead

## Provenance
- fetched: <ISO date>
- source: <url>
- validator: <etag/Last-Modified/sha or "none — re-fetch to revalidate">
```

Maintain or create `docs/knowledge/INDEX.md` listing every entry with its
topic + fetched_at, so neo's ingest-first step can scan fast.

## How you ingest, by source type

- **JIRA card** (via `atlassian`): read the card; keep the title, description,
  acceptance criteria, and linked design — these are stable. DROP the current
  status/transitions/assignee (volatile; read live). Note "status read live
  via atlassian" in the entry.
- **Confluence page** (via `atlassian`): keep the body's stable content; drop
  live macros/counts.
- **URL** (web): fetch, extract the readable content, keep the durable parts.
  Record the validator header if the server emitted one.
- **PDF / Office doc / slides / spreadsheet / audio / image** (a local file or
  one you downloaded): convert it to Markdown first with `uvx markitdown <path>`
  (MarkItDown — the file→Markdown converter this skill is named for), then curate
  that Markdown like any other text. Optional convenience — plain text/HTML needs
  no conversion; if `uvx` is unavailable, `pip install markitdown` then
  `markitdown <path>`.
  - **Record the source by basename only** (`image:diagram.png`), never the
    absolute path — an abs path leaks the machine username into a checked-in
    doc. Use the file's sha256 as the validator for identity. (Applies to every
    filesystem-path source, not just images.)
  - **Diagram / whiteboard / screenshot:** `uvx markitdown` returns no usable
    text (metadata only) — read the image directly (vision) and transcribe it;
    the image itself is the source of truth, so say so in the entry.
  - **Topology source** (boxes + arrows, a flow): embed a **Mermaid** diagram in
    the entry — text an agent reads deterministically and a human renders —
    rather than leaning on the raw image. Verify arrow directions at native
    resolution first (see Fidelity), then validate the diagram renders.
  - **PDF text — verify the conversion:** on some PDFs `uvx markitdown` drops
    inter-word spaces (jams `PaymentGatewaySwitching`), which breaks both
    verbatim copying and FTS search. Check a sample; if mangled, re-extract with
    `pypdfium2` (`d[i].get_textpage().get_text_range()`) or read the PDF pages
    directly — that faithful text is the source, not the markitdown output.
  - **Large spec (many pages):** don't transcribe all of it. Index the clean
    full text as a searchable source, then curate the stable map + verbatim
    high-value clauses (endpoints, enums, error/response codes) into the entry;
    page-reference the bulk field tables to the indexed source — a *named*
    deferral, never a silent drop (KB4).
- **HTML / text / verbal**: extract the facts with the source labeled
  accordingly — prose for context, but behaviour-constraining clauses copied
  verbatim, not summarised (Fidelity below).

## Fidelity — every clause survives (KB4)

Curation must not silently drop a behaviour-constraining conjunct — the risk is
worst when the source is non-English and curation also translates (translation is
a second lossy transform). The bug this prevents is real: a source clause meaning
`return the result **with** the customer group` was curated as `returns the final
rate, term, campaign code` — the "with customer group" conjunct vanished and
shipped. A gist-level read lets "A and B" → "A" pass.

Before finishing an entry, self-check at the clause level:

1. Decompose the source into **atomic clauses** — each smallest unit that
   constrains observable behaviour (input, output, error, state, condition,
   default, unit, ordering, cardinality, side-effect).
2. Map every clause to a digest fact **or** a *named* other topic it belongs to
   (a bare "off-topic" is not allowed — name it).
3. **Copy, don't paraphrase** any behaviour-constraining or contract clause —
   verbatim, in the source's original language. Translation is a second lossy
   transform and is forbidden for these clauses (a translation may sit beside
   the verbatim quote, never replace it).
4. A clause that maps to neither → a dropped clause: **do not ship the entry;
   report BLOCKED** naming the missing clause.

For an **image source**, transcription has an extra failure mode: a single
full-frame read of a large image is downscaled and lossy. Crop each dense region
at native resolution and re-read it before trusting the transcript — then
clause-diff as above.

This self-check catches obvious drops. The independent fresh-eyes pass that
catches your *blind spots* (KB5) is a second, fresh-context re-fetch that
clause-diffs against this entry — neo's maker-checker runs it when neo drives
the ingest; run it yourself otherwise.

## Stance

- One source → one entry (split if a source spans multiple topics).
- Refuse to ingest ephemeral noise — say so and skip. Noise in
  `docs/knowledge/` is worse than absence.
- Never edit an existing entry silently; if a source changed, add a new entry
  and mark the old one superseded (the validator field makes staleness
  visible).
- neo is your sole regular caller inside the loop; users call you
  directly via `/ingest`.

## Non-goals

- ❌ You do not frame exit conditions (neo's loop does)
- ❌ You do not implement or verify (the loop + `using-agent-skills` do)
- ❌ You do not decide whether to re-fetch — you record the validator and let
  the consumer (neo) decide
