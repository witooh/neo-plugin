# Shared: JIRA Ref Rules

**Single source of truth for the optional `JIRA Ref` traceability field.** It links an artifact back to the JIRA card(s) (story / task / sub-task / bug) that originated or track a scenario, and flows **AC → test case → E2E test → execution report**. Referenced by Business Analyst (capture), QA (inheritance), `test-case-document.md` / `test-execution-report.md`, and `e2e-playwright.md`.

**The AC document is the single source of truth.** BA *captures* JIRA Refs onto ACs; every downstream role *inherits* them **verbatim** — no one invents, edits, or drops IDs.

## 1. Capture (Business Analyst, at AC-generation time)

- **Default = OMITTED.** If the user's task prompt names no JIRA card, the `JIRA Ref:` line is omitted from every AC body and the AC Summary table's JIRA Ref column reads `—` (em dash). **Never** raise an Open Question asking "which JIRA card is this" — the field is optional by design.
- **Capture trigger.** When the prompt names JIRA card IDs (format `ABC-123` — all-caps project key + dash + integer), capture each ID exactly as written and attach it to the AC(s) the user associates with it. Examples:
  - "create AC for PROJ-123" → every AC of this usecase gets `JIRA Ref: PROJ-123`
  - "AC-002 comes from PROJ-456 and PROJ-789" → AC-002 gets both; other ACs do NOT inherit
  - "Sub-operation 'Activate' tracked by PROJ-501" → every AC under that sub-operation gets it
  - A JIRA URL `https://<host>/browse/PROJ-123` → extract just `PROJ-123`
- **Mapping ambiguity.** If IDs are named but their AC mapping is unclear, raise an Open Question (Never-Guess — preamble §1) asking which AC(s) each ID covers. Do NOT default to "all ACs get all IDs" — that destroys traceability granularity.

## 2. Inheritance (QA test cases, execution report)

- Every test case inherits its `JIRA Ref` from the AC it traces to — copy **VERBATIM** (same IDs, same order, same casing).
- When a TC traces to multiple ACs (rare), write the **deduplicated union** of those ACs' JIRA Refs.
- When the source AC has **no** `JIRA Ref` line → OMIT the `**JIRA Ref:**` line from the TC body entirely (write `—` only in the Summary table column, never in the body).
- The execution report inherits each TC's `JIRA Ref` the same way.
- If you believe a TC needs a JIRA Ref the AC doesn't carry → escalate to the Orchestrator to have BA update the AC document first. **Never add it at the TC layer.**

## 3. E2E bracket prefix (QA, in test code)

Each `it()` block is prefixed `[<TC-ID> - <JIRA-IDs> - <AC-IDs>]: <description>`. The **JIRA segment is omitted** (collapse to `[<TC-ID> - <AC-IDs>]`) when the source AC has no JIRA Ref. IDs come from the TC's inherited value — never re-derived.

## 4. Format rules

- Comma-separated, single space after the comma: `PROJ-123` or `PROJ-123, PROJ-456`.
- **IDs only** — never URLs, titles, or prefixes like `[JIRA]` / `#`.
- Deduplicate within one item (`PROJ-123, PROJ-123` → `PROJ-123`).
- Preserve the user's exact casing of the project key.
- Body line: `**JIRA Ref:** PROJ-123` (omit the line entirely when none). Summary-table column: same list, or `—` (em dash) when none — never blank / `N/A` / a dropped column.

## 5. Persistence on Blocker → Ready promotion

`JIRA Ref` is **sticky** — it persists UNCHANGED across Blocker resolution. Do NOT add/modify/remove JIRA values during promotion **unless** the promotion message explicitly supplies new IDs (e.g. "promote AC-002 with JIRA Ref PROJ-700" → merge per §1 + §4, deduplicate). The Blocker field (upstream dependency) and JIRA Ref (tracking ticket) are independent — resolving one never touches the other.

## 6. Forbidden / never-invent

- **Never invent** a JIRA ID the user did not provide (Never-Guess — preamble §1). If the user said "the JIRA card for login" with no ID, ask which ID — do not write a placeholder.
- `JIRA Ref` is **not** a Blocker substitute — Blocker = upstream dependency that prevents implementation; JIRA Ref = the ticket this artifact was authored against. Both may coexist on one AC.
- Do NOT auto-fill from git branch names, commit messages, or any source the user did not call out as the JIRA reference.

## 7. Content fetch for source-verification (Business Analyst, Spec phase only)

§1-6 govern the JIRA **ID** as a bookkeeping field — the ID is captured and inherited, **never the card's content**. This section is the single exception: when the user points BA at a JIRA card as a **source artifact to verify the AC against** (the orchestrator passes it under `## Source Artifacts` in the dispatch — distinct from JIRA-Ref bookkeeping), BA may **fetch the card's content** to run the BA5 coverage check (each acceptance bullet / description rule in the card → an AC).

- **Fetch** with a read-only `acli` view command through **Bash** (the `atlassian` skill is the acli reference; a general-purpose specialist runs `acli` directly — it does **not** call a Skill). Read the card body only — never transition, comment, or edit the card.
- **Graceful fallback (mandatory).** If `acli` is absent, unauthenticated, or the card is unreadable → **note it in the output and fall back to JIRA-ID-only** (§1). Do NOT hard-fail, do NOT block the AC.
- **Scope: Spec/BA phase only.** MR-review stays local (`phase-map.md` § MR) — never fetch a live card there.
- **Capture rules unchanged.** Fetched content informs the coverage check only; the `JIRA Ref` field still follows §1 (IDs only, never invent, downstream inherits verbatim). **Never** write fetched prose into the `JIRA Ref` field.
