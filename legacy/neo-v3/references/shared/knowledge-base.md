# Shared: Knowledge Base — ingested external knowledge (`docs/knowledge/`)

**Single source of truth for the knowledge-base layer: how external sources are ingested once into `docs/knowledge/` and reused.** Referenced by the Librarian (sole writer + gate enforcer), the Orchestrator (ingest-first guard + routing), the Business Analyst (reads the KB at Spec instead of re-fetching — `jira-ref.md §7`), and the downstream doc/code roles (context-only read — `preamble.md §5`). This file owns the **definitions**; the role/SKILL prose that cites it keeps its own enforcement.

**Why a KB layer.** Today external knowledge enters through BA alone, fetched fresh every dispatch and never reused; downstream roles never see the source. The KB ingests each source **once** into a curated, portable, versioned markdown layer the whole team shares — so knowledge is reused across roles + sessions, conflicts across sources become visible, and a changed source is detectable instead of silently stale.

## 1. Scope — ingest once, reuse everywhere

`docs/knowledge/` lives in the **consuming repo** (the project `neo` runs in), is **committed and shared across the team**, and holds knowledge ingested from external sources. A source is ingested **once**; every role thereafter reads the digest instead of re-fetching the original. The KB is **not** a spec: it is provenance + context. The acceptance-criteria document stays the single source of truth for *what to build* (`ac-status.md`); the KB is *what we know, and where it came from*.

## 2. Layout — markdown, a registered linter exception

```
docs/knowledge/
  VERSION.md            # whole-KB version + changelog (§6) — what changed, when
  INDEX.md              # discovery index (§6) — find a topic; resolve a [tag] to its source
  <topic>.md            # a curated, topic-named digest (§5)
```

- **Markdown by design** — the Orchestrator reads it to route/resume, exactly as it reads `docs/design/INDEX.md` / `docs/tasks/<card>/plan.md`. It is **out of scope of `lint.py` / `docverify.py`** and a registered markdown exception (`html-output.md §8`). **Never** author it as `.html`; never point the HTML verifiers at `docs/knowledge/`.
- **No `_sources/` directory.** Originals are never copied into the repo (they bloat git and fork the source of truth). A source is referenced by a **portable pointer** (§4), not a stored copy.

## 3. Source types + provenance

| `source_type` | Fetch | Re-fetchable? | Ground truth for KB1/KB5 verify |
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
- **Current correct state only.** A digest states what is true *now* — the same philosophy as a design doc (`html-output.md §5.1`). It is not a changelog and not a conflict log; the change trail is **`VERSION.md`** (§6).
- **Every fact carries an inline source tag**, so provenance survives without 1:1 files: `txn limit/txn: 60,000 [confluence:NEOACCT]`, `KYC re-run at open [GI-52]`, `multi-currency required [verbal:BA 2026-06-10]`. The tag resolves to an INDEX Sources entry (§6).
- **Contract clauses are quoted verbatim — never paraphrased, never translated.** Curation stays free to compose and group, but **any clause that constrains observable behavior** — input / output / error / state / condition / default / unit / ordering / cardinality / side-effect (e.g. a return list, a field list, an error list, an enum, a status transition) — is copied into the digest as the source's **original, unaltered wording**. Paraphrase silently drops a conjunct (`returns A **and** B` → `returns A`); translation is a second lossy transform on top. This is the rule **KB4** verifies (§7). Curation freedom remains for **non-contract context** (background, rationale, grouping).
- **KB content mirrors the source's language** — a digest may be non-English; the language-neutral rule binds **skill files** (`skills/neo/**`), not runtime `docs/knowledge/` digests. A quoted contract clause keeps the **source's original language** even when the surrounding digest prose differs — never translate a contract clause to match the digest's language.

## 6. VERSION.md (whole-KB version + changelog) + INDEX.md (discovery)

The KB mirrors the `docs/design/` split — a **`VERSION.md`** changelog (one section per version) + an **`INDEX.md`** discovery index (one section per topic / source), both Orchestrator-readable (no freeform prose, no Notes).

