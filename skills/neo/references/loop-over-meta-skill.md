# Running `using-agent-skills` inline

The LOOP step's only job is to run each iteration through the SDLC that
`using-agent-skills` defines — and let *it* own that SDLC. neo does not pick
skills, does not sequence them, and does not define a maker/verifier split for
the build — those live inside `using-agent-skills`. neo just runs them.

## How one iteration runs

1. neo invokes `using-agent-skills` via the **Skill tool** to get the SDLC for
   the current goal (from STATE.md) + the last iteration's gap.
   `using-agent-skills` is **guidance, not an executor** — it does not make
   changes and does not return a result.
2. It supplies its **discovery flowchart** (which skill(s) apply), its
   **Lifecycle Sequence** (what order), and the **6 Core Operating Behaviors**
   (surface assumptions, manage confusion, push back, enforce simplicity,
   maintain scope, verify).
3. neo **runs the chosen skills inline** in its own context, with its own
   `Edit`/`Write`/`Bash`. The work product (reads, edits, test runs) stays in
   neo's context; the durable result is written to disk as **evidence artifacts**
   (test report, drift report, build log, diff).
4. neo checks the exit condition against that evidence (see `exit-condition.md`),
   then logs the iteration to STATE.md as a **pointer, not payload**: a one-line
   change summary + the evidence artifact paths — never a code or transcript dump.
   - **Met** → proceed to the human gate.
   - **Not met** → `next:` = the gap, repeat.
   - **Blocked on missing context** → hand back to the Librarian / BA, not the
     loop (the lifecycle's behaviors #1/#2 say STOP, don't guess).

## Inline by default; isolate only when it pays

neo runs inline because context bloat is handled the same way `using-agent-skills`
handles it when used directly: decompose into thin slices, persist to disk, and
lean on STATE.md resume + the harness's own compaction. Spawn an isolated subagent
for an iteration **only** when a single slice is large enough to bloat the
context — an optional optimization, not the default. (The one routine subagent is
the fresh *judgment* exit verifier in `exit-condition.md`.)

## Lifecycle subset vs full

`using-agent-skills` decides the subset. A bug fix may invoke only
`debugging-and-error-recovery` → `test-driven-development` →
`code-review-and-quality`; a full feature may invoke most of the 16-step
lifecycle. neo does not constrain this — it feeds the goal and runs what the
discovery + lifecycle return.

## What neo must NOT do

- ❌ Name a specific skill itself ("run incremental-implementation") — that is
  `using-agent-skills`' discovery job. neo runs what discovery picks.
- ❌ Define a maker sub-agent + separate verifier sub-agent **for the build** —
  that split is encoded in `using-agent-skills` Build vs Review skills. (neo owns
  exactly one verifier: the fresh *judgment* exit check.)
- ❌ Re-state the lifecycle ("spec → plan → build → …") — it lives in
  `using-agent-skills` Lifecycle Sequence.
- ❌ Re-derive operating behaviors — inherit the 6.

Running the SDLC inline is **not** owning it: neo still consults
`using-agent-skills` every iteration and follows what it returns. If you find neo
picking skills, sequencing them, or re-deriving the behaviors, stop — that is the
second meta-skill that drifts from upstream.
