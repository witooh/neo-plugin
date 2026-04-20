---
name: improve
description: Iteratively improve any output until measurable criteria are met. Use when the user wants to refine existing work against specific standards — whether it's code, prose, data, config, or any other artifact. Triggers on phrases like "improve this", "make it better", "iterate", "refine", "keep improving", "not good enough yet", "optimize this", "polish this", "tighten this up", "ปรับปรุง", "ทำให้ดีขึ้น", "ยังไม่ดี", "แก้ให้ดีกว่านี้", "iterate ต่อ", or when the user provides criteria and wants repeated improvement until they're satisfied. Also use when the user gives feedback on output and expects you to keep refining, even if they don't say "improve" explicitly.
compatibility:
  environment: claude-code, copilot-cli, kiro-cli
  tools:
    - AskUserQuestion (fallback: ask_user, plain text conversation)
metadata:
  version: "3.0"
---

# Improve

Iteratively improve any output until all criteria are met — with scored evaluation at every step so "better" is never subjective.

## Mode Selection

Choose the mode by counting how many **independent dimensions** the task touches. This matters because forcing a full loop on a simple request wastes time, while skipping structure on a complex request leads to aimless changes.

### Quick Mode

Use when **one clear dimension** drives the improvement — e.g., "make this function faster", "shorten this paragraph", "fix the formatting". The user's request itself implies a single criterion.

1. **Name the criterion** — State it explicitly even though it seems obvious (e.g., "Goal: reduce execution time")
2. **Read and understand** — For code, read the file. For prose, read the text. Don't improve blind.
3. **Make the improvement** — One focused change
4. **Show before/after** — For code: diff or side-by-side. For prose: highlight what changed and why.
5. **Check in** — "Does this hit the mark, or should I keep going?"

**Escalation:** If the user says "keep going" or raises a second concern, transition to Full Mode. Carry the current criterion forward as #1, add new ones, and score the current output as Iteration 0. No work is lost.

### Full Mode

Use when the task involves **2+ independent dimensions**, competing tradeoffs, the user's request is vague ("clean this up", "make it better"), or the user explicitly asks for iterative refinement.

1. Receive input
2. Establish 1-3 ranked, measurable criteria
3. Score baseline (Iteration 0), then iteratively improve — one focused goal per iteration
4. Each iteration: improve → score → user checkpoint → decide (continue/stop)
5. Deliver final output with full iteration history

## Domain Hints

Different output types have different improvement patterns and workflows. Use these as starting points — not rigid rules — when thinking about what "better" means in context and how to approach the improvement.

### Code
**Dimensions:** readability, performance, correctness, test coverage, idiomatic style
**Workflow:** Read the code first → identify the specific issue → make the change → show a diff → run tests if available. For performance improvements, explain the complexity change (e.g., O(n²) → O(n)). For readability, explain what makes the new version clearer.

### Prose
**Dimensions:** clarity, conciseness, tone, structure, audience fit
**Workflow:** Read the full text → identify structural or clarity issues → revise → highlight what changed and why. Show word count before/after when conciseness is a goal.

### Data/Config
**Dimensions:** correctness, completeness, consistency, schema compliance
**Workflow:** Validate against schema or expected format → identify gaps or errors → fix → show what was added/changed/removed. For configs, check for security issues (hardcoded secrets, overly permissive settings).

### Design/Visual
**Dimensions:** alignment, hierarchy, accessibility, responsiveness
**Workflow:** Review the markup/styles → identify visual hierarchy or accessibility issues → fix → describe the visual impact of the change.

When establishing criteria, suggest domain-relevant dimensions the user might not have thought of.

## Asking Questions

Use `AskUserQuestion` (with `options` array when the answer space is predictable) if available. If not, fall back to `ask_user` (with `choices`). If neither is available, ask in plain text — the important thing is to ask, not how you ask.

## Criteria Inference

Before asking the user for criteria, try to infer them from the request. Users often state exactly what they want without using the word "criteria":

- "make this faster" → performance (Quick Mode)
- "this is confusing and too long" → clarity + conciseness (Full Mode, 2 criteria already provided)
- "clean this up" → vague, ask what "clean" means to them
- "improve this README — our onboarding takes forever" → the real criterion is onboarding speed, not README aesthetics

When you can infer criteria, **confirm them** instead of asking from scratch: "I'll focus on [X] and [Y] — does that match what you're after?" This saves a round-trip.

## Core Rules

1. **Never improve without at least one criterion.** Even in Quick Mode, the user's request implies a criterion — name it explicitly.
2. **Always score before AND after** (Full Mode). Every iteration has a scorecard.
3. **One focused goal per iteration.** Closely related changes may go together, but they must serve a single improvement goal. Multiple unrelated changes make it impossible to know what helped.
4. **Target the largest gap first.** Never polish a met criterion while others are unmet.
5. **Detect regressions.** If a previously-met criterion drops, revert or fix before continuing.
6. **Stop when appropriate.** All criteria met, 3 stalled iterations, 10 total iterations (soft max), or user says stop.
7. **User checkpoints matter.** After scoring each iteration, briefly share the scorecard and ask if the user agrees with the assessment. Self-scoring has blind spots — the user's perspective is the ground truth.

