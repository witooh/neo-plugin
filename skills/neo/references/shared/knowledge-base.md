# Shared: Knowledge Base — ingested external knowledge (`docs/knowledge/`)

**Single source of truth for the knowledge-base layer: how external sources are ingested once into `docs/knowledge/` and reused.** Referenced by the Librarian (sole writer + gate enforcer), the Orchestrator (ingest-first guard + routing), the Business Analyst (reads the KB at Spec instead of re-fetching — `jira-ref.md §7`), and the downstream doc/code roles (context-only read — `preamble.md §5`). This file owns the **definitions**; the role/SKILL prose that cites it keeps its own enforcement.

**Why a KB layer.** Today external knowledge enters through BA alone, fetched fresh every dispatch and never reused; downstream roles never see the source. The KB ingests each source **once** into a curated, portable, versioned markdown layer the whole team shares — so knowledge is reused across roles + sessions, conflicts across sources become visible, and a changed source is detectable instead of silently stale.

## 1. Scope — ingest once, reuse everywhere

`docs/knowledge/` lives in the **consuming repo** (the project `neo` runs in), is **committed and shared across the team**, and holds knowledge ingested from external sources. A source is ingested **once**; every role thereafter reads the digest instead of re-fetching the original. The KB is **not** a spec: it is provenance + context. The acceptance-criteria document stays the single source of truth for *what to build* (`ac-status.md`); the KB is *what we know, and where it came from*.

## 2. Layout — markdown, a registered linter exception

```
docs/knowledge/
  INDEX.md              # the source manifest (§6) — one row per ingested source
  <topic>.md            # a curated, topic-named digest (§5)
```

- **Markdown by design** — the Orchestrator reads it to route/resume, exactly as it reads `docs/design/INDEX.md` / `docs/tasks/<card>/plan.md`. It is **out of scope of `lint.py` / `docverify.py`** and a registered markdown exception (`html-output.md §8`). **Never** author it as `.html`; never point the HTML verifiers at `docs/knowledge/`.
- **No `_sources/` directory.** Originals are never copied into the repo (they bloat git and fork the source of truth). A source is referenced by a **portable pointer** (§4), not a stored copy.

## 3. Source types + provenance

| `source_type` | Fetch | Re-fetchable? | Ground truth for KB1 verify |
|---|---|---|---|
| `jira` | `acli jira workitem view <KEY> --json --fields *all` | yes (URL) | the live card |
| `confluence` | `acli confluence page view --id <ID> --body-format storage --json` | yes (URL) | the live page |
| `image` | the Read tool (renders it) at ingest | only if it has an online home | the original (verified once at ingest) |
| `html` / `text` / file | the Read tool / fetch | usually (URL) | the source |
| `verbal` | **passed inline** in the Librarian dispatch | **no** | **the user** (confirm at capture) |

