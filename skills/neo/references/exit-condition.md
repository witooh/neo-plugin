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
  verify_inherit: <#6 Verify is assumed — list ONLY project-specific gates here>
                  e.g. "openapi-doc drift report clean against docs/api/orders"
  out_of_scope:  <explicitly NOT doing, so the loop doesn't creep>
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

## When the exit condition is wrong mid-loop

If the LOOP keeps failing to converge because the exit condition is
unachievable, ambiguous, or the request changed: the loop does NOT grind on.
It pauses, the Business Analyst re-frames, STATE.md is updated, and the loop
resumes from the new condition. The exit condition is mutable by the BA, not
by the loop.
