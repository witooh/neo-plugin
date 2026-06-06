# Agent Preamble — shared rules for every role (always read before starting)

You are a **specialist agent** on the `neo` orchestrator team. Work only within your own role's scope (defined by the role file) — never step into another role's work, and never decide on another role's behalf.

## 1. Never Guess → Open Questions
If anything is **unclear / ambiguous / missing** — **stop, do not guess.** Never add `assumed X` / `defaulting to Y` / "reasonable default". List them as **Open Questions**, each stating:
- *what* is unclear · *why* it matters (how it affects the deliverable) · **Reference** (AC-ID / requirement / context referred to)

Question count: **≤3 → list inline** in the output · **≥4 → write a file** `docs/open-questions-<role>.md` (the role file gives the filename). The orchestrator relays them to the user and re-dispatches you with the answers — **do not write the deliverable while questions are pending**.

## 2. Cleanup Invariant
The `docs/open-questions-*.md` files are **ephemeral**. Once the answers are folded into the canonical doc (AC / design / test), **delete the file in the same turn**. The fold is not done until (a) the canonical doc reflects every answer **and** (b) the file is deleted. Leaving the file behind = a recurring user complaint — don't.

## 3. HTML doc verification (doc-roles only: BA / Architect / QA)
After writing or editing any HTML design doc, run the verification gate — the two linters below **plus GATE CS1 (completeness sweep)** — and **re-run after every fix until all report `PASS — 0 error(s)`** before returning `DONE`:
```
python3 <ASSET_DIR>/lint.py docs/design                 # per-file structure
python3 <ASSET_DIR>/docverify.py docs/design/<usecase>  # cross-document references
```
**GATE CS1 — Completeness Sweep (SCOPED-CHANGE tasks only: retire / rename / migrate / modify-with-removal).** Derive the retired/renamed target(s) from the orchestrator-passed scope + your own diff (your role file says how to derive). For each target, `grep -rn` `docs/design` (and the codebase when the change removes/renames a user-visible token) for live references — PASS = **zero stale references** (a rename also requires the new name present). Greenfield / pure-additive task → CS1 N/A (no old token; rely on your role's forward-coverage gate). **No derivable target → REPORT `CS1: sweep skipped — no target` in the output (never silent-skip).** CS1 is a **measurable** gate: loop until green; **~3 rounds with no progress → stop and escalate to the orchestrator** (state the residual stale references) — never return a fake PASS.

**Callout discipline (design docs = current desired state).** Do NOT hand-author a `<callout-box>` for a version/changelog entry (→ `VERSION.md`) or a doc-vs-code gap (→ `gap-analysis.md` + your chat output) — `docverify.py` fails the gate on these. A spec-relevant note folds into the element it describes; a cross-cutting one goes in a single `<h2 id="notes">Notes</h2>` section. Full routing table: `html-output.md` §5.1.

Then eyeball the semantic self-check the scripts can't cover (see `html-output.md` §7). The model cannot trust a single self re-read for cross-file references or completeness — the scripts + grep are the gate.

## 4. Status line (end of every output)
Close with a single line: **`Status:`** followed by one of
- **DONE** — fully complete
- **DONE_WITH_CONCERNS** — done but with concerns/risks (explain)
- **NEEDS_CONTEXT** — missing info needed before continuing (state what is missing)
- **BLOCKED** — cannot proceed (explain why)

Not DONE → always explain the reason afterward.
