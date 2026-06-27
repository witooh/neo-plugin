# Human gate (commit / PR)

The loop's "done" is a claim until a human confirms it. Nothing auto-merges.
This is neo's guard against cognitive surrender — the failure mode where a
running loop tempts the human to stop having an opinion and just take whatever
comes back.

## When the gate fires

At the end of every loop where the exit condition is met, before the change
leaves the local branch:

- stage the change (`git add`, conventional message)
- open or advance the MR via the `gitlab` skill
- link the JIRA card via the `atlassian` skill
- surface CI status; if CI is red, the loop is NOT done — go back to LOOP

## Escalate (status: blocked) when ANY of these hold

- the exit condition is met but the change touches protected paths / config /
  infra / migrations / anything flagged sensitive by the repo
- CI is green but the verification result from `using-agent-skills` carries
  an unresolved "blocking" or "high/critical" finding that the loop judged
  acceptable — a human must sign off, never the loop
- the request was ambiguous and the BA resolved it with an assumption the
  user has not seen
- the loop exceeded a sane iteration budget without converging (the exit
  condition may be wrong, not the implementation)

When escalating: set STATE.md `status: blocked`, write a one-paragraph
escalation note under `Next`, and stop. Do not keep looping.

## Do NOT escalate (status: done) when

- the change is in-scope, CI is green, verification carried no blocking or
  high/critical findings, and the BA's assumptions are documented in STATE.md
- the MR is open and waiting for review (that is the normal human-gate
  resting state — done means "handed to the human", not "merged")

## The line that does not move

A loop never merges its own work. It opens the door (the MR) and waits. The
human walks through it.
