# Loop Engineering — neo's operational contract

This is the operational detail behind the `## Loop Engineering` section of `SKILL.md`. The
concept primer lives in `LOOP.md` at the repo root (Addy Osmani, *loop engineering*); this file
is how neo actually runs the loop. It does NOT re-derive the SDLC — the lifecycle itself is the
forked router in `SKILL.md`, pointing at the upstream agent-skills lifecycle skills. Loop
engineering "sits one floor above the harness": neo wraps that lifecycle so it runs against a
checkable goal and feeds itself until done.

## The loop neo runs on every invocation

**First move, every `/neo` — before any source-code Edit/Write/Bash.** The loop is not a
concept and not optional; it is the first thing that happens. neo (1) creates or resumes
`docs/tasks/<slug>/STATE.md`, (2) writes the goal + the observable exit condition into it, and
(3) **announces the goal + exit condition to the user as its first output**. `STATE.md` on disk
is the proof the loop ran; the turn-1 announce puts the human in the detection loop immediately
(if neo skips the loop, the user sees no goal/exit and catches it on turn 1). If you are about
to edit source and `docs/tasks/<slug>/STATE.md` does not exist, STOP — you have skipped the
loop; frame it first.

Durable state lives at `docs/tasks/<slug>/STATE.md` (shape: `state-schema.md`; blank copy:
`../templates/STATE.md`). `<slug>` is a short kebab-case name for the task (or the JIRA card id
/ MR id when there is one). Resume = re-read STATE.md and continue from `next_step`; never
restart from zero.

**Resume on `done-partial`.** A `done-partial` task has NO unmet exit criterion — the loop already
closed for its scope — so resuming it is not "continue the open loop" but "open a new scope". On
`/neo continue <slug>` when `status: done-partial`: read `## Deferred / out of scope`, help the
user pick one item (deferred items are not yet exit criteria), then **re-frame that item as a new
goal** — add a new `exit_condition` row (or rows) for it, set `status: looping`, and run the loop
from step 4. When it clears the fresh-context checker + the human gate, tick that item `- [x]` in
`## Deferred` and set `status: done` if nothing remains there, else back to `done-partial`. Never
silently re-open a closed exit: a deferred item becomes work only by being framed into the exit
condition.

1. **Frame the recursive goal.** Restate the task as a single goal sentence in STATE.md. "Make
   the module better" is not a goal; "every acceptance criterion is covered by a passing test
   and `go build ./...` is clean" is.

2. **Author the OBSERVABLE exit condition** (STATE.md `exit_condition`). A list of criteria,
   each:
   - observable — a human or a command can check it true/false, no "seems done";
   - tagged `verify_method: machine` (a command proves it — tests, build, lint, a diff) or
     `verify_method: judgment` (needs a reasoning check — e.g. "the response shape matches the
     AC");
   - tied to its `evidence` — the command + expected result, or the artifact to inspect.

   The exit condition AUGMENTS Core Operating Behavior #6 (the Definition of Done); it never
   replaces it. Confirm the framing with the user when intent is ambiguous — a wrong goal loops
   confidently toward the wrong "done".

   **Feature work carries a non-waivable `design-exists` criterion.** If the task adds or
   changes a feature (not a trivial fix), the exit condition MUST include a row such as
   `id: design-exists | verify_method: judgment | evidence: <the spec/design artifact the
   Define phase produced>`. This is what turns "jumped to Build with no docs" into a *detectable
   unmet exit*: the loop cannot exit while it is unmet, and — unlike an ordinary phase — it
   cannot be waived for features (see the process-integrity gate below + `state-schema.md`).

   **API/HTTP work carries a conditional `e2e-ac` criterion.** If an iteration touches the
   service's **HTTP surface** (a new/changed endpoint, request/response shape, status, or error
   code) AND the project has an e2e process (discover a `tests/e2e` harness), the exit condition
   MUST include a row such as `id: e2e-ac | verify_method: machine | evidence: <the project's real
   e2e run output>`, criterion = "every HTTP-observable Ready AC is covered by a passing e2e test
   (title prefix `[<CARD> - AC-NNN]`)". Route the authoring + running to the `e2e-playwright`
   skill; the evidence is the **real suite run**, so a Go/unit test can never satisfy it. An AC
   that genuinely cannot be observed over HTTP (a log/PII side effect, an internal-only state) is
   excluded from the count as a declared `it.skip` with a reason — and the **fresh-context checker
   validates each exclusion is real** (a testable AC dodged with a skip fails the check). When the
   work is NOT on the HTTP surface (CLI, library, infra-only) or the project has no e2e process,
   record the gate as `out_of_scope` with a one-line reason — never silently omit it. Like
   `design-exists` this lives in the exit condition + the checker (neo-owned); it is **conditional**
   (HTTP surface only), not a blanket rule.

