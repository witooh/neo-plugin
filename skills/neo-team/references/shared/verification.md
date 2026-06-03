# Shared: Document Verification & Fix

**Single source of truth for the verify-before-DONE procedure.** Read this whenever a HARD-GATE in your role file says "run the shared Verification Process." It is referenced by Business Analyst (GATE BA3), Architect (GATE AR3), and QA (GATE Q2). Each role adds its own **role-specific checks** (listed in its own file) on top of this generic procedure — do BOTH.

An unverified document *looks* complete but silently propagates wrong assumptions to every downstream role — worse than no document, because no one questions it. Do not skip this. It applies to **newly created AND edited** documents (e.g. after folding in answers to Open Questions).

## Verification Process

1. **Re-read from disk** — open the document you just wrote/edited with `Read`. Verify against the file, never against your memory of what you intended to write.
2. **Re-read the upstream sources** your document must stay consistent with (e.g. BA's AC document, the API contract, the test-case doc — whichever your role consumes). Cross-check field-by-field.
3. **Verify structure** against your role's template reference file (`acceptance-criteria.md` / `system-design.md` / `test-case-document.md` / `test-execution-report.md`) — every required section and metadata field present.
4. **Verify quality & consistency** — run the **role-specific checks** listed in your own role file (BA: AC quality + Status + JIRA consistency + BR/priority counts; Architect: AC traceability coverage; QA: AC trace + specific status codes + count consistency). No vague outcomes, no implicit rules, no missing failure paths.
5. **Placeholder scan** — search for `TODO`, `TBD`, `[...]`, `assumed`, `default`, `example`, any bracket-enclosed placeholder, and generic field names (`field1`, `string`, `value`). Each one is unfinished content that must be resolved before handoff.
6. **Cross-reference** — every ID in a summary/traceability table matches an item in the body and vice-versa (no phantom IDs, no missing IDs); all counts in summaries match the body. *(For the AC and test-case docs, the summary↔card and cross-file ID resolution is now enforced mechanically by `docverify.py` — step 9; keep hand-checking what it does not parse: the traceability table's AC→design-element mapping and any prose tables.)*
7. **Fix** every issue found, then **re-read** to confirm the fixes landed.
8. **Lint the HTML (per-file structure)** — run `python3 <ASSET_DIR>/lint.py docs/design` until it reports `PASS — 0 error(s)`, then do the **semantic self-check** in [`html-output.md`](../html-output.md) §7. Fix and re-lint until clean. A doc that fails lint has silent breakage (unbalanced tags, unescaped `<`/`&`, `.card` missing `data-status`).
9. **Cross-document check (references between files)** — run `python3 <ASSET_DIR>/docverify.py docs/design/<usecase>` until it reports `PASS — 0 error(s)`. This is the **independent, deterministic** check for the class that neither the per-file linter nor your own re-read can catch, because it lives BETWEEN documents: every `<tc-card traces=>` resolves to an AC that exists, every AC is covered by ≥1 test, a Blocked AC propagates `@blocked` to its TCs, `JIRA Ref` is inherited verbatim (the dedup-union of the traced ACs), and every summary row matches a card. **Stage-aware** — it runs only the correlations whose docs exist, so BA (AC only) gets the within-AC checks and QA (every doc present) gets the full cross-file set. Fix and re-run until clean. *(Author self-review reliably misses dangling cross-references — this script is why you don't have to trust a single re-read.)*

**MUST NOT** return `DONE` until the full process — including a clean `lint.py` **and** `docverify.py` pass — is complete.
