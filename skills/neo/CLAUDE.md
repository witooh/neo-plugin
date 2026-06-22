# CLAUDE.md — editing the `neo` skill

Scoped guidance for anyone (human or Claude) **editing files under `skills/neo/`**. The repo-root `CLAUDE.md` owns the wider wiring (hook polyglot, version bump, publish flow); this file owns the invariants that are easy to break when you touch `neo` itself. Root keeps a one-paragraph pointer here — keep the two in sync, but put neo detail here, not there.

**This is a maintainer doc, not runtime.** The skill never point-to-reads this file, and it is NOT loaded when the plugin is installed in another repo — it only loads while editing `skills/neo/` in *this* repo. Zero runtime token cost. Don't reference it from `SKILL.md` or any role file.

## Architecture in one paragraph

`neo` is a **phase-based orchestrator**. `SKILL.md` (~100 lines) is a thin router that does **no real work** — it selects the phase subset a task touches (per `references/phase-map.md`) and dispatches specialists via the `Agent` tool. Phases: **Spec**(BA) → **Design**(Architect) → **TestSpec**(QA) → **Build**(Developer) → **Verify**(QA-E2E ∥ Code Reviewer ∥ Security), plus **Diagnose**(System Analyzer) for bugs. The orchestrator is allowed only `Agent` / `Read` / `Skill` / `AskUserQuestion` — **never `Edit`/`Write`/`Bash`** (those would mean it implemented work itself). All real work lives in specialists. **The API contract is the `api-spec`** — custom-YAML, one file per endpoint, in a separate **global** tree `docs/api/` authored spec-first by the Architect (`templates/api-spec.md` + `assets/apispeccheck.py`), *not* the HTML design site under `docs/design/`; the downstream api-doc chain (`openapi-doc` / `open-collection` / `confluence-api-doc`) reads it.

## Invariants — do not break

- **Point-to-read, never paste.** A dispatch sends *paths* (`NEO_DIR` + artifact paths); the specialist reads its own role spec from `references/roles/<role>.md`. The orchestrator must never paste role specs / artifacts / session history into the prompt. If you add a rule a specialist needs, put it in the role file — not in `SKILL.md`'s dispatch prompt.
- **`NEO_DIR` / `ASSET_DIR` handoff is mandatory on every dispatch.** The specialist is `general-purpose` and does not know the skill's install path. `ASSET_DIR = <NEO_DIR>/assets`. **Missing either = a doc-role cannot build HTML and fails silently.**
- **Load-bearing gates — 23 IDs / 156 occurrences.** Verify the count is unchanged before/after any edit (see § Verify). Current inventory:
  `KB4`×29 · `KB5`×26 · `CS1`×23 · `KB1`×15 · `KB3`×11 · `BA5`×10 · `KB2`×9 · `AR7`×8 · `Q7`×6 · `AR4`×4 · `BA1`×2 · `D4`×2 · `CR3` `Q1` `Q3` `Q4` `Q6` `SEC2` `SA1` `SA2` `SA3` `SA4` `SA5` ×1 each.
  These encode real behavior (CS1 completeness-sweep · BA5 intent confirm + source-artifact coverage · AR7/Q7 doc-adversarial + verify-only mode · AR4 traceability count-match · D4 route-reg · CR3 · SEC2 secrets→Critical · SA1–5 prod-safety · **KB1 portable provenance + verify-once-at-ingest · KB2 INDEX+VERSION integrity · KB3 source staleness → bump KB version · KB4 digest atomic-clause fidelity self-check · KB5 second-Librarian fresh-eyes re-fetch + clause-level diff (verify-at-ingest, mandatory)** — Librarian, `shared/knowledge-base.md` §7). Renaming/removing one silently drops a guard — don't, unless you also remove its enforcement deliberately and update this count. *(Counts move when gates are cited in new prose — re-measure with the § Verify grep and write the observed numbers, never a guess.)* **Three pre-Build guards are intentionally ID-less** — the All-Blocked guard, the card Task-file guard (`shared/task-tracking.md`), and the **Ingest-first guard** (`phase-map.md` § Ingest-first guard) are routing checks, not numbered gates; don't give them IDs (that would inflate this count and is unnecessary — the orchestrator enforces them by prose). The Ingest-first guard wraps the **Ingest Loop**, whose fidelity gates **KB4/KB5 do carry IDs** (the wrapper stays ID-less; the gates inside it are numbered — `shared/knowledge-base.md` §7).
