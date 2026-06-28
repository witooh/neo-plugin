---
name: ingest
description: >
  Ingest an external source (JIRA card, Confluence page, URL, image, HTML,
  text, or a verbal brief) once into `docs/knowledge/` as curated, reusable
  context — with provenance (source url, fetched_at, version/etag when
  available). The memory primitive that neo's Librarian and the ingest-first
  gate depend on. Standalone — call it directly (`/ingest <url>`) to pre-warm
  the knowledge base, or neo triggers it when a task needs context that is not
  yet ingested. Triggers: "/ingest", "ingest <source>", "remember this",
  "add <url> to the knowledge base", or neo routing here during the
  ingest-first gate.
---

# ingest — write a source into `docs/knowledge/`

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
topic + fetched_at, so the Librarian's ingest-first gate can scan fast.

## How you ingest, by source type

- **JIRA card** (via `atlassian`): read the card; keep the title, description,
  acceptance criteria, and linked design — these are stable. DROP the current
  status/transitions/assignee (volatile; read live). Note "status read live
  via atlassian" in the entry.
- **Confluence page** (via `atlassian`): keep the body's stable content; drop
  live macros/counts.
- **URL** (web): fetch, extract the readable content, keep the durable parts.
  Record the validator header if the server emitted one.
- **Image / HTML / text / verbal**: extract the facts with the source labeled
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

This self-check catches obvious drops. The independent fresh-eyes pass that
catches your *blind spots* is the Librarian's (KB5,
`skills/neo/roles/librarian.md`).

## Stance

- One source → one entry (split if a source spans multiple topics).
- Refuse to ingest ephemeral noise — say so and skip. Noise in
  `docs/knowledge/` is worse than absence.
- Never edit an existing entry silently; if a source changed, add a new entry
  and mark the old one superseded (the validator field makes staleness
  visible).
- The Librarian is your sole regular caller inside neo; users call you
  directly via `/ingest`.

## Non-goals

- ❌ You do not frame exit conditions (the Business Analyst does)
- ❌ You do not implement or verify (the loop + `using-agent-skills` do)
- ❌ You do not decide whether to re-fetch — you record the validator and let
  the consumer (Librarian/BA) decide
