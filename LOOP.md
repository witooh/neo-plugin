# Loop Engineering — A Primer

*A standalone reference on the concept of loop engineering, as named and
structured by Addy Osmani (June 2026). This document explains the idea on its
own terms — it is not specific to any tool or repository.*

---

## TL;DR

Loop engineering is **designing the system that prompts the agent, instead of
prompting it yourself**. You define a task once as a *recursive goal* with a
checkable success condition, and a system iterates the agent — act, check,
decide, repeat — until that condition is provably met. The skill is no longer
writing one good prompt; it is designing a loop whose "done" actually means done.

> "Loop engineering is replacing yourself as the person who prompts the agent.
> You design the system that does it instead." — Addy Osmani

---

## Where it sits: four layers of engineering

Each layer wraps the previous one rather than replacing it.

| Layer | Concern |
|---|---|
| **Prompt engineering** | The words you send in a single turn. |
| **Context engineering** | All the information the model sees (files, history, retrieved docs). |
| **Harness engineering** | The environment a single agent runs inside (tools, sandbox, permissions). |
| **Loop engineering** | The iterative cycle that drives the agent toward a goal — *on its own*. |

Osmani places it precisely: loop engineering "sits one floor above the harness."
The harness is where one agent runs; the loop wraps the harness so it runs on a
timer, spawns little helpers, and **feeds itself**.

The shift it names: for about two years, getting work from a coding agent meant
*you* holding it turn by turn — type a thing, read what came back, type the next
thing. Loop engineering replaces that manual hand with a system that finds the
work, hands it out, checks it, records what is done, and decides the next thing.

Two practitioners crystallized it the same week (June 2026):

- **Peter Steinberger:** stop prompting your agents and start designing the
  loops that prompt them.
- **Boris Cherny** (who built Claude Code): *"I don't prompt Claude anymore. I
  have loops running that prompt Claude and figuring out what to do."*

---

## Inner loop vs outer loop

- **Inner loop** — what a coding agent already runs every turn:
  *perceive → reason → act (edit a file, run a test) → observe → reason again.*
  You get this for free.
- **Outer loop** — the part you actually build: the system that runs the inner
  loop *on a schedule*, feeds it work, checks the result, and decides what is
  next — **without you typing each prompt.**

Two in-session primitives map to this distinction (both now ship as native
commands in coding agents such as Claude Code and Codex):

- **`/loop`** — re-runs a prompt on a cadence.
- **`/goal`** — keeps going until a condition you wrote is *actually true*.

---

## The heart: a recursive goal with a checkable exit

A loop is a **recursive goal**: define the purpose once, and the agent iterates
until the work is genuinely complete. The loop engineer's first job is turning a
fuzzy intention into a goal the system can *verify* — defining not just what to
achieve, but how the system will know it has been achieved.

The success condition has to be **observable**:

| Not a loop goal | A loop goal |
|---|---|
| "Make the code better" | "Make all the tests pass" |
| "Improve the module" | "The linter returns zero errors" |

Without an observable success condition a loop has no exit — and a loop with no
exit is not autonomous work, it is open-ended token spend.

**A robust loop carries several *independent* exits, not one:**

1. **A verifier** that confirms the goal is met.
2. **A hard iteration cap.**
3. **A token / wall-clock budget.**
4. **No-progress detection** — the subtle one. If the last few steps produced
   the same error or left state unchanged, the loop should break and escalate
   rather than burn budget circling a dead end. (A common technique: hash each
   *(action, observation)* pair and compare against the last N steps; if it is
   repeating itself, force-exit with a "stuck" status.)

The opposite failure also exists: **premature exit** — the model subjectively
decides it is done and quits early. The countermeasure is to *intercept the
exit* and re-check real completion criteria (tests green, types clean, coverage
met), reinjecting the task if they are not.

> The whole craft is in making the check real and deciding when to stop.

---

## The five building blocks

Osmani notes a well-engineered loop converges on five components:

1. **Automations** — scheduled discovery and triage that run by themselves. The
   loop's heartbeat: work initiates without you.
2. **Worktrees** — isolated environments so parallel agents "don't step on each
   other," and so nothing touches production directly.
3. **Skills** — codified project knowledge (e.g. the `SKILL.md` format). This
   pays down *intent debt*: written-down intent so the loop **compounds**
   instead of re-deriving the project from zero every cycle.
4. **Plugins / connectors** — hooks into real tools (issue trackers, CI/CD,
   repositories, pull requests), commonly via MCP.
5. **Sub-agents** — separation of roles so *one agent makes and a different one
   checks.*

### The sixth thing: external memory

The model forgets everything between runs, so durable state must live **on disk,
not in context** — a markdown file, a tracker board, anything that records what
is done and what is next.

> "The agent forgets, the repo doesn't."

---

## Maker–checker

The single most valuable structural element is **splitting the agent that writes
from the agent that checks.** A *fresh* model deciding whether the loop is done —
rather than the one that did the work declaring victory — is what gives a
`/goal`-style stop condition any meaning. Self-assessment is the weakest link in
a loop; an independent checker is the fix.

---

## The three risks

An unattended loop is also a loop that makes mistakes unattended. Osmani is
explicit that the concept is double-edged:

1. **Weak verification** — if "done" is not backed by proof, the loop
   confidently ships wrong work. Even a verifier sub-agent only *reduces* this; a
   "done" claim is still not proof.
2. **Comprehension debt** — the loop ships code faster than you can understand
   it, so the gap between what is in the repo and what you actually grasp grows.
   A smoother loop just grows it faster — *unless you read what the loop made.*
3. **Cognitive surrender** — it becomes tempting to stop forming an opinion and
   accept whatever the loop returns. Designing the loop is the *cure* when you do
   it to sharpen judgment, and an *accelerant* for harm when you do it to avoid
   thinking.

The standard mitigations: a separate verifier, **a human kept in the
design-and-review path**, and durable memory a human can read to stay oriented.

---

## Bottom line

> Two people can build the exact same loop and get opposite results. One uses it
> to move faster on work they understand deeply; the other uses it to avoid
> understanding the work at all. The loop does not know the difference — you do.

This is why loop design is *harder* than prompt engineering, not easier: the
leverage point moved, but judgment did not go away. Direct, turn-by-turn
prompting is still effective, and token costs vary wildly — the loop is a tool to
reach for deliberately, not a default to switch on everywhere.

> "Build the loop. But build it like someone who intends to stay an engineer,
> not just the person who presses go." — Addy Osmani

---

## Sources

- Addy Osmani — *Loop Engineering* (canonical essay):
  <https://addyosmani.com/blog/loop-engineering/>
- Addy Osmani — *Loop Engineering* on Substack ("Elevate"):
  <https://addyo.substack.com/p/loop-engineering>
- O'Reilly Radar — *Loop Engineering* (reposted with permission):
  <https://www.oreilly.com/radar/loop-engineering/>
- Data Science Dojo — *Agentic Loops: From ReAct to Loop Engineering (2026)*:
  <https://datasciencedojo.com/blog/agentic-loops-explained-from-react-to-loop-engineering-2026-guide/>
- Tosea.ai — *What Is Loop Engineering? From Prompt to Harness Engineering*:
  <https://tosea.ai/blog/loop-engineering-ai-agents-complete-guide-2026>
- Verdent — *What Is a Loop Engineer in AI Coding?*:
  <https://www.verdent.ai/guides/agent/what-is-a-loop-engineer>