**`docs/knowledge/VERSION.md`** — one **whole-KB version** (not per source) + a changelog, newest first: one `## v<N> — <date>` section per version with **Sources** / **Change** bullets. It bumps on every ingest / re-ingest / conflict resolution; this is the human-readable "what changed".

```
# Knowledge Base — version history
Current: v1.2

## v1.2 — 2026-06-10
- **Sources:** GI-52, confluence:NEOACCT
- **Change:** OQ-1 resolved: GI-52 authoritative on campaign rate (Confluence BFID-0001-A + NEOX-1427/1398 stale)

## v1.1 — 2026-06-10
- **Sources:** GI-52
- **Change:** re-ingest GI-52 (txn limit 50k → 60k)

## v1.0 — 2026-06-10
- **Sources:** GI-52, confluence:NEOACCT, image:neobank-flow
- **Change:** initial ingest
```

**`docs/knowledge/INDEX.md`** — a discovery index: a **Topics** section (find the knowledge; one `### <Topic> — <file>` entry with **Covers** / **Keywords** bullets) + a **Sources** section (resolve an inline `[tag]` to its origin + carry each source's `hash` for staleness; one `### <source-tag> (<type>)` entry with **Locator** / **Hash** / **Topics** bullets). **No version field** — version is whole-KB in `VERSION.md`.

```
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

### verbal:BA-2026-06-10 (verbal)
- **Locator:** (attribution)
- **Topics:** account-eligibility
```

**Hash** = first hex of SHA-256 of fetched content at ingest (staleness, KB3); the bullet is omitted for verbal / orphan. Topics = the searchable discovery layer; Sources = provenance + staleness state.

## 7. Gates KB1 / KB2 / KB3 / KB4 / KB5 (defined here; enforced by `roles/librarian.md`)

- **GATE KB1 — Ingest soundness.** Every digest fact has a **portable source pointer** (§4 precedence; **never** a local path), and the source has an INDEX Sources entry. For a **last-resort / non-text** source (image / html) the extraction is **thorough** and **verified once at ingest** against the best-available ground truth: re-fetchable (jira/confluence/url) → against the source via its URL; **verbal / orphan → user-confirmed** (the digest is the durable record). Fail → `BLOCKED`.
- **GATE KB2 — Manifest integrity.** Every ingested source has exactly one INDEX Sources entry (`### <source-tag> (<type>)` + **Locator** / **Hash** / **Topics** bullets) and is named in a `VERSION.md` changelog entry; `VERSION.md` carries a current whole-KB version; every inline `[tag]` resolves to an INDEX Sources entry; no orphan tag and no orphan entry. Measurable — loop until green.
- **GATE KB3 — Staleness.** A **re-fetchable** source is re-hashed when encountered again; on hash drift the Librarian **auto-refreshes the digest** — and because a refresh re-runs the same paraphrase/translate transform, it **re-runs KB4 (and KB5 for an in-scope type) on the refreshed facts** before it **bumps the whole-KB version in `VERSION.md` (+ a changelog entry), and reports** the drift (it does **not** auto re-verify downstream — the user decides whether to re-spec). One-shot binary / verbal = N/A (changes only when the user re-provides → manual re-ingest + version bump).
- **GATE KB4 — Digest fidelity (L1, self-check).** The Librarian decomposes the source into **atomic clauses** (every acceptance bullet, every rule in the description, every item of a return / field / error / enum list). Each clause must **either** map to a digest fact **or** be logged as *belonging to another named topic* — name the owning topic; a bare "off-topic" is **not** allowed (it is the escape hatch that drops a clause). Every **contract clause** (§5) appears **verbatim in the source's original wording**. Applies to **all** source types **including verbal**. The coverage log is **transient** — surfaced in the Librarian's `Fidelity:` output line, **never persisted** in a digest (§10). Measurable → loop until every clause is accounted for. A dropped behavior-constraining clause → **`BLOCKED`** (never `DONE_WITH_CONCERNS`).
- **GATE KB5 — Digest fidelity (L2, independent fresh-eyes, verify-at-ingest).** A **second Librarian in verify-only mode** — a separate dispatch with fresh context, **not** the ingesting agent re-reading its own work (that is only KB4) — **re-fetches the raw source**, reads the digest, reconstructs the source's **atomic-clause set from the digest alone**, and **diffs it clause-by-clause** against the raw source, flagging **omission** (in the source, missing from the digest) and **invention** (in the digest, absent from the source). Clause-level granularity is mandatory: a gist-level diff lets a *narrowed* clause (`returns A and B` → `returns A`) pass. Scope: **re-fetchable text** (jira / confluence / html / text) **+ image** (re-read); **verbal / orphan = N/A** (KB1 user-confirm is their net — nothing independent to re-fetch). **Mandatory at ingest** for an in-scope source. Any gap → loop back to the ingest Librarian → re-verify; **loop until the diff is clean OR ~3 rounds no-progress → escalate** (never silent, never fake-green).

**The Ingest Loop (mirrors the Dev Loop).** `Ingest (Librarian — KB1/KB2/KB4) → Verify (second Librarian — KB5, in-scope sources) → gap → re-ingest → re-verify → exit when fidelity-green`. It **auto-loops** inside the Ingest phase: like `Build → Verify` it adds **no user checkpoint** — the orchestrator dispatches the verify pass automatically (`phase-map.md` § Ingest-first guard). ~3 rounds no-progress → escalate.

## 8. Conflict ownership — surfaced, never AI-resolved

Two sources can disagree (the card says limit 50k, Confluence says 60k). The KB **must not** pick a winner — choosing silently is guessing (Never-Guess, `preamble.md §1`) and hides the disagreement. Instead:

1. **Detect** — the Librarian (at ingest, best-effort across a topic's sources) or BA (at Spec, when it cannot write a single AC value — its existing Never-Guess) notices the clash.
2. **Surface** — relay it to the user as an Open Question (transient; not stored as a standing artifact). The AI may **propose** ("GI-52 looks stale → 60k"), never **decide**.
3. **User decides.**
4. **Apply** — split by sole-writer domain: the **Librarian** edits the topic digest **in place** to the correct value (KB domain) — the corrected value must **satisfy KB4** (quoted verbatim from the now-authoritative source; a re-fetchable winner is a KB5 candidate) — **and logs the resolution as a `VERSION.md` changelog entry** (which source won + why); the **BA** applies the corrected value to the AC + re-verifies (AC domain).

There is **no `conflicts.md`** and **no inline conflict markers in digests** — a digest holds only the current correct state, and the resolution (which source won + why) is **one `VERSION.md` changelog entry**, not a per-digest section. A conflict is often **staleness in disguise** (§9) — ask "genuinely disagree, or is one source stale?" first.

## 9. Recursion + staleness

- **References — record all, ingest on-need (depth-1).** A source often cites others (GI-52's rule says "same criteria as GI-74"; a diagram cites a dozen cards). Record **all** transitive references in the digest / INDEX (free), but **ingest** a referenced source only **when a phase needs it** (demand-driven), and do **not** auto-recurse past it. A dependency cluster deeper than ~3 hops in one task → **escalate to the user** ("ingest the whole cluster, or scope it?"). **Attachments are a kind of reference** — listed at ingest (`acli jira workitem attachment`), ingested on-need, referenced to their parent (§4).
- **Staleness — KB3.** See §7: re-hash on re-encounter → auto-refresh (re-runs KB4/KB5 per §7) + bump the `VERSION.md` version + report; user decides re-spec.

## 10. No catch-all Notes

A KB artifact has **no freeform `## Notes` section**. Every fact gets a purposeful home — a topic line, an inline `[source]` tag, or an INDEX entry. If a piece of information has no purposeful home, it is not recorded. (Same discipline as `html-output.md §5.1` callout-routing; a generic Notes bucket invites noise and drift.) The **KB4 coverage log** (which source clauses mapped, which belong to another topic) is **not** an exception — it is transient verification state surfaced in the Librarian's `Fidelity:` output, never written into a digest or a sibling file.