- **HTML asset coupling** (`references/html-output.md` + `assets/`):
  - `scaffold.sh` is idempotent and **must never overwrite `nav.js`** — a writer that regenerates `nav.js` breaks navigation.
  - `components.js` must load **before** `app.js` (classic script order).
  - `INDEX.md` / `VERSION.md` stay **Markdown** (the orchestrator reads them to route).
  - `docverify.py` reads the source authoring tag — don't strip it from generated HTML.
  - `docverify.py` enforces **callout discipline** (`html-output.md` §5.1) across **every** page in a usecase folder (not just the card docs — it now globs `*.html`, so `traceability.html` / `index.html` are covered): a version/changelog or doc-vs-code-gap `<callout-box>` on a spec page is an **ERROR** (→ `VERSION.md` / `gap-analysis.md`); a Notes-region (`<h2 id="notes">`) is exempt; >6 non-exempt callouts/page warns. Keep hand-authored callouts parseable — don't bury them in `<script>`/`<pre>` to dodge the check. The classifier (`VERSION_RE` start-anchored, `VERSION_MIDTEXT`+`CHANGE_VERB` mid-text co-signal, `GAP_PHRASES` / `GAP_WEAK` + code-pointer co-signal) is corpus-tuned; widen `GAP_PHRASES` as new docs surface. These are docverify check IDs (C1-C3), **not** gate-inventory IDs — the gate grep pattern matches neither `C\d` nor `X\d` (the cross-file X-series, incl. X6), so the gate-inventory count is unaffected (**23 IDs / 156 occ**, unchanged).
  - `docverify.py` also runs **X6 — execution evidence** (conditional on `test-report.html` existing): every **Ready** AC must be traced by a test case that PASSED in the report — closes "scoped-pass != feature-complete" (a Ready AC with only ❌/⏸/absent results errors; Blocked AC + its `@blocked`/deferred TC exempt; per-usecase, like X1/X2/X5). The X-series (incl. X6) are docverify check IDs, **not** gate-inventory IDs.
  - Doc-roles must run `lint.py` + `docverify.py` until both report `PASS — 0 error(s)` before returning `DONE`.
