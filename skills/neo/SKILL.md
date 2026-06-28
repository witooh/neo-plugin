---
name: neo
description: >
  Loop wrapper that turns a software-development task into a recursive goal and
  iterates it against an exit condition until "done" is proven — delegating the
  ENTIRE development lifecycle to the `using-agent-skills` meta-skill (which owns
  skill discovery, the 6 Core Operating Behaviors, and the spec→ship lifecycle).
  neo adds only four things on top: (1) a recursive loop, (2) project memory
  (STATE.md + `docs/knowledge/` via the Librarian and the `ingest` skill),
  (3) a project-specific exit condition authored by the Business Analyst, and
  (4) a human gate at commit/PR. neo is THIN — it never re-derives the SDLC,
  never picks skills itself, never re-states the operating behaviors.
  Triggers: /neo, "neo", a JIRA card id or URL, a GitLab MR URL, or any
  software-development task that benefits from a recursive goal loop with
  durable memory and a human gate. NOT for single-file fixes, quick questions,
  or pure research — answer those directly.
compatibility:
  tools: [Agent, Read, Skill, Edit, Write, Bash, AskUserQuestion]
---

# neo — Loop wrapper over `using-agent-skills`

neo is **not** an SDLC. `using-agent-skills` is the SDLC. neo is the loop that
runs it against a goal until that goal is provably met.

## What neo owns (4 things, nothing more)

1. **The loop** — turn the task into a *recursive goal* and iterate until an
   exit condition holds or the human gate escalates.
2. **Project memory** — `docs/tasks/<slug>/STATE.md` (iteration log) and
   `docs/knowledge/` (curated context), owned by the Librarian.
3. **The exit condition** — authored by the Business Analyst; augments
   `using-agent-skills`' Core Operating Behavior #6 ("Verify, Don't Assume")
   with the *project-specific* definition of done.
4. **The human gate** — commit/PR must pass through a human; risky/ambiguous
   outcomes escalate, never auto-merge.

## What neo delegates (everything else, to `using-agent-skills`)

- Skill **discovery** (which skill applies) → `using-agent-skills` router
- **Lifecycle order** (spec → plan → build → test → review → ship) → `using-agent-skills` Lifecycle Sequence
- **Operating behaviors** (surface assumptions, manage confusion, push back,
  enforce simplicity, maintain scope, verify) → inherited as-is
- **Verification methodology** → `using-agent-skills` Skill Rules + the Verify-phase skills (test-driven-development, code-review-and-quality, security-and-hardening, …)

## The loop

```
/neo <task>
1. INGEST-FIRST GATE (Librarian)
   docs/knowledge/ has the context this task needs?
   ├─ yes → resolve knowledge_refs, proceed
   └─ no  → trigger `ingest` (or ask user) first
2. FRAME (Business Analyst)
   read the task + knowledge_refs → write STATE.md:
     goal:           <one-line recursive goal>
     exit_condition: <project-specific "done"; see references/exit-condition.md>
     knowledge_refs: <files in docs/knowledge/>
3. LOOP — repeat until exit_condition is true or the human gate escalates:
     a. CONSULT `using-agent-skills` (Skill tool) for discovery + lifecycle +
        the 6 behaviors, then RUN the chosen skills INLINE (neo's own
        Edit/Write/Bash) — producing the change AND its verification evidence
        as artifacts on disk (test report, drift report, build log, diff).
        `using-agent-skills` is guidance, not an executor: neo runs it.
     b. neo checks exit_condition against that EVIDENCE (never a self-report):
        machine gates → read the artifact inline; judgment gates → spawn one
        fresh verifier subagent. See references/exit-condition.md.
        ├─ met     → go to step 4
        └─ not met → log the iteration in STATE.md (a pointer, not payload:
                     change + evidence paths; `next:` = the gap). STUCK GUARD:
                     if `exit_met: no` repeated ~3x with the same `next:` gap,
                     STOP → force the human gate (status: blocked); else repeat 3a
     c. INSUFFICIENT CONTEXT — if the lifecycle stops because context is missing
        (behaviors #1/#2: STOP, don't guess), route to the Librarian (ingest the
        missing source) or the BA (reframe if ambiguous) → update knowledge_refs
        in STATE.md → resume 3a. Do NOT re-run the same under-context work.
4. HUMAN GATE — stage the change, open/advance the MR (via `gitlab`), link the
   JIRA card (via `atlassian`), surface CI. Risky or ambiguous → escalate,
   set STATE.md status to blocked. Not risky → set done.
```

## Resume

`/neo continue <slug>` (or a task whose `STATE.md` already exists) — read
STATE.md, show the iteration log, continue from step 3 with the last
`next:` action. The repo remembers; the agent forgets.

## Non-goals (do these WITHOUT neo)

- Single-file fixes, quick questions, pure research → answer directly
- Standalone skill work (`/spec`, `/test`, `/review`, …) → invoke those skills
  directly; neo is only for the recursive-goal loop
- Jira/Confluence ops without a dev task → `atlassian`
- GitLab lightweight MR reads → `gitlab`

## References (point-to-read)

- `references/loop-over-meta-skill.md` — how each iteration runs `using-agent-skills` inline
- `references/exit-condition.md` — how the Business Analyst writes done
- `references/state-schema.md` — STATE.md shape
- `references/human-gate.md` — commit/PR escalation rules
- `roles/business-analyst.md` — exit-condition framer
- `roles/librarian.md` — memory primitive + ingest trigger
- `templates/STATE.md` — the durable spine

## Tools

neo runs the lifecycle inline, so it holds execution tools — it is a loop, not a
pure dispatcher.

Allowed: `Edit`/`Write`/`Bash` (run the chosen lifecycle skills inline + write
STATE.md), `Read` (STATE.md, knowledge, evidence artifacts), `Skill`
(`using-agent-skills` for discovery/lifecycle, `gitlab`, `atlassian`, `ingest`),
`AskUserQuestion` (clarify at FRAME, escalate at GATE), and `Agent` — OPTIONAL,
only for (a) isolating a very long loop's iteration to bound context, or (b) a
fresh judgment-based exit verifier. No per-iteration subagent by default.
