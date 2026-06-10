# Template: Knowledge digest + INDEX + VERSION (`docs/knowledge/`)

**Content spec for a knowledge digest and the source manifest.** Read with `../shared/knowledge-base.md` (definitions + gates). Written **only by the Librarian** (sole writer of `docs/knowledge/`). Read by the Librarian (refresh) and, **context-only**, by downstream roles (Architect / QA / Developer — `../shared/preamble.md §5`).

- **Format: Markdown, never HTML** — a registered exception (`../html-output.md §8`); do **not** run `lint.py` / `docverify.py` on it.
- **Topic-named**, kebab-case, timeless (`account-eligibility.md` — not `gi-52.md`, not a date/ticket). One file = one topic; it may aggregate several sources (`../shared/knowledge-base.md §5`).

## Digest skeleton

```markdown
# <Topic> (knowledge)

## <Sub-topic / grouping>
- <fact stated as current truth> [<source-tag>]
- <fact> [<source-tag>] (<short qualifier if needed>)

## <Sub-topic>
- <fact> [<source-tag>]

## References
- <ref-id-or-url> [<source-tag>] — <why it matters> [needed | record-only]
```

- **Every fact ends with an inline `[source-tag]`** that resolves to an INDEX Sources entry. Several sources on one fact → list each tag.
- **Current correct state only** — no changelog, no conflict markers, no superseded values (`VERSION.md` is the change trail; `../shared/knowledge-base.md §5,§8`).
- **`## References`** lists transitive sources this topic cites (record all; `[needed]` ones are ingested on-need — `../shared/knowledge-base.md §9`). Attachments are references too.
- **No `## Notes`** — every fact has a topic line, an inline tag, or an INDEX entry; nothing else is recorded (`../shared/knowledge-base.md §10`).

## VERSION.md skeleton

`docs/knowledge/VERSION.md` — one whole-KB version + a changelog (newest first); one `## v<N> — <date>` section per version with **Sources** / **Change** bullets; bumps on every ingest / re-ingest / conflict resolution:

```markdown
# Knowledge Base — version history
Current: v1.2

## v1.2 — 2026-06-10
- **Sources:** GI-52, confluence:NEOACCT
- **Change:** OQ-1 resolved: GI-52 authoritative on campaign rate (Confluence + linked tests stale)

## v1.1 — 2026-06-10
- **Sources:** GI-52
- **Change:** re-ingest GI-52 (txn limit 50k → 60k)

## v1.0 — 2026-06-10
- **Sources:** GI-52, confluence:NEOACCT, image:neobank-flow
- **Change:** initial ingest
```

## INDEX.md skeleton

`docs/knowledge/INDEX.md` — a discovery index: a **Topics** section (find the knowledge; one `### <Topic> — <file>` entry with **Covers** / **Keywords** bullets) + a **Sources** section (resolve a `[tag]` + carry each source's `hash`; one `### <source-tag> (<type>)` entry with **Locator** / **Hash** / **Topics** bullets). **No version field** (version is whole-KB in `VERSION.md`):

```markdown
# Knowledge Base — index

## Topics

### Account eligibility — account-eligibility.md
- **Covers:** re-validate at open: Customer Group / Age / Account Limit
- **Keywords:** eligibility, KYC, account limit

### Campaign & rate — campaign-rate.md
- **Covers:** campaign validation + final rate
- **Keywords:** campaign, G5_NOV_26, bonus

## Sources

### GI-52 (jira)
- **Locator:** https://.../browse/GI-52
- **Hash:** a1b2c3
- **Topics:** account-eligibility, campaign-rate

### confluence:NEOACCT (confluence)
- **Locator:** https://.../wiki/.../NEOACCT
- **Hash:** d4e5f6
- **Topics:** account-opening-flow, account-eligibility

### login-mockup.png (image)
- **Locator:** https://.../wiki/.../Login (attachment)
- **Hash:** e7f8a9
- **Topics:** login

### verbal:BA-2026-06-10 (verbal)
- **Locator:** (attribution)
- **Topics:** account-eligibility
```

- **Locator** (Sources) — portable per `../shared/knowledge-base.md §4`: URL > parent-URL + filename > bare filename; **never a local path**.
- **Hash** (Sources) — computed at ingest from fetched content (staleness, KB3); omit the bullet for `verbal` / orphan.
- **Topics** (Sources) — which digest file(s) cite this source (find where a source went; supports KB2). The **Topics** section is the searchable discovery layer.

## Field rules

- **Source tag format:** `[<KEY>]` for jira (`[GI-52]`), `[confluence:<short-name>]`, `[image:<filename>]`, `[verbal:<who>-<date>]`, `[url:<short-name>]`. A digest tag must match its INDEX `source-tag`.
- **Language:** a digest mirrors its source's language and **may be non-English**; the language-neutral rule binds skill files only (`../shared/knowledge-base.md §5`). *(Placeholders above are English because this template is a skill file.)*
- **Gates:** the Librarian runs KB1 (portable pointer + verify-once), KB2 (INDEX + VERSION integrity), KB3 (staleness → bump VERSION) before returning `DONE` (`../shared/knowledge-base.md §7`, `../roles/librarian.md`).
