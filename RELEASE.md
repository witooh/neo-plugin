# Release Notes — neo-dev-toolkit

Notable changes per release. The version here tracks the `version` field in
`.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`. Bump that
field on every commit (local-path marketplaces don't auto-update) and add the
matching entry below.

## 0.7.0 — 2026-06-06

### api-doc-gen — two-layer verification + quality pass

Generated API docs are now proven against the code by an independent layer, not
just self-checked, and the skill's instructions are de-duplicated and tightened.

**Added**
- `assets/doccheck.py` (Layer 1) — a stdlib "tripwire" comparing `docs/api/`
  against Go source (endpoint coverage, field count, M/O, JSON + index-link
  validity); confident mismatches → ERROR, unverifiable spots → NOTE for Layer 2
- `references/api-doc-verifier.md` (Layer 2) — a read-only fresh-eyes verifier
  role for the judgment checks a script can't do (error-row tracing, step
  counting, custom types, field-cell correctness, response metadata, structural
  consistency)
- Step 4 rewritten as two layers (script loop → optional fresh-eyes, default
  yes); `Agent` added to the skill's tools; an L1/L2 ownership map in the
  § Verification Checklist

**Changed**
- Fixed an M/O contradiction (non-pointer non-bool without `required` → M
  everywhere) and aligned error row-ordering to 4-tier across SKILL + references
- De-duplicated the M/O, field-description, and step-classification rules — SKILL
  now carries a brief essence and points to the single source in references
- Added edge-case rules: 204/no-body, non-Go halt, monorepo, undocumented-route
  opt-out, inline-query ordering, list/error envelope variants, and handler files
  exporting multiple methods / bound to multiple routes

**Notes**
- `open-collection`'s references to § Verification Checklist / § M/O
  Classification are unchanged (anchors preserved)

## 0.6.0 — 2026-06-06

### Callout discipline — a design doc is the current desired state, not a changelog

Stops the `neo` doc-roles (BA / Architect / QA) from flooding generated HTML
design docs with version-changelog and doc-vs-code-gap `<callout-box>`es that
buried the actual spec content (a real sample had 23 callouts / 0 cards on one
contract page, ~73% of them non-spec). Root cause: no rule said a spec doc holds
only the current desired state, and nothing enforced it — so every doc-review /
verify pass leaked its findings onto the page.

**Added**
- `docverify.py` now enforces callout discipline across **every** page in a
  usecase folder. It previously opened only `acceptance-criteria.html` +
  `test-cases.html`, so `api-contracts.html` — the worst offender — was never
  inspected; it now globs `*.html`:
  - `C1` version/changelog callout on a spec page → **ERROR** (route to `VERSION.md`)
  - `C2` doc-vs-code gap/drift callout → **ERROR** (route to `gap-analysis.md`)
  - `C3` more than 6 hand-authored callouts outside a Notes section → **WARNING**
  - callouts inside `<h2 id="notes">` are exempt (that is the correct home)
  - the classifier pairs a version regex with a strong/weak keyword set; weak
    words (`gap`, `plumbing`, `verified`, `migration`, `drift`, `stale`) need a
    code-pointer co-signal, so legitimate spec prose ("verified against the
    response shape") is not flagged
- `html-output.md` §5.1 — the per-callout routing table (single source of truth)
- `html-output.md` §8 — the `gap-analysis.md` convention (the doc-vs-code drift ledger)
- A `## Notes` section wired into the HTML mapping of all three doc templates,
  as the only on-page home for cross-cutting spec notes

**Changed**
- Every doc-role now has an explicit destination for a flagged conflict:
  changelog → `VERSION.md`; doc-vs-code gap → `gap-analysis.md` + the chat
  response; element-specific note → folded into its element; cross-cutting note
  → the single Notes section
- The Architect's design-doc Verify step now runs `docverify.py` (was `lint.py`
  only), so the callout check covers `api-contracts.html` / `traceability.html`

**Notes**
- No new gate ID — the enforcement rides the existing docverify checks plus the
  CS1 verify gate; the gate inventory stays 18 IDs / 64 occurrences
- Design docs generated before this release will fail the new gate until they are
  regenerated through `neo`; that is intended (they still carry the leaked callouts)

## 0.5.0 — 2026-06-06

### neo verification enhancement

- In-place gate enhancements (neo-only): L1 loop-on-measurable defects, L2
  fresh-eyes verify-only mode folded into the final checkpoint, L3 completeness
  sweep (`CS1`) inside the verify gate
- BA verifies acceptance criteria against the actual source artifacts
  (image / mockup read directly, JIRA card via `acli`), not just the typed text
- Shared references for the verification process, JIRA-ref capture/inheritance,
  and the AC Ready/Blocked status machine

_Earlier `0.1.x`–`0.4.x` releases predate this file; see `git log` for their history._
