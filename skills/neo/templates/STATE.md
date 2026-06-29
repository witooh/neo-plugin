# STATE — <slug>

> neo task memory. One file per task. The agent forgets; this file remembers.
> Resume with `/neo continue <slug>`. Schema: `../references/state-schema.md`.

- **slug:** <kebab-id-or-JIRA-or-MR>
- **human_gate:** pending   <!-- pending | passed; neo may not commit/PR until passed -->

## Goal

<one observable sentence — the recursive goal>

## Exit condition

<!-- per-criterion `status` is set by the fresh-context checker only -->
<!-- FEATURE work MUST include the design-exists row below; it is non-waivable. Work that does not add or change behavior omits it. -->

| id | criterion | verify_method | evidence | status |
|----|-----------|---------------|----------|--------|
| ac-1 | <observable statement> | machine | `<cmd>` → <expected> | unmet |
| ac-2 | <observable statement> | judgment | <artifact> → <what "met" looks like> | unmet |
| design-exists | a spec/design doc exists for this feature | judgment | <Define-phase spec/design artifact> → substantive, not an empty stub | unmet |

## Limits

- iteration_cap: 20
- budget: <token / wall-clock, or "ask before open-ended spend">

## Knowledge refs

- <docs/knowledge/...>   <!-- sources ingested for this task -->

## Status

framing   <!-- framing | primed | looping | stuck | done | done-partial -->

## Iterations

<!--
Append-only AUDIT log; one ### block per iteration; NEVER rewrite history.
For inspection, a human reading top-to-bottom must see what was tried, what
passed, and what is still open. If a block runs more than a few lines, the
iteration was too big — take a smaller slice next time.
Run phases in order (Define→Plan→Build→Verify→Review→Ship) — neo drives this
order itself, it is not a menu for the user. A skipped phase records `waiver:` in
place of `ran:` — never a silent skip; the process-integrity gate rejects a change
with neither. A phase is waivable only for work that does NOT add or change
behavior. Define is non-waivable for feature work.
-->

### 1
- ran:      <lifecycle skill(s) this iteration ran, e.g. test-driven-development → code-review-and-quality>
  <!-- if a phase was skipped, use instead: waiver: <reason> (user-approved <date>)  (non-behavior-changing run: one `waiver: trivial — …` may cover all skipped phases) -->
- change:   <one line — what this iteration changed>
- evidence: <artifact path(s) the checker read — test report, build log, drift report>
- exit_met: no   <!-- yes | no — the fresh-context checker's verdict for this iteration -->
- next:     <the unmet gap that drives the next iteration>

## Next

<!-- resume pointer for a NON-terminal status. When the loop reaches a terminal status
(done / done-partial), state DONE here and move any remaining follow-ups to ## Deferred
below — do not pile residual work into this section. A done-partial is resumed FROM
## Deferred (re-framed as a new goal), not from here. -->
<what the resuming run should do first (when status != done)>

## Deferred / out of scope

<!--
Scoped-OUT follow-ups — work this loop deliberately did NOT do. These are NOT exit
criteria (every exit_condition row must still be `met`); they are what remains AFTER the
loop closed for its scope. The MAKER writes this section (deferrals arise during the loop,
like ## Decisions) — not the checker. If ANY item is listed here at close, `status` MUST be
`done-partial`, not `done`. If nothing was deferred, leave this section empty / delete it
and use `status: done`.
-->

**Before prod / needs a decision** (real deferred scope):
- [ ] <what> — <why deferred> (user-deferred <date> | out-of-scope | integration-deferred)

**Post-ship admin** (user-owned — neo leaves these for you):
- [ ] push / open PR or MR / transition the card in JIRA

Resume any of these with `/neo continue <slug>`.