3. **Ingest-first.** If a criterion needs knowledge not on disk (a JIRA card, a Confluence
   spec, an external doc), route to the `ingest` skill first and record the result under
   `knowledge_refs` (→ `docs/knowledge/`). The agent forgets between runs; the repo doesn't.

4. **Iterate.** One pass = run the Skill Discovery flowchart + Lifecycle Sequence from
   `SKILL.md` for the next unmet criterion. Append an `## Iterations` block (append-only, never
   rewrite): `ran:` (the lifecycle skill[s] you ran — the audit trail of *which* SDLC step
   executed), `change:`, `evidence:` (artifact path), `exit_met:`, `next:`. A human reading the
   log top-to-bottom must see what was tried, what passed, and what is open (`state-schema.md`).

   Run the phases in order — Define → Plan → Build → Verify → Review → Ship, and **neo executes
   that order itself; it does not turn the lifecycle into a methodology menu for the user** (see
   "neo drives the flow" below). You may skip a phase, but only by recording a `waiver: <reason>
   (user-approved <date>)` in place of `ran:` for that step — a SILENT skip is malformed and the
   process-integrity gate rejects it. **The waive line is behavior:** a phase may be waived only
   when the task does **not add or change behavior** (a typo, a config / dependency bump, a
   rename, a single-line fix) — that is the only "trivial" that qualifies. Anything that adds or
   changes behavior is **feature work**: the full flow runs and Define is **non-waivable** — do
   not open a Build iteration (`incremental-implementation`) on a feature until the Define
   artifact exists.

