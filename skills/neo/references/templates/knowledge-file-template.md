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

- **Every fact ends with an inline `[source-tag]`** that resolves to an INDEX row. Several sources on one fact → list each tag.
- **Current correct state only** — no changelog, no conflict markers, no superseded values (`VERSION.md` is the change trail; `../shared/knowledge-base.md §5,§8`).
- **`## References`** lists transitive sources this topic cites (record all; `[needed]` ones are ingested on-need — `../shared/knowledge-base.md §9`). Attachments are references too.
- **No `## Notes`** — every fact has a topic line, an inline tag, or an INDEX row; nothing else is recorded (`../shared/knowledge-base.md §10`).

## VERSION.md skeleton

`docs/knowledge/VERSION.md` — one whole-KB version + a changelog (newest first); bumps on every ingest / re-ingest / conflict resolution:

```markdown
# Knowledge Base — version history
Current: v1.2

| Version | Date | Change | Sources |
|---|---|---|---|
| 1.2 | 2026-06-10 | OQ-1 resolved: GI-52 authoritative on campaign rate (Confluence + linked tests stale) | GI-52, confluence:NEOACCT |
| 1.1 | 2026-06-10 | re-ingest GI-52 (txn limit 50k → 60k) | GI-52 |
| 1.0 | 2026-06-10 | initial ingest | GI-52, confluence:NEOACCT, image:neobank-flow |
```

## INDEX.md skeleton

`docs/knowledge/INDEX.md` — a discovery index: a **Topics** table (find the knowledge) + a **Sources** table (resolve a `[tag]` + carry each source's `hash`). **No `version` column** (version is whole-KB in `VERSION.md`):

```markdown
# Knowledge Base — index

## Topics
| Topic | File | Covers | Keywords |
|---|---|---|---|
| Account eligibility | account-eligibility.md | re-validate at open: Customer Group / Age / Account Limit | eligibility, KYC, account limit |
| Campaign & rate | campaign-rate.md | campaign validation + final rate | campaign, G5_NOV_26, bonus |

## Sources
| source-tag | type | portable locator | hash | topics |
|---|---|---|---|---|
| GI-52 | jira | https://.../browse/GI-52 | a1b2c3 | account-eligibility, campaign-rate |
| confluence:NEOACCT | confluence | https://.../wiki/.../NEOACCT | d4e5f6 | account-opening-flow, account-eligibility |
| login-mockup.png | image | https://.../wiki/.../Login (attachment) | e7f8a9 | login |
| verbal:BA-2026-06-10 | verbal | (attribution) | | account-eligibility |
```

- **Portable locator** per `../shared/knowledge-base.md §4`: URL > parent-URL + filename > bare filename; **never a local path**.
- **`hash`** (Sources) = computed at ingest from fetched content (staleness, KB3); blank for `verbal` / orphan.
- **`topics`** (Sources) = which digest file(s) cite this source (find where a source went; supports KB2). The **Topics** table is the searchable discovery layer.

## Field rules

- **Source tag format:** `[<KEY>]` for jira (`[GI-52]`), `[confluence:<short-name>]`, `[image:<filename>]`, `[verbal:<who>-<date>]`, `[url:<short-name>]`. A digest tag must match its INDEX `source-tag`.
- **Language:** a digest mirrors its source's language and **may be non-English**; the language-neutral rule binds skill files only (`../shared/knowledge-base.md §5`). *(Placeholders above are English because this template is a skill file.)*
- **Gates:** the Librarian runs KB1 (portable pointer + verify-once), KB2 (INDEX + VERSION integrity), KB3 (staleness → bump VERSION) before returning `DONE` (`../shared/knowledge-base.md §7`, `../roles/librarian.md`).
