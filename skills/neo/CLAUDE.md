# CLAUDE.md — maintaining the `neo` skill

Maintainer notes for editing `neo`. Not loaded at runtime, not shipped to consumers. Read this
before any non-trivial neo edit.

## What neo is (the one rule)

neo is **the upstream `using-agent-skills` meta-skill, forked and customized**, then **wrapped
in a loop**. It is NOT a thin delegator that calls `using-agent-skills` via the Skill tool —
that was the previous generation (now `legacy/neo-loop-wrapper/`). This generation *embeds* the
router in `SKILL.md`.

- The **router half** of `SKILL.md` (Overview, Skill Discovery flowchart, the 6 Core Operating
  Behaviors, Failure Modes, Skill Rules, Lifecycle Sequence, Quick Reference) is **forked from
  upstream `addyosmani/agent-skills` `skills/using-agent-skills/SKILL.md`**. Keep it faithful.
  Only these divergences from upstream are allowed:
  1. the added `ingest` branch (Define — "have a context, need knowledge");
  2. the added `api-spec` branch (Ship — "update api-spec?");
  3. the DoD-path fix in Behavior #6 (upstream cites `references/definition-of-done.md`, which
     lives in the EXTERNAL plugin, not here — inlined instead);
  4. the **removed** `ci-cd-and-automation` and `shipping-and-launch` branches (user opted out —
     won't use them; removed from the flowchart, Lifecycle Sequence, Quick Reference, and the
     Skill Rules example).

  When upstream changes its router, re-fork and re-apply these diffs (re-add ingest/api-spec,
  re-drop ci-cd/shipping, re-inline the DoD). Do not otherwise "improve" the router.

  The mandatory-loop + sequential-phase enforcement (the process-integrity gate, the
  `design-exists` exit criterion, the turn-1 announce) adds **no** router divergence — it lives
  entirely in the loop half (the exit condition + the checker). The router still says "not every
  task needs every skill"; neo's only added discipline is that a skip must be *recorded*
  (`ran:`/`waiver:`), never silent. So there is nothing new to re-apply on a re-fork.
- The **loop half** is neo's own: the `## Loop Engineering` section in `SKILL.md`, plus
  `references/loop-engineering.md`, `references/state-schema.md`, `templates/STATE.md`. Built
  fresh from `LOOP.md` (the repo-root primer). When editing the loop, ground in `LOOP.md`.

## Invariants

1. **Fork, don't delegate.** The lifecycle is embedded here; the lifecycle SKILLS are external.
2. **External prerequisite.** The skills the flowchart points to (`spec-driven-development`, …)
   ship in `addyosmani/agent-skills`, installed separately. neo references them by name; they
   are not in this repo. The validator's `EXTERNAL_SKILLS` allowlist keeps those refs from
   flagging as dead.
3. **The loop has four independent exits** (verifier, iteration cap, budget, no-progress) — not
   one. Removing any one re-introduces open-ended token spend or a dead-end loop.
4. **Maker ≠ checker.** The exit is verified by a fresh-context checker, never by the agent that
   did the work. `exit_condition[].status: met` is the checker's to set.
5. **External memory is load-bearing.** STATE.md is why resume works. Keep it scannable and
   append-only where the schema says so. The `done-partial` status + the `## Deferred / out of
   scope` section (a scope-complete close that still carries recorded out-of-scope follow-ups —
   every `exit_condition` row stays `met`; deferred items are never exit criteria) are neo-owned
   loop machinery: they live in the schema / template / `loop-engineering.md` only, add **no**
   router divergence, and have nothing to re-apply on a re-fork.
6. **The human gate is non-negotiable.** neo never auto-commits / auto-opens an MR. Connectors
   (`gitlab`, `atlassian`) run only after approval.
7. **neo owns only four things:** the loop, the memory, the exit condition, the human gate. It
   never re-derives the SDLC or re-states the 6 behaviors — that is the forked router.
8. **The loop is framed-first; the design artifact is non-waivable for features.** Every `/neo`
   creates/resumes STATE.md and announces the goal + observable exit as its first output, before
   any source edit (the turn-1 announce puts the human in the detection loop immediately). Phases
   run in order; a skip is a recorded `waiver:`, never silent. For feature work the spec/design
   artifact is a non-waivable `design-exists` exit criterion — and it lives in the **exit
   condition + the checker** (both neo-owned), NEVER as a gate bolted onto the forked router.
9. **Every change-iteration is traceable to a ran skill — or a logged waiver (the
   process-integrity gate).** Each change-producing iteration records `ran:` (the lifecycle
   skill[s] that executed) in STATE.md, or `waiver: <reason> (user-approved <date>)` if
   deliberately skipped. A change with neither is invalid; neo's exit carries a standing
   **process-integrity gate** — presence + phase-order + `ran`↔`evidence` consistency (machine,
   every exit) and authenticity (a real fresh `Agent` subagent) — that rejects it
   (`references/loop-engineering.md`). Self-enforced → a silent skip is **visible / dated /
   costly, not impossible**; the only binding layer is a harness hook, deliberately out of scope.
   Don't downgrade `ran:` to a bare boolean. Shipped at 3.5.0, dropped in the fork rebuild,
   restored here — re-termed for the embedded router (`ran:` = the skill that ran, not a
   delegation). Mirrors the no-progress exit: a neo-owned, always-on independent check.

10. **neo drives the flow; the lifecycle is executed, never offered as a menu.** neo runs the
    phase order itself and does not ask the user to pick a methodology ("vertical-slice vs
    build-all-at-once vs plan-first") or surface an option that contradicts a lifecycle skill
    (build-all-at-once contradicts `incremental-implementation`). Its only user-facing pauses are
    goal/intent ambiguity, the **large-feature plan checkpoint** (one approval after Plan, before
    Build, for a feature spanning multiple AC or layers — neo judges the size; small tasks skip
    it), and the commit/PR human gate. The waive line is **behavior-based**: a phase is waivable
    only for work that does not add or change behavior; behavior-changing work is a feature
    (Define non-waivable). Like #8/#9 this is the loop's discipline, not the router's — it lives
    in `SKILL.md ## Loop Engineering` + `references/loop-engineering.md` + the schema/template,
    adds **no** router divergence, and has nothing to re-apply on a re-fork. The "no menu" rule
    forbids offloading the *methodology* choice only; it never suppresses genuine clarifying
    questions (Behaviors #1/#2).

## Adding / removing a router branch — sync list

A branch lives in five places; change all of them together:
1. `SKILL.md` — the Skill Discovery flowchart (use a `──→` arrow so the validator catches the
   ref).
2. `SKILL.md` — the Quick Reference table row (correct Phase).
3. `SKILL.md` — the Lifecycle Sequence (if it belongs in the linear flow).
4. `hooks/session-start` — the neo overview block.
5. `README.md` — the skills table.

Then: if the branch points to a LOCAL skill, ensure its dir is in `skills/`; if EXTERNAL, add it
to `EXTERNAL_SKILLS` in `scripts/validate-skills.js`.

## Verify before commit

- `node scripts/validate-skills.js` → 0 errors, 0 dead-ref warnings (neo is section-exempt).
- `description` (folded) ≤ 1024 chars — the platform injects it into the system prompt.
- 0 Thai in `skills/neo/` — skills are English-neutral; language lives in the user's CLAUDE.md.
- `bash hooks/session-start | python3 -m json.tool` parses — run it whenever you touch
  `hooks/session-start` (the neo overview block must stay valid JSON after escaping).
- The user runs the commit + the marketplace reinstall (`/plugin marketplace update neo` →
  uninstall → install). Do not auto-commit.
