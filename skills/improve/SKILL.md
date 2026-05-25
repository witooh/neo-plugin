---
name: improve
description: Iteratively improve any output until a clear finish-line condition holds — autonomous loop modeled on Claude Code's `/goal` command. Establish ONE measurable completion condition up front (with adaptive questioning if vague), then run improve → self-evaluate → loop until the condition is met or the bound is reached. After each iteration the evaluator returns a yes/no + one-sentence reason; if "no", that reason becomes the next iteration's directive. Use to refine code, prose, data, config, design, or any artifact against a verifiable end state. Triggers on phrases like "improve this", "make it better", "iterate", "refine", "keep improving", "not good enough yet", "optimize this", "polish this", "tighten this up", "ปรับปรุง", "ทำให้ดีขึ้น", "ยังไม่ดี", "แก้ให้ดีกว่านี้", "iterate ต่อ", or when the user provides criteria and wants repeated improvement until they're satisfied. Also use when the user gives feedback on output and expects continued refinement, even without saying "improve" explicitly.
compatibility:
  environment: claude-code
  tools:
    - AskUserQuestion
metadata:
  version: "4.0"
---

# Improve

Set a finish-line condition for any output, then run an autonomous improve → evaluate loop until the condition holds. Modeled on Claude Code's `/goal` — the condition itself is the directive, and a fresh self-evaluation after each iteration decides whether to keep going.

## How It Works (TL;DR)

1. **Finish line** — Establish ONE measurable completion condition with an explicit check and a bound
2. **Improve** — Make one focused change targeting the condition
3. **Evaluate** — Self-check against the condition: `met` / `not met` + one-sentence reason
4. **Loop or stop** — If met → deliver. If not → the reason becomes the directive for the next iteration.
5. **Bound lives in the condition** — e.g., "…or stop after 5 iterations"

This skill stays **autonomous** between iterations: no user checkpoint mid-loop. The condition is the contract. The user can interrupt at any time with "stop" / "good enough".

## Tools

| Tool | Purpose |
|---|---|
| `AskUserQuestion` | Ask the user ONE question at a time to nail down the condition, using the `options` array. |

Use `AskUserQuestion` only during the **discovery phase** (before the loop starts). Once the condition is confirmed, do not pause the loop to ask anything — the loop runs end-to-end and reports back.

## Core Principles

1. **Never improve without a finish line.** A vague directive produces vague output. Establish the condition first; everything else flows from it.
2. **The condition must be verifiable from output alone.** The evaluator does not run external commands during evaluation — it judges only what the iteration has already surfaced (test output pasted into the transcript, file content shown, counts reported, etc.). If a check requires running tests/lint/builds, the iteration step must run them and surface the result.
3. **One measurable end state.** A test result, an exit code, a file count, a word count, a checklist — something Claude can prove in its own output. Not "better" or "cleaner".
4. **Autonomous loop, not user-paced.** No "is this good?" after every iteration — that's what the condition is for. The user agreed to the condition; trust it until met, stalled, bound reached, or user interrupts.
5. **Stop fast when stalled.** If iterations stop making progress, surface it and ask the user to relax/redirect — don't grind.
6. **Bound is mandatory.** Every loop has a max — iterations or wall-clock. No exceptions.

## Workflow

For deeper patterns on writing conditions, evaluator prompts, and stop logic, see [references/CONDITION-GUIDE.md](references/CONDITION-GUIDE.md).

### Phase 1 — Receive

Accept the input and understand it:

- **Existing work** — User provides code, text, or a file path. Read it thoroughly.
- **Raw request** — User describes what they want. Produce a first draft only after the condition is set.

Briefly state what you received (one line) and what current state you observe (one line). **Do NOT start improving yet.**

### Phase 2 — Establish the Finish Line

Try to infer the condition from the user's request first. Users often state the end state without using the word "condition":

