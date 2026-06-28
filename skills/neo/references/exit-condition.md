# Exit condition (Business Analyst)

The exit condition is the **project-specific** definition of "done" for this
loop. It is authored by the Business Analyst at FRAME and checked by neo at the
end of every LOOP iteration.

## It augments `using-agent-skills` behavior #6 — it does not replace it

`using-agent-skills` Core Operating Behavior #6 is "Verify, Don't Assume":
every task is incomplete until verification passes (tests, build, runtime
data). neo inherits that — it never weakens it. The exit condition adds the
**project-specific** layer on top: what does "done" mean *for this task in
this repo*, beyond generic verification.

## Shape (write into STATE.md)

```yaml
exit_condition:
  goal:          <one-line recursive goal — the thing the loop achieves>
  behavior:      <observable done, tied to the request — what a human can see>
  acceptance:    <criteria pulled from the task source (Jira AC, request, etc.)>
  gates:         # project-specific gates only (#6 Verify is already assumed)
    - check:         <what must hold, e.g. "openapi-doc drift clean for docs/api/orders">
      verify_method: machine   # machine = neo reads the artifact; judgment = fresh verifier subagent
      evidence:      <artifact path neo reads, e.g. docs/api/_drift/orders.txt>
  out_of_scope:  <explicitly NOT doing, so the loop doesn't creep>
```

## How neo checks it

Each gate is checked against **evidence**, never the maker's prose claim:

- `verify_method: machine` — neo reads the `evidence` artifact inline (a test
  report's status, an empty drift report, a build log). The truth is external
  and context-independent — a green test cannot be faked by grading nicely — so
  neo can check it in its own context.
- `verify_method: judgment` — the gate needs an opinion ("the code is clean",
  "the UX is acceptable") that the maker's context is too invested to give
  honestly. neo spawns **one fresh verifier subagent** to judge it: the
  maker/checker split applied to the stop condition, and the only verifier neo owns.

Prefer `machine` gates. Reach for `judgment` only when no artifact can settle it.

## Reusable gate templates (use only when the task warrants — non-default)

Copy one of these into `gates:` when the task has the matching artifact. They are
NOT generic verification — behavior #6 already assumes tests-green / review-clean
/ no-high-severity. Each names a check #6 does *not* cover, and each reads an
**outcome** artifact, never an intent one (a written test is not a passing test).

**X6 — execution evidence (scoped-pass ≠ feature-complete).** When the task has
acceptance criteria and a test report:

```yaml
- check:         every Ready AC is traced by >=1 test case that PASSED in the report
  verify_method: machine
  evidence:      <test-report path, e.g. docs/tasks/<slug>/test-report.*>
```

A Ready AC whose only test is failing / deferred / absent fails this gate.
Blocked ACs and their deferred tests are exempt.

**AR4 — requirement coverage count-match.** When an explicit AC / requirement set
exists (hand-waving like "covered by the API" hides gaps):

```yaml
- check:         every AC id maps to a concrete element; coverage count == AC count
  verify_method: machine
  evidence:      <traceability / coverage file the loop wrote>
```

## Completeness rule (the guard)

The exit condition is **incomplete** and must be sent back to the Business
Analyst if:

- `behavior` is not observable (a human can't tell it's done)
- `acceptance` is missing or vague while a task source exists
- it re-states generic verification (tests green, review no blocking,
  security no high/critical) as if those were project-specific — those are
  behavior #6's defaults, not neo's; only name them when they are
  *non-default* for this task
- a gate is missing its `verify_method`, or a `machine` gate names no
  `evidence` artifact for neo to read

## When the exit condition is wrong mid-loop

If the LOOP keeps failing to converge because the exit condition is
unachievable, ambiguous, or the request changed: the loop does NOT grind on.
It pauses, the Business Analyst re-frames, STATE.md is updated, and the loop
resumes from the new condition. The exit condition is mutable by the BA, not
by the loop.