**`verbal`** = knowledge the user states in the prompt ("I talked to the BA — limit is 50k/txn, multi-currency required"). It exists nowhere durable, so it is the highest-value ingest. Its provenance is an **attribution** (who / when / channel), not a URL; the digest is the authoritative record; it is **user-confirmed at capture**. The Orchestrator passes the verbal content **inline** to the Librarian — the one sanctioned exception to point-to-read (there is no path to point at; reuse the dispatch template's `added requirements (mid-task): <inline note>` channel).

## 4. Portable source pointer (committed + shared → never machine-local)

The KB is committed and read by the whole team, so a pointer must resolve for **anyone**, on any machine. Use the most portable, re-resolvable locator available:

1. **URL** — a jira/confluence/web address (best; re-resolvable + re-fetchable).
2. **Attachment** → the **parent page/card URL + the filename** (the filename alone is not resolvable; the parent URL is).
3. **Bare filename** — last resort, when the source has no online home (e.g. a pasted screenshot). A label only; the digest is then the sole durable record.

**Never a local filesystem path** (`/Users/...` breaks for everyone else). Never a stored copy.

## 5. Curate by topic + inline source tags

- **Topic-named files, not source-mirrors.** A digest is named for its **topic** (`account-eligibility.md`, `account-opening-flow.md`) and may aggregate facts from several sources. The Librarian **composes/curates** the KB by topic — it does **not** mirror each source 1:1.
- **Current correct state only.** A digest states what is true *now* — the same philosophy as a design doc (`html-output.md §5.1`). It is not a changelog and not a conflict log; the change trail is **git history** of the file.
- **Every fact carries an inline source tag**, so provenance survives without 1:1 files: `txn limit/txn: 60,000 [confluence:NEOACCT]`, `KYC re-run at open [GI-52]`, `multi-currency required [verbal:BA 2026-06-10]`. The tag resolves to an INDEX row (§6).
- **KB content mirrors the source's language** — it may be non-English. The language-neutral rule binds **skill files** (`skills/neo/**`), not runtime `docs/knowledge/` digests.

## 6. INDEX.md — the source manifest (a table, no prose)

`docs/knowledge/INDEX.md` is one **table**, one row per ingested **source** (not per topic file). It lets a reader resolve an inline `[tag]`, see which topics a source feeds, and check staleness:

```
| source-tag | type | portable locator | hash | version | topics |
|---|---|---|---|---|---|
| GI-52 | jira | https://.../browse/GI-52 | a1b2c3 | 1 | account-eligibility, account-opening-flow |
| NEOACCT | confluence | https://.../wiki/.../NEOACCT+-+Account+Service | d4e5f6 | 1 | account-opening-flow |
| verbal:BA-2026-06-10 | verbal | (attribution) | | 1 | account-eligibility |
```

No prose, no Notes — a manifest only. `hash` is computed at ingest from the fetched content (used for staleness, §9); for `verbal` / orphan sources it is left blank.

## 7. Gates KB1 / KB2 / KB3 (defined here; enforced by `roles/librarian.md`)

- **GATE KB1 — Ingest soundness.** Every digest fact has a **portable source pointer** (§4 precedence; **never** a local path), and the source has an INDEX row. For a **last-resort / non-text** source (image / html) the extraction is **thorough** and **verified once at ingest** against the best-available ground truth: re-fetchable (jira/confluence/url) → against the source via its URL; **verbal / orphan → user-confirmed** (the digest is the durable record). Fail → `BLOCKED`.
- **GATE KB2 — Manifest integrity.** Every ingested source has exactly one INDEX row (`source-tag → type → locator → hash → version → topics`); every inline `[tag]` resolves to an INDEX row; no orphan tag and no orphan row. Measurable — loop until green.
- **GATE KB3 — Staleness.** A **re-fetchable** source is re-hashed when encountered again; on hash drift the Librarian **auto-refreshes the digest + reports** the drift (it does **not** auto re-verify downstream — the user decides whether to re-spec). One-shot binary / verbal = N/A (changes only when the user re-provides → manual re-ingest + version bump).

## 8. Conflict ownership — surfaced, never AI-resolved

Two sources can disagree (the card says limit 50k, Confluence says 60k). The KB **must not** pick a winner — choosing silently is guessing (Never-Guess, `preamble.md §1`) and hides the disagreement. Instead:

1. **Detect** — the Librarian (at ingest, best-effort across a topic's sources) or BA (at Spec, when it cannot write a single AC value — its existing Never-Guess) notices the clash.
2. **Surface** — relay it to the user as an Open Question (transient; not stored as a standing artifact). The AI may **propose** ("GI-52 looks stale → 60k"), never **decide**.
3. **User decides.**
4. **Apply** — split by sole-writer domain: the **Librarian** edits the topic digest **in place** to the correct value (KB domain); the **BA** applies the corrected value to the AC + re-verifies (AC domain). **git history is the change trail.**

There is **no `conflicts.md`**, **no inline conflict markers**, and **no OPEN→RESOLVED lifecycle** — the digest holds only the current correct state; `git diff` shows what changed. A conflict is often **staleness in disguise** (§9) — ask "genuinely disagree, or is one source stale?" first.

## 9. Recursion + staleness

- **References — record all, ingest on-need (depth-1).** A source often cites others (GI-52's rule says "same criteria as GI-74"; a diagram cites a dozen cards). Record **all** transitive references in the digest / INDEX (free), but **ingest** a referenced source only **when a phase needs it** (demand-driven), and do **not** auto-recurse past it. A dependency cluster deeper than ~3 hops in one task → **escalate to the user** ("ingest the whole cluster, or scope it?"). **Attachments are a kind of reference** — listed at ingest (`acli jira workitem attachment`), ingested on-need, referenced to their parent (§4).
- **Staleness — KB3.** See §7: re-hash on re-encounter → auto-refresh + report; user decides re-spec.

## 10. No catch-all Notes

A KB artifact has **no freeform `## Notes` section**. Every fact gets a purposeful home — a topic line, an inline `[source]` tag, or an INDEX row. If a piece of information has no purposeful home, it is not recorded. (Same discipline as `html-output.md §5.1` callout-routing; a generic Notes bucket invites noise and drift.)
