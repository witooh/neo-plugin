---
name: neo-ingest
description: >
  Entry point for the Ingest phase of the neo workflow — capture an external
  source into docs/knowledge/ before spec, plan, or code. Delegates to the
  `markitdown` skill for all curation (provenance, verbatim contract clauses,
  docs/knowledge/INDEX.md); this entry adds only the neo ingest-first framing.
  Use when a neo task names an unread URL, JIRA/Confluence link, PDF, image, or
  brief, when a later phase needs context not yet in docs/knowledge/, or when you
  invoke /neo-ingest. The curation method itself is `markitdown`.
---

# Neo Ingest — knowledge-base capture entry point

## Overview

This is the neo entry point for the Ingest phase. It is a thin wrapper: all
curation — provenance, verbatim contract clauses, the `docs/knowledge/` layout
and `INDEX.md` — is done by the `markitdown` skill. This entry adds only the neo
ingest-first framing (capture a named source before later phases consume it). It
does **not** duplicate any curation logic; the method lives in `markitdown`.

## When to Use

- When a neo task names an external source that isn't captured yet — a URL,
  JIRA/Confluence link, PDF, Office doc, image, audio, or a verbal brief.
- When a later phase (spec, plan, build) needs context not yet in
  `docs/knowledge/`.
- When you invoke `/neo-ingest`.
- Route elsewhere: for the curation mechanics themselves → `markitdown` (it owns
  the `/ingest` trigger); to write a spec from already-captured context →
  `neo-spec`.

## The Workflow

1. Identify the source the user named.
2. Run the `markitdown` skill to curate it into the right `docs/knowledge/`
   bucket (`contracts/` · `requirements/<domain>/` · `reference/` — markitdown
   owns the placement rules) with provenance and to update
   `docs/knowledge/INDEX.md`. markitdown copies behaviour-constraining and
   contract clauses verbatim (never paraphrased or translated), drops ephemeral
   state, and refuses ephemeral noise; a requirements entry gets a curator
   **Related** block linking the contracts/reference entries it depends on.
3. Confirm the source is captured so downstream phases can rely on it — and if
   this ingest satisfies a "not yet ingested" item in an existing requirement's
   Related block, update that block to link the new entry.

Do not re-implement curation here — defer to `markitdown` for every mechanic.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I'll just read the source into context and move on." | Ingest produces a reusable, provenance-stamped entry the whole workflow (and future sessions) can re-read — an in-context read is lost next turn. |
| "I'll summarize the contract clauses to save space." | markitdown copies contract clauses verbatim; a paraphrase or translation is a second lossy transform that can drop a constraint. |
| "The source has a live status, capture all of it." | Drop ephemeral state and note where to read it live — noise in docs/knowledge/ is worse than absence. |
| "The full path documents exactly where the source file was." | For a filesystem source, record the **basename only** — an absolute path leaks the machine username into a checked-in doc. The sha256 validator identifies the file; the path adds nothing but PII. |

## Red Flags

- Proceeding to spec/plan/build on a named-but-unread source without ingesting it.
- Paraphrasing or translating a behaviour-constraining or contract clause.
- Duplicating markitdown's curation steps here instead of deferring to it.
- Leaking an absolute filesystem path (with the machine username) into the
  entry — a local-file source must be recorded by **basename only** (e.g.
  `image:diagram.png`, never `/Users/<name>/…/diagram.png`). The rule lives in
  `markitdown`; this gate catches it before the entry ships.

## Verification

- The source is curated into its `docs/knowledge/` bucket
  (`contracts/` / `requirements/<domain>/` / `reference/`) with provenance.
- A requirements entry carries its **Related** block (dependency links +
  named not-yet-ingested list).
- `docs/knowledge/INDEX.md` is updated (grouped by bucket).
- `markitdown`'s own fidelity self-check passed (no dropped clauses).
- No absolute host paths or usernames in the entry — filesystem-path sources are
  recorded by basename (identity comes from the sha256 validator, not the path).