5. **Check (maker-checker).** Hand the exit condition + the iteration's evidence to a
   **fresh-context checker** (a sub-agent via the Agent tool, or — when isolation is not worth
   it — a deliberately fresh re-read that ignores your own prior reasoning). The checker decides
   met / not-met **per criterion against evidence**, never on the maker's say-so.
   - `machine` criteria: the checker re-runs the command and reads the real output.
   - `judgment` criteria: the checker reasons from the artifact + the source of truth.

   The checker sets each iteration's `exit_met` and the per-criterion `status` in STATE.md.
   Intercept premature exit: if the maker declared "done" but a criterion is unproven, the
   checker reinjects the task. Self-assessment is the weakest link in a loop; the independent
   checker is the fix.

   The checker ALSO runs the **process-integrity gate** (below) before any exit may pass — and
   its authenticity + `design-exists` judgments MUST run as a real isolated `Agent` subagent,
   never the deliberately-fresh-re-read fallback (those two are exactly the judgments the
   maker's own context is too invested to grade honestly).

6. **Decide — four independent exits:**

   | Exit | Trigger | Action |
   |---|---|---|
   | **Verifier** | every criterion met (checker-confirmed) | → human gate (step 7) |
   | **Progress** | not all met, but this iteration changed state toward the goal | → loop (step 4) |
   | **No-progress** | the last ~3 iterations log `exit_met: no` with the same `next:` gap | → STUCK |
   | **Cap / budget** | iteration count hits the cap, or token / wall-clock budget is spent | → STUCK |

   Pick a cap and a budget up front and write them in STATE.md `limits` (sane defaults: cap
   ≈ 20 iterations; budget = whatever the user set, else stop and ask before an open-ended
   spend). `STUCK` is not failure — it is the loop refusing to burn budget circling a dead end.
   On STUCK, write the blocker + the last evidence to STATE.md and **escalate to the human**
   with a specific question, never a vague "I'm stuck".

7. **Human gate at commit/PR.** neo never auto-commits or auto-opens an MR. Present: the goal,
   the checker's per-criterion verdict + evidence, and the diff summary. The human decides. Only
   on approval do the connectors run — `gitlab` for MR create / review-comment / CI, `atlassian`
   for the JIRA transition. Set `human_gate: passed` in STATE.md after approval.

   Then **close the loop**: record any scoped-OUT follow-up in `## Deferred / out of scope`
   (genuine deferred scope — a user-deferred open question, an out-of-scope concern, an
   integration step this loop could not verify — plus post-ship admin like push / PR / JIRA), and
   set `status: done` if that section is empty or `status: done-partial` if it carries anything.
   Do NOT bury residual work in `## Next`. `done-partial` still means every `exit_condition` row
   is `met` — it flags out-of-scope follow-ups, not an unmet exit — so a reader sees at the top
   that the task closed *for its scope* with named items to resume via `/neo continue <slug>`,
   instead of a bare `done` that reads as "nothing remains".

## neo drives the flow — the only user-facing pauses

The lifecycle is neo's to **execute**, not the user's to choose. neo runs
Define→Plan→Build→Verify→Review→Ship itself and **never presents a "pick your methodology" menu**
("vertical-slice vs build-all-at-once vs plan-first", "design fully then build at once", …). That
decision is already made by the lifecycle skills — `incremental-implementation` means thin
vertical slices, each tested before expanding — so re-offering it to the user is both redundant
and a vector for anti-patterns. Never surface an option that contradicts a Core Operating
Behavior or a lifecycle skill (e.g. "build all the acceptance criteria at once" contradicts
`incremental-implementation`). This concerns the *methodology* choice only; it never overrides
Behaviors #1–2 — genuine goal ambiguity or conflicting requirements are still surfaced.

neo has exactly **three** user-facing pauses; everything else it decides and records to STATE.md:

1. **Goal / intent ambiguity** (step 2) — confirm the framing when a wrong goal would loop
   confidently toward the wrong "done". A goal check, not a methodology choice.
2. **Large-feature plan checkpoint** — for a feature spanning **multiple acceptance criteria or
   multiple layers**, pause **once** after Plan to show the slice plan + AC→test mapping for
   approval before the first Build iteration. For a small or single-slice task, skip this pause
   and proceed. **neo judges the size itself** — it does not ask the user which mode to run — and
   records the approval in that Plan iteration's `### N` block (no new STATE field). This is a
   *plan-approval pause* ("here is the decomposition — ok to build?"), the opposite of a
   *pick-your-methodology menu*.
3. **The commit/PR human gate** (step 7) — the mandatory gate; neo never auto-commits.

The large-feature checkpoint is the one pause added beyond neo's original commit/PR gate: cheap
insurance that catches a wrong decomposition before Build, triggered by neo on size — not a
question posed to the user.

## Process-integrity gate (neo-owned, always on — restored from 3.5.0)

Separate from the exit-condition criteria above: before ANY exit passes, neo verifies the loop
actually **ran the indicated lifecycle skill each iteration** (rather than re-deriving the SDLC
from memory) and that the **lifecycle ran in order** — Define before Build on feature work. This
is neo's own machinery — it owns the loop + the checker — NOT a project gate the exit condition
authors, so it never tensions with "augments #6, never re-states generic verification". It
parallels the always-on no-progress exit: a neo-owned independent check, not a task clause. (It
was shipped at 3.5.0 and dropped in the fork rebuild; this restores it, re-termed for the
embedded router — `ran:` names the lifecycle skill that executed, not a `using-agent-skills`
delegation.)

- **Presence (machine, every exit).** Scan STATE.md `## Iterations`: every change-producing
  iteration carries `ran:` (the lifecycle skill[s] it ran) or a `waiver: <reason>
  (user-approved <date>)`. A change logged with neither → exit FAILS → record it and force the
  human gate.
- **Phase-order (every exit).** For feature work the Define/design artifact must exist before
  the first Build iteration (an iteration whose `ran:` includes `incremental-implementation`, or
  whose diff adds feature source). A Build iteration with no preceding Define artifact and no
  recorded waiver → exit FAILS. Define is **non-waivable for features** — only a task that does
  **not add or change behavior** may waive it, and only with a recorded reason (`state-schema.md`).
- **Consistency (machine, every exit).** `ran:` must square with the iteration's `evidence:` —
  e.g. `ran: test-driven-development` with no test report in `evidence:` is suspect. A named
  skill that left no matching artifact does not pass. Likewise, a non-empty `## Deferred / out of
  scope` at close requires `status: done-partial` (not `done`) — a bare `done` while follow-ups
  are listed is an inconsistency the gate rejects. Likewise, an iteration that changed the **HTTP
  surface** (in a project with an e2e process) must carry the `e2e-ac` criterion with a real e2e
  run in `evidence:` — or a recorded `out_of_scope` reason; HTTP work that closed with no e2e
  evidence is exactly the gap the `e2e-ac` criterion exists to catch.
- **Authenticity (judgment, a real fresh `Agent` subagent — never the self-reread fallback).**
  The fresh-context checker confirms each `ran:` is reflected by the iteration's diff (a change
  the named skill plainly did not shape is rejected) and that the `design-exists` artifact is
  substantive, not an empty stub. These two judgments are too easy for the maker's own context
  to grade kindly, so they MUST run as an isolated `Agent` subagent.

