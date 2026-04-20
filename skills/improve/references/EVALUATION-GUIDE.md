# Evaluation Guide

Detailed patterns for scoring, baseline capture, and iteration tracking. Read this file when executing the improvement loop (Full Mode) to understand how to evaluate each iteration objectively.

---

## Establishing Criteria

Criteria come from the user's input:

- **If criteria were provided with the input** — Use them directly after confirming with the user.
- **If a single clear goal exists** — That's enough. Don't force the user to add more criteria just to hit a number. One focused criterion can drive a productive improvement loop.
- **If no criteria exist** — Ask before starting:
  - What's the most important thing to get right?
  - What would make you reject the result?
  - If more than 3, force-rank and pick the top 3.

Every criterion should be **specific and observable**:

| Vague Criterion | Specific Criterion |
|---|---|
| Easy to understand | A beginner can follow it without external help in under 10 minutes |
| High quality | Passes all listed acceptance checks with zero failures |
| Fast | Completes in under 2 seconds for typical input |
| Professional | Matches the tone and structure of the provided reference example |

### Domain-Specific Criteria Examples

When the user's criteria are vague, suggest concrete alternatives based on the output type:

**Code:**

| User Says | Suggest Instead |
|---|---|
| Clean code | Follows project conventions, no duplicated logic, clear naming |
| Performant | Reduces time complexity from O(n^2) to O(n), or completes in <100ms |
| Well-tested | All public methods have unit tests, edge cases covered |

**Prose:**

| User Says | Suggest Instead |
|---|---|
| Better writing | Active voice, one idea per paragraph, grade-8 reading level |
| More engaging | Opens with a hook, uses concrete examples, varies sentence length |
| Shorter | Under N words while preserving all key information |

**Data/Config:**

| User Says | Suggest Instead |
|---|---|
| Fix this config | Validates against schema, no missing required fields, no deprecated keys |
| Make it consistent | Uniform naming convention, consistent indentation, sorted keys |
| More secure | No hardcoded secrets, least-privilege permissions, no wildcard access |

**Design/Visual (CSS/HTML/Templates):**

| User Says | Suggest Instead |
|---|---|
| Looks messy | Consistent spacing, aligned elements, clear visual hierarchy |
| Not accessible | WCAG 2.1 AA compliant: contrast ratio >= 4.5:1, alt text, keyboard nav |
| Make it responsive | Works at 320px-1920px without horizontal scroll or overlapping elements |

---

## Capturing Baseline

Before any improvement, capture the current state as Baseline (iteration 0):

1. **Produce the first output** based on the prompt/task
2. **Score it against each criterion** using the rubric below
3. **Record the scores** — this is the baseline all future iterations compare against

### Scoring Rubric

Score each criterion on a 3-point scale:

| Score | Label | Meaning |
|---|---|---|
| 0 | Not met | Criterion is clearly not satisfied |
| 1 | Partial | Some progress but gaps remain |
| 2 | Met | Criterion is fully satisfied |

### Baseline Scorecard Format

```
## Iteration 0 — Baseline

| Criterion | Score | Evidence |
|---|---|---|
| [Criterion 1] | 0/1/2 | [What was observed] |
| [Criterion 2] | 0/1/2 | [What was observed] |

**Total: X / Y**
**Key gaps:** [List the most impactful unmet criteria]
```

---

## Iteration Evaluation

After each improvement iteration, produce a scorecard in the same format and compare to the previous iteration:

```
## Iteration N

**Changes made:** [What was changed and why]

| Criterion | Previous | Current | Delta |
|---|---|---|---|
| [Criterion 1] | 1 | 2 | +1 |
| [Criterion 2] | 0 | 1 | +1 |

**Total: X / Y (was: Z / Y, delta: +W)**
**Remaining gaps:** [What's still unmet]
**Next action:** [What to improve next, targeting the largest gap]
```

### User Checkpoint

After presenting the scorecard, pause and ask the user if they agree with the assessment. Self-scoring tends to be generous — the user may see issues you missed, or value things differently than you scored them. If the user disagrees, adjust the scores before deciding the next action. This checkpoint is what keeps the loop honest.

---

## Deciding What to Improve Next

Priority order for selecting the next improvement target:

1. **Criterion scored 0** — Not met at all is the biggest gap
2. **Highest-ranked criterion that is not yet 2** — User's priority order matters
3. **Criterion with easiest path from 1 → 2** — Quick wins build momentum

Never improve a criterion that is already scored 2 while others are below 2.

---

## Completion Conditions

The loop ends when ANY of these are true:

| Condition | Action |
|---|---|
| All criteria scored 2 | Declare success, present final output |
| 3 consecutive iterations with zero total delta | Stop — diminishing returns. Ask user to adjust criteria or accept current state |
| 10 total iterations reached | Stop — soft max. Present best result and ask user whether to continue or accept |
| User says "good enough" or "stop" | Respect it immediately |
| A criterion is proven impossible given constraints | Flag it, ask user to remove or relax it, then continue |

---

## Regression Detection

After each iteration, check that NO previously-met criterion has dropped:

- If a regression is detected, **revert the change** or fix the regression before continuing
- Never trade a met criterion for progress on another unless the user explicitly approves

---

## Anti-Patterns

| Anti-Pattern | Why It's Harmful | What to Do Instead |
|---|---|---|
| Improving without scoring first | No way to know if it got better | Always score before AND after |
| Changing multiple things at once | Cannot attribute improvement to a specific change | One focused goal per iteration (related changes OK) |
| Ignoring user's criterion ranking | Optimizes for wrong thing | Follow the user's priority order |
| Continuing after 3 stalled iterations | Wastes time, frustrates user | Stop and discuss with user |
| Polishing a met criterion while others are unmet | Misallocated effort | Target the largest gap first |
| Forcing 3 criteria when 1 is enough | Adds friction, slows down simple tasks | Match criteria count to task complexity |
| Never checking with the user | Self-scoring drifts from reality | Checkpoint after each iteration |
