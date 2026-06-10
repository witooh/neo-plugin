# Template: Knowledge digest + INDEX (`docs/knowledge/`)

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
- **Current correct state only** — no changelog, no conflict markers, no superseded values (git history is the trail; `../shared/knowledge-base.md §5,§8`).
- **`## References`** lists transitive sources this topic cites (record all; `[needed]` ones are ingested on-need — `../shared/knowledge-base.md §9`). Attachments are references too.
- **No `## Notes`** — every fact has a topic line, an inline tag, or an INDEX row; nothing else is recorded (`../shared/knowledge-base.md §10`).

## INDEX.md skeleton

`docs/knowledge/INDEX.md` — one table, one row per ingested **source**:

```markdown
# Knowledge Base — source manifest

| source-tag | type | portable locator | hash | version | topics |
|---|---|---|---|---|---|
| GI-52 | jira | https://.../browse/GI-52 | a1b2c3 | 1 | account-eligibility, account-opening-flow |
| NEOACCT | confluence | https://.../wiki/.../NEOACCT+-+Account+Service | d4e5f6 | 1 | account-opening-flow |
| login-mockup.png | image | https://.../wiki/.../Login (attachment) | e7f8a9 | 1 | login |
| verbal:BA-2026-06-10 | verbal | (attribution) | | 1 | account-eligibility |
```

- **Portable locator** per `../shared/knowledge-base.md §4`: URL > parent-URL + filename > bare filename; **never a local path**.
- **`hash`** = computed at ingest from fetched content (staleness, KB3); blank for `verbal` / orphan.
- **`topics`** = which digest file(s) cite this source (lets a reader find where a source went; supports KB2).

## Field rules

- **Source tag format:** `[<KEY>]` for jira (`[GI-52]`), `[confluence:<short-name>]`, `[image:<filename>]`, `[verbal:<who>-<date>]`, `[url:<short-name>]`. A digest tag must match its INDEX `source-tag`.
- **Language:** a digest mirrors its source's language and **may be non-English**; the language-neutral rule binds skill files only (`../shared/knowledge-base.md §5`). *(Placeholders above are English because this template is a skill file.)*
- **Gates:** the Librarian runs KB1 (portable pointer + verify-once), KB2 (INDEX integrity), KB3 (staleness) before returning `DONE` (`../shared/knowledge-base.md §7`, `../roles/librarian.md`).