| User says | Inferred finish line |
|---|---|
| "Make this faster" | Reduce p50 latency below a target (ask: what target?) — bound 3 iterations |
| "Shorten this README" | Under N lines (ask: what N?) while keeping all section headings — bound 3 iterations |
| "Fix the failing tests" | `npm test` exits 0 — bound 5 iterations |
| "Clean this up" | Vague — must ask. What does "clean" mean (style? size? duplication?) |

When the condition is clear from context, **confirm** in one sentence (Phase 3). When it's vague, ask **1–2 questions max** via `AskUserQuestion` to nail down:

- The measurable end state (e.g., target latency, max lines, test result)
- The check (how to prove it — running tests, counting lines, eyeballing diff)
- Any constraints (what must NOT change — public API, deps, format)
- The bound (default 5 iterations if unspecified)

Combine into a single question when natural. Skip the question entirely if the request already names a clear end state.

### Phase 3 — Confirm

Restate the finish line in one line, then start the loop:

> I'll iterate until **[condition]**, proving it by **[check]**. Constraint: **[what must not change]**. Bound: **[N iterations]**. Starting now.

No need to wait for "yes" — start the loop immediately. The user can interrupt if anything is wrong.

### Phase 4 — Autonomous Loop

Repeat until the condition holds, the bound is reached, or the loop stalls:

**4a. Improve** — Make one focused change targeting the condition (or, on iteration 0, produce the baseline). Explain what changed in one sentence.

**4b. Verify** — Surface the proof: run tests, print line count, show diff, render output — whatever the check requires. The evaluator can only judge what's in the transcript.

**4c. Self-evaluate** — In your own output, give the verdict:

```
Iteration N — [one-line change description]
Verdict: met | not met
Reason: [one sentence — what the proof shows]
```

**4d. Decide:**

- `met` → exit loop, go to Phase 5
- `not met` → the `Reason` becomes the directive for iteration N+1; loop back to 4a
- Stop conditions (see below) → exit loop, go to Phase 5

Keep iterations tight. Don't restate the whole condition every loop — the iteration log is enough.

### Phase 5 — Deliver

Present:

1. The final output (or final state if condition not fully met)
2. A compact iteration log:

```
| Iteration | Change | Verdict | Reason |
|---|---|---|---|
| 0 (baseline) | — | not met | [baseline reason] |
| 1 | [change] | not met | [reason] |
| 2 | [change] | met | [reason] |

Final: [met / stalled / bound reached / user stopped]
```

If the loop ran 3+ iterations, also write the log to `improve-history.md` in the working directory so progress is preserved if context resets.

## Stop Conditions

The loop exits when ANY of these are true:

| Condition | Action |
|---|---|
| Verdict = `met` | Declare success, deliver final output |
| Bound reached (e.g., 5 iterations) | Stop. Deliver best state. Summarize remaining gap and ask if the user wants to extend the bound |
| 3 consecutive iterations with no movement on the condition | Stall. Stop and ask: relax the condition, change approach, or accept current state |
| User says "stop" / "good enough" / equivalent | Respect immediately |
| Condition proven impossible given constraints | Flag the contradiction, ask the user to relax a constraint or drop the condition |

## Writing an Effective Condition

A condition that survives the loop usually has:

- **One measurable end state** — a test result, a build exit code, a count, a checklist item
- **A stated check** — how to prove it: "`npm test` exits 0", "`wc -l < 100`", "no `eslint` errors"
- **Constraints that matter** — what must NOT change: "no public API changes", "no new deps"
- **A bound** — "stop after N iterations" or "stop after T minutes"

Examples:

| Vague | Better |
|---|---|
| "Make this cleaner" | "Reduce to under 100 lines while keeping all tests passing — max 5 iterations" |
| "Faster" | "Reduce p50 latency below 50ms on the bench — max 3 iterations, no API changes" |
| "Better docs" | "Every public function has a docstring with one usage example — max 4 iterations" |
| "Fix this config" | "`yamllint` exits 0 and the file loads in the app without warnings — max 3 iterations" |

For exhaustive patterns and the evaluator prompt template, see [references/CONDITION-GUIDE.md](references/CONDITION-GUIDE.md).

