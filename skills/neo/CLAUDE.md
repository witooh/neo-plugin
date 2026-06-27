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

## Invariants

1. **Delegate the SDLC.** neo never picks a skill itself. Each LOOP iteration
   hands off to `using-agent-skills` (via the Skill tool) and lets its router +
   lifecycle decide. neo only compares the result to the exit condition.
2. **The exit condition augments, never replaces.** The Business Analyst's
   exit condition adds the *project-specific* definition of done on top of
   `using-agent-skills` Core Operating Behavior #6 ("Verify, Don't Assume").
   It must not re-state generic verification — that is behavior #6's job.
3. **Maker/verifier is not a neo concept.** The maker/verifier split lives
   inside `using-agent-skills` (its Build-phase and Review-phase skills). neo
   does not define its own maker/verifier roles.
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
   (standalone skill, callable directly as `/ingest <url>`).

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