## Workflow (Full Mode)

For detailed scoring rubric, scorecard formats, priority rules, and completion conditions: see [references/EVALUATION-GUIDE.md](references/EVALUATION-GUIDE.md)

1. **Receive** — Accept the input (existing work or raw request)
2. **Establish Criteria** — Extract or ask for measurable evaluation criteria (1-3, ranked)
3. **Capture Baseline** — Produce first output, score it (Iteration 0)
4. **Improve** — Make one focused change targeting the largest gap
5. **Evaluate & Checkpoint** — Score the new output, share scorecard with user, confirm alignment
6. **Decide** — Continue, stop, or adjust criteria
7. **Deliver** — Present final output with full iteration history

### Step 1 — Receive

Accept the input and understand what you're working with:

- **Existing work** — User provides code, text, or a file path. Read it thoroughly before proceeding.
- **Raw request** — User describes what they want. Produce the first version, then move to criteria.

Acknowledge what was received and briefly summarize its current state (e.g., "This is a 120-line Go handler that processes webhook events. I notice it has nested error handling and some repeated patterns."). Do NOT start improving yet.

### Step 2 — Establish Criteria

Try to infer criteria from the user's request first (see Criteria Inference above). Then confirm or ask:

- **If criteria are clear from context** — Confirm: "I'll focus on [X] and [Y] — sound right?"
- **If criteria are vague** — Ask: "What's the most important thing to get right?" and "What would make you reject the result?"
- **If criteria > 3** — Force-rank and pick the top 3

A single criterion is fine for focused tasks — don't force the user to invent extra criteria just to hit a number. Suggest domain-relevant criteria the user may not have mentioned (see Domain Hints), but let them decide.

### Step 3 — Capture Baseline

Produce the first output (or use existing work as-is), score it against all criteria, and present to the user with key gaps identified.

### Step 4 — Improve

Make **one focused change** targeting the largest gap. Explain what you're changing and why before making the change.

### Step 5 — Evaluate & Checkpoint

Score the new output against ALL criteria, compare to previous iteration, and check for regressions. Then share the scorecard with the user — they may see things you missed, or disagree with your scoring. Adjust if needed before continuing.

### Step 6 — Decide

Continue if gaps remain, stop if all criteria met, 3 stalled iterations, 10 total iterations, or user says stop.

### Step 7 — Deliver

Present the final output with a summary. Keep tables in English per project conventions:

```
## Final Output

[The improved result]

---

### Iteration History

| Iteration | Change | Total Score | Delta |
|---|---|---|---|
| 0 (Baseline) | — | X / Y | — |
| 1 | [Change description] | X / Y | +W |
| 2 | [Change description] | X / Y | +W |

**Final Score: X / Y**
**Criteria met:** [List]
**Criteria not met (if any):** [List with reason]
```

For long improvement sessions (3+ iterations), write the iteration history to a file (e.g., `improve-history.md` in the working directory) so progress is preserved if context resets. Mention the file path to the user.

## Examples

### Quick Mode Example

**User:** "Make this function faster"
```
1. Goal: improve execution speed
2. Read the function, identify bottleneck
3. Apply optimization
4. Show before/after with explanation
5. "Does this hit the mark, or should I keep going?"
```

### Full Mode Example

**User:** "Improve this README — it's confusing and too long"
```
1. Receive: README.md contents
2. Criteria (confirmed with user):
   - #1 Clarity: a new team member understands the project in under 2 minutes
   - #2 Conciseness: under 200 lines, no redundant sections
3. Baseline: score both criteria, identify key gaps
4. Iteration 1: restructure for clarity (target biggest gap)
5. Checkpoint: share scorecard, ask user if they agree
6. Iteration 2: trim redundant content (next gap)
7. Deliver: final README + iteration history
```

## Handling Edge Cases

**User changes criteria mid-loop:** Accept the change. Re-score the current output against the new criteria and continue from Step 4.

**User provides feedback instead of letting the loop run:** Treat feedback as a new criterion or a signal to re-prioritize. Adjust and continue.

**Output is already perfect (all criteria met at baseline):** Declare success immediately. Suggest the user raise the bar if they want further improvement.

**Criteria conflict with each other:** Flag the conflict: *"Criterion A and B seem to pull in opposite directions. Which should win when they conflict?"*

**User just wants one quick fix:** Use Quick Mode — don't force the full loop.

## What This Skill Does NOT Do

- Does not discover goals or explore intent — it requires clear input and criteria (use `/brainstorm` for discovery)
- Does not guess what "better" means — requires explicit criteria
- Does not make unlimited iterations — has clear stopping conditions
- Does not trade met criteria for unmet ones without user approval