## Asking Questions

Use `AskUserQuestion` with `options` array when the answer space is predictable. One question per call — multiple questions get shallow answers.

Each question needs: a recommended option first labeled `"(Recommended)"`, 2–4 mutually exclusive choices with `label` (1–5 words) and `description` (explains the trade-off).

## Examples

### Example 1 — Clear condition, no questions needed

**User:** "Make `parseDate` handle ISO 8601 with timezone — all tests in `date.test.ts` should pass"

```
Phase 1 — Receive
Read parseDate.ts and date.test.ts. 3 of 12 tests fail on timezone parsing.

Phase 3 — Confirm
I'll iterate until all 12 tests in date.test.ts pass, proving it by running `npm test`.
Constraint: no signature change. Bound: 5 iterations. Starting now.

Phase 4 — Loop
Iteration 0 — baseline run.  Verdict: not met. Reason: 3/12 fail (TZ offset).
Iteration 1 — added offset parsing. Verdict: not met. Reason: 1/12 fails (negative offsets).
Iteration 2 — handle negative offsets. Verdict: met. Reason: 12/12 pass.

Phase 5 — Deliver final + log.
```

### Example 2 — Vague request, one question to nail down

**User:** "Tighten this paragraph up"

```
Phase 1 — Receive
Read the paragraph: 78 words, 4 sentences.

Phase 2 — Question
"What's the target?"
  - Under 40 words while keeping the key claim (Recommended)
  - Active voice only, length unchanged
  - Cut every word that doesn't earn its place — aim for ~50 words

User picks option 1.

Phase 3 — Confirm
Iterating until the paragraph is under 40 words and keeps the key claim. 
Bound: 3 iterations. Starting now.

Phase 4 — Loop
Iteration 0 — 78 words. Verdict: not met. Reason: too long.
Iteration 1 — cut redundancies → 52 words. Verdict: not met. Reason: still over 40.
Iteration 2 — merge sentences 2+3 → 36 words. Verdict: met. Reason: 36 < 40, key claim preserved.

Phase 5 — Deliver.
```

### Example 3 — Stall, ask user to relax

**User:** "Cut this 800-line file under 200 lines while keeping all public API"

```
Iteration 0 → 1 → 2: 800 → 540 → 420 lines (extracted helpers, removed dead code).
Iteration 3 → 4 → 5: 420 → 415 → 410 lines (diminishing returns).

Stall detected (3 iterations < 50 lines progress).

Surface: "Under 200 with the current public API surface looks structurally infeasible — 
the API itself has 180+ lines of signatures. Options:
  1. Relax to <300 lines
  2. Allow public API trimming
  3. Accept current state (410 lines)"
```

## Handling Edge Cases

**Condition met at baseline (iteration 0).** Declare success immediately. Offer to raise the bar if the user wants more.

**User provides feedback mid-loop.** Treat as either (a) a new constraint to add to the condition, or (b) a redirect ("stop, change the condition to X"). Acknowledge and adjust before continuing.

**Constraint conflicts with the end state.** Flag neutrally: *"Reaching X under constraint Y looks impossible — which should give?"* Don't grind.

**Condition is too narrow and creates regressions elsewhere.** Surface the trade-off in the iteration log. If a regression is severe and the user didn't sanction it, treat as a stall and ask.

**User says "improve" with no input artifact.** Ask what to improve. Don't fabricate an artifact to improve.

## What This Skill Does NOT Do

- Does **not** discover goals or explore intent — use `/brainstorm` for that. This skill assumes you can name a measurable finish line (or get to one in 1–2 questions).
- Does **not** pause for user approval mid-loop — the condition is the contract.
- Does **not** run unbounded — every loop has an explicit cap.
- Does **not** auto-detect regression in criteria that aren't named in the condition — if it matters, write it into the condition.
- Does **not** install a session-scoped Stop hook like `/goal` — the loop runs within one skill invocation. For cross-session autonomous goals, use the actual `/goal` command.