- **Checkpoints at 4 points only:** CP1 plan · CP2 BA5 intent · CP3 before Build / before posting an MR comment · CP-final. Don't reintroduce per-role checkpoints (that was v2.6's slowness). (The L2 fresh-eyes ask is folded into CP-final — not a 5th checkpoint.)
- **Verification is independent-verify, not ceremony.** Doc-adversarial loops back upstream **1 round on semantic/judgment defects** then escalates; **measurable defects (count/grep/CS1) loop until evidence-green, ~3 rounds no-progress → escalate** (same stall wording as the Dev Loop). L2 fresh-eyes reuses the downstream role in **verify-only mode** when a writer runs isolated (folded into CP-final). **Still no budget/max-iteration prose** — "evidence-green OR ~N rounds" only; never delete the independent verify itself.
- **Knowledge base** (`shared/knowledge-base.md` + `roles/librarian.md`). `docs/knowledge/` is **markdown** (registered exception — `html-output.md §8`); the Librarian is its **sole writer**; downstream reads it **context-only** (AC stays binding — `preamble.md §5`). Conflicts are **user-decided**, applied in place by the Librarian (KB) + BA (AC) and logged as a `VERSION.md` changelog entry (`## v<N> — <date>` section, **Sources**/**Change** bullets) — **no `conflicts.md`**, no inline markers. **No catch-all `## Notes`** in any KB artifact. KB *content* may be non-English (the 0-Thai rule binds skill files only). **Digest fidelity is gated:** **KB4** (Librarian self-checks that every source clause maps to a digest fact or a *named* other topic; contract clauses copied **verbatim in the source's language**, never paraphrased/translated) + **KB5** (a second Librarian in verify-only mode re-fetches the raw source and diffs the digest clause-by-clause at ingest — the **Ingest Loop**, mirrors the Dev Loop, no extra checkpoint, mandatory for re-fetchable text + image). The KB4 coverage log is **transient** (surfaced in the Librarian's `Fidelity:` output), never a persisted Notes. The Ingest-first guard is ID-less (see the gate bullet).
- **API spec** (`templates/api-spec.md` + `assets/apispeccheck.py` + `roles/architect.md`). `docs/api/` is the **custom-YAML source of truth for every HTTP endpoint** — one file per endpoint, **global by-domain** (not per-usecase), authored **spec-first** by the Architect (its sole writer), with a **generated** `index.md` + hand-maintained `VERSION.md`. It is **YAML/markdown, never HTML** (registered exception — `html-output.md §8`); out of scope of `lint.py`/`docverify.py` — its L1 gate is **`apispeccheck.py`** (validates each endpoint YAML + regenerates `index.md`). Downstream reads it: `openapi-doc` verifies Go against it (drift / sync-back), `open-collection` + `confluence-api-doc` render it. **Notes discipline:** a field note → its `remark`; only a cross-cutting note → an endpoint's `notes:` (omit when empty); changelog → `VERSION.md`. **Not OpenAPI** — the schema carries M/O + Remark + multi-flow business logic natively. The Architect runs `openapi-doc` for **sync-back** (Go drift → reconcile the YAML).

## Language-neutral rule

The plugin is **English-only / language-neutral** — the runtime communication language belongs in the consuming repo's `~/.claude/CLAUDE.md`, **not** hardcoded here. Do not reintroduce a "respond in <language>" directive into any skill file (Open Questions, MR comment template, role specs). After any edit, a Thai/non-ASCII scan over `skills/neo/**/*.md` must stay **0**:

```
python3 - <<'PY'
import glob
print(sum(1 for f in glob.glob('skills/neo/**/*.md',recursive=True)
         for c in open(f,encoding='utf-8').read() if 0x0e00 <= ord(c) <= 0x0e7f))
PY
```

If a consuming team needs MR comments in their language, that directive goes in **their** repo's `CLAUDE.md`, never in `mr-review-template.md` / `qa.md`.

## Reference layout (what reads what)

```
SKILL.md                       thin router (loaded on every trigger — keep lean)
references/
  phase-map.md                 task → phase subset (read before every plan)
  html-output.md               HTML form + the lint/docverify contract
  system-analyzer-cli-tools.md System Analyzer's read-only tooling
  roles/<role>.md              distilled role capsule (specialist point-to-reads this)
  shared/preamble.md           universal agent header (read first on every dispatch) + report-discipline (§6)
  shared/ac-status.md          Ready/Blocked state machine + Sign-Off math
  shared/jira-ref.md           JIRA Ref capture → inherit-verbatim → sticky
  shared/task-tracking.md      Build progress axis + Build Plan (dev work-breakdown) + the card task-file (docs/tasks/<card-id>/plan.md, markdown; card-keyed work)
  shared/knowledge-base.md     KB definitions + gates KB1-5 (docs/knowledge/ ingested external knowledge; Librarian-written markdown)
  shared/convention-grounding.md  layered-guide grounding: inclusion modes + file-set selection (Code Reviewer + Developer point-to-read; Architect keeps its own inline block — see note)
  templates/*.md               per-artifact content specs (read by the role that emits it; incl. api-spec.md + task-file-template.md + knowledge-file-template.md)
assets/                        scaffold.sh + lint.py + docverify.py + apispeccheck.py (api-spec L1, docs/api/) + JS/CSS/HTML (English already)
```

**Architect vs. convention-grounding.md.** `convention-grounding.md` serves the **file-set-driven** roles (Code Reviewer = the diff, Developer = files about to be written). The Architect grounds the same way but is **design-section-driven** (maps each Design Section to a layer, not a file-set), so it intentionally keeps its own inline grounding block in `roles/architect.md` — accepting a little duplication rather than contorting the shared algorithm. Don't "DRY" the Architect into this file.

`SKILL.md`'s `description` frontmatter is the **trigger contract** — Claude matches against it (not the body) to decide whether to fire. Edit it only to change *when* `neo` activates; edit the body to change *what happens after*.

## Adding a role or phase — sync these

1. **`references/roles/<role>.md`** — the new capsule (start from `shared/preamble.md` as the header; keep it distilled, gates + domain only).
2. **`references/phase-map.md`** — add the routing row(s) so the orchestrator can select the new phase; a phase with no phase-map row is unreachable.
3. **`SKILL.md`** — the Phase Model table + Flow if the dispatch order / checkpoints change; the `description` triggers if the new work is user-invokable.
4. **`shared/preamble.md` pointer** — every role must read the preamble; doc-roles also read `html-output.md` + `ac-status.md` + `jira-ref.md` + their templates. A **non-doc-role** (e.g. Librarian) reads its own defs/template (`shared/knowledge-base.md` + `templates/knowledge-file-template.md`) instead — it emits markdown, not HTML; never point it at `html-output.md`.
5. **Cross-references** — if you rename a section other files cite (e.g. `ac-status.md §4`, `phase-map.md § Re-entry`), grep and fix every citation. Copy-verbatim carries old names — check `.md` *and* asset comments.
6. **Repo root** — README trigger table + `hooks/session-start` overview block (per root `CLAUDE.md` § Editing skills) if the trigger surface changed.

## Verify before commit

1. **Gate grep before/after** — count must be identical:
   ```
   grep -rohE '\b(BA|AR|SEC|CR|SA|Q|D|CS|KB)[0-9]+\b' skills/neo/references skills/neo/SKILL.md | sort | uniq -c
   ```
2. **Thai/non-ASCII scan = 0** (snippet above).
3. **Cross-ref integrity** — every `<file> §<section>` citation still resolves (grep the section headings); incl. the KB citations (`knowledge-base.md`, `librarian.md`, `preamble.md §5`, `jira-ref.md §7`, `phase-map.md § Ingest-first guard`, `html-output.md §8`).
4. **Asset gate** (if you touched `assets/` or HTML) — run `lint.py` + `docverify.py` on a sample `docs/design/<usecase>` and confirm `PASS`. If you touched the api-spec, run `apispeccheck.py` on a sample `docs/api/` (the Phase-0 samples are at `docs/api-spec-redesign/samples/`) and confirm `PASS`.
5. **Runtime proof** (only the user can do this) — reinstall (`/plugin marketplace update neo` → uninstall → install), then `/neo create AC for <usecase>` + an MR-review dry-run; confirm dispatch + lint/docverify PASS + English output.
6. **Bump `version`** in `.claude-plugin/plugin.json` + `marketplace.json` (root `CLAUDE.md` § Before every commit). Don't reuse the `neo` skill `metadata.version` for that — they're separate.
