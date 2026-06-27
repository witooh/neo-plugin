# Loop over `using-agent-skills`

The LOOP step's only job is to hand each iteration to `using-agent-skills` and
let it own the SDLC. neo does not pick skills, does not sequence them, and does
not define a maker/verifier split — those live inside `using-agent-skills`.

## How one iteration hands off

1. neo invokes `using-agent-skills` via the **Skill tool**, passing the current
   goal (from STATE.md) and the latest iteration's findings.
2. `using-agent-skills` runs its own **discovery flowchart** to pick the
   applicable skill(s), follows its **Lifecycle Sequence** to order them, and
   applies the **6 Core Operating Behaviors** throughout (surface assumptions,
   manage confusion, push back, enforce simplicity, maintain scope, verify).
3. It returns: the change made + the verification result it produced (tests
   run, review findings, security findings) — already shaped by its Skill
   Rules ("skills are workflows, not suggestions").
4. neo compares that result to the exit condition (see `exit-condition.md`).
   - **Met** → proceed to the human gate.
   - **Not met** → log the iteration in STATE.md (`next:` = the gap), repeat.

## Lifecycle subset vs full

`using-agent-skills` decides the subset. A bug fix may invoke only
`debugging-and-error-recovery` → `test-driven-development` →
`code-review-and-quality`; a full feature may invoke most of the 16-step
lifecycle. neo does not constrain this — it feeds the goal and reads the
result.

## What neo must NOT do in the handoff

- ❌ Name a specific skill to invoke ("run incremental-implementation") — that
  is `using-agent-skills`' discovery job.
- ❌ Define a maker sub-agent and a separate verifier sub-agent — the
  maker/verifier split is encoded in `using-agent-skills` Build vs Review
  skills, not in neo.
- ❌ Re-state the lifecycle ("spec → plan → build → …") — it lives in
  `using-agent-skills` Lifecycle Sequence.
- ❌ Re-derive operating behaviors — inherit the 6.

If you find neo doing any of the above, stop: the contract is broken and you
are rebuilding the second meta-skill that drifts from upstream.
