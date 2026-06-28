# STATE.md schema

STATE.md is the durable spine of a loop. One file per loop, at
`docs/tasks/<slug>/STATE.md`. The agent forgets between runs; this file does
not. It must be readable by a human (guards against comprehension debt).

## Shape

```markdown
# STATE — <slug>

## Goal
<one-line recursive goal — copied from the exit condition>

## Exit condition
<the project-specific "done"; see references/exit-condition.md>

## Knowledge refs
<files in docs/knowledge/ the loop depends on, with fetched_at>

## Status
framing | primed | looping | blocked | done

## Iterations
### 1
ran:           <lifecycle skills run this iteration, e.g. tdd → code-review>
change:        <one line — what the iteration changed>
evidence:      <artifact path(s) neo read — test report, drift report, build log>
exit_met:      no
next:          <the gap that drives the next iteration>

### 2
…

## Next (when status != done)
<what the resuming run should do first>
```

## Rules

- The Business Analyst owns `Goal`, `Exit condition`, and `Knowledge refs`.
- The loop owns `Iterations` (append-only; never rewrite history).
- `Status` is the only mutable field outside append.
- Keep entries short. STATE.md is a log, not a report — the report is the diff
  the loop produced. If an entry exceeds a few lines, the iteration was too
  big; the next iteration should take a smaller slice.
- A human reading STATE.md top-to-bottom must be able to understand what the
  loop tried, what passed, and what is open. If they can't, the entry failed
  its purpose.
