# neo — maintainer invariants

These are the load-bearing rules for editing the neo skill. Read before any
non-trivial change. Keep neo detail HERE, not duplicated in the repo CLAUDE.md.

## The one rule

**neo is a thin loop wrapper over `using-agent-skills`.** If a change makes
neo own part of the SDLC (discovery, lifecycle order, operating behaviors, or
verification methodology), the change is wrong — that belongs to
`using-agent-skills`, not here. Re-deriving any of it inside neo creates a
*second* meta-skill that drifts from the upstream one and is exactly what
"not really using agent-skills" feels like.

Running the lifecycle **inline** is not owning it: neo still consults
`using-agent-skills` every iteration and follows the discovery + lifecycle it
returns. What's forbidden is *re-deriving* the SDLC, not *executing* it. (neo
implements only the **recursive-goal** half of loop engineering; the
**unattended-automation** half is wrapping neo with Claude Code `/loop` or cron.)

## Invariants

1. **Delegate the SDLC, run it inline.** neo never picks a skill itself. Each
   LOOP iteration consults `using-agent-skills` (via the Skill tool) for the
   discovery + lifecycle, then runs the chosen skills inline with neo's own
   Edit/Write/Bash. Delegation is *who decides* the SDLC (always
   `using-agent-skills`), not *where it executes* (neo's context).
2. **The exit condition augments, never replaces.** The Business Analyst's
   exit condition adds the *project-specific* definition of done on top of
   `using-agent-skills` Core Operating Behavior #6 ("Verify, Don't Assume").
   It must not re-state generic verification — that is behavior #6's job.
   Reusable *non-default* gate templates (X6 execution-evidence, AR4
   coverage-count) live in `references/exit-condition.md` — the BA copies one in
   only when the task's artifacts warrant it, never as a default.
3. **neo owns no build maker/verifier — but owns one exit verifier.** The
   build-time maker/verifier split lives inside `using-agent-skills` (its Build-
   and Review-phase skills); neo defines no build roles. The one exception: a
   `judgment` exit gate is checked by a single fresh verifier subagent neo spawns
   (see `references/exit-condition.md`). Machine gates need none — neo reads the
   evidence artifact inline. (The KB5 ingest-fidelity verifier is a *separate*
   fresh-eyes check at the **ingest layer** — `roles/librarian.md` — not a second
   build verifier; it does not touch this invariant.)
4. **Human gate is mandatory at commit/PR.** Loop outcomes that are risky or
   ambiguous escalate to the human; nothing auto-merges. This is the guard
   against cognitive surrender (see `references/human-gate.md`).
5. **STATE.md is the durable spine.** Every iteration is logged so the loop
   is resumable across sessions and so a human can read what the loop did
   (guards against comprehension debt). The agent forgets; the repo does not.
6. **Two roles only.** Business Analyst (exit-condition framer) and Librarian
   (memory primitive). Architect/QA/Developer/Code Reviewer/Security/System
   Analyzer are RETIRED — replaced by `using-agent-skills` skills and the four
   agent-skills agents (code-reviewer, security-auditor, test-engineer,
   web-performance-auditor). Do not re-add retired roles.
7. **ingest-first is an explicit gate.** Before FRAME, the Librarian checks
   `docs/knowledge/`; if the needed context is absent, `ingest` runs first
   (standalone skill, callable directly as `/ingest <url>`). Ingest fidelity is
   gated: `ingest` self-checks clause coverage (**KB4** — behaviour-constraining
   and contract clauses copied verbatim, untranslated) and the Librarian runs a
   fresh-eyes re-fetch + clause-diff (**KB5**). A dropped clause → BLOCKED.
8. **The loop carries independent exits, not just success.** Per loop-engineering
   (`LOOP.md`), a robust loop needs more than the evidence-checked exit
   condition: it also has a **no-progress / stuck detector** — `exit_met: no`
   repeated ~3 iterations with the same `next:` gap forces the human gate (reads
   the STATE.md `Iterations` log; `SKILL.md` LOOP step + `references/human-gate.md`).
   Don't remove it: a loop with only a success-verifier is open-ended token spend
   on a dead end.
9. **Every change-iteration is traceable to a consulted skill — or a logged
   waiver.** The step-3a consult of `using-agent-skills` must leave evidence:
   each change-producing iteration records `ran:` (the chosen skill[s]) in
   STATE.md, or a `waiver: <reason> (user-approved <date>)` if deliberately
   skipped. A change with neither is invalid; neo's exit check carries a standing
   **process-integrity gate** — presence + `ran`↔`evidence` consistency (machine,
   every exit) and authenticity (the fresh judgment verifier when one runs) — that
   rejects it (`references/exit-condition.md`). This is self-enforced, so it makes
   a silent skip **visible / dated / costly, not impossible**; the only binding
   layer is a harness hook, deliberately out of scope. Don't downgrade `ran:` to a
   bare boolean — naming the real skill (and its matching artifact) is what raises
   the cost of faking. Mirrors #8: a neo-owned, always-on independent exit.

## Add-a-role / add-a-reference sync list

When changing neo's contract, update in lockstep:

- `SKILL.md` (the trigger description + the loop shape)
- `hooks/session-start` (the skill-overview entry injected every session)
- `scripts/validate-skills.js` `SECTION_EXEMPT_SKILLS` (neo uses a
  non-standard anatomy — it must stay exempted)
- `README.md` (the neo row + agent-skills section)
- repo `CLAUDE.md` (the "Skills currently bundled" line)

## Verify-before-commit

Run `node scripts/validate-skills.js` (expect 0 errors; the 2 `local`/`params`
warnings in `open-collection` are pre-existing false positives). Run
`bash hooks/session-start | python3 -m json.tool` (must be valid JSON).