**Honest ceiling.** This is self-enforced — neo writes STATE.md, and the checker reads
artifacts, not neo's transcript. So it makes a skipped phase / consult **visible, dated, and
costly** (faking now means naming a real skill, producing a matching evidence artifact, *and* a
substantive design doc ≈ doing the work) — it does **not** make skipping impossible. The only
structurally-binding layer is a harness PreToolUse hook on Edit/Write, deliberately out of this
skill's scope.

## The three risks (carry them consciously)

1. **Weak verification.** A "done" claim — even the checker's — is not proof; it only reduces
   the risk. Prefer `machine` evidence over `judgment` wherever a criterion can be made
   checkable. If you cannot make a criterion observable, say so at the human gate.
2. **Comprehension debt.** The loop ships faster than a human can read. The human gate is the
   brake: the diff summary and evidence exist so the human stays oriented — not so they can
   rubber-stamp. Read what the loop made.
3. **Cognitive surrender.** Designing the loop is a tool to sharpen judgment, not to avoid
   thinking. The same loop helps one engineer and harms another — the difference is whether a
   human keeps forming an opinion. neo keeps the human in the design-and-review path on purpose.

## Roles (from LOOP.md's "one makes, a different one checks")

- **Maker** — the inline loop (steps 1–4, 7). Holds Edit/Write/Bash; runs the lifecycle.
- **Fresh-context checker** — the independent verifier (step 5). Must NOT inherit the maker's
  context; spawn it fresh (Agent tool) or do a clean-slate re-verification. The
  process-integrity **authenticity** and **`design-exists`** judgments are the exception: they
  require a real `Agent` subagent, never the re-read fallback.
- **Human** — owns the goal framing (when ambiguous) and the commit/PR gate.
- **Knowledge** is not a role — it is the `ingest` skill writing `docs/knowledge/`. There is no
  separate "Librarian / Business-Analyst" role to maintain: the loop owns goal + exit, `ingest`
  owns knowledge.

## What neo does NOT own

neo does not re-derive the SDLC, re-state the 6 Core Operating Behaviors, or pick lifecycle
skills by hand outside the flowchart. Those are the forked router in `SKILL.md`, sourced from
the upstream agent-skills plugin. neo owns exactly four things: the loop, the durable memory,
the exit condition, and the human gate.
