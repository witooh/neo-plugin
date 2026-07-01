# Condition Guide

Patterns for writing finish-line conditions, structuring the self-evaluator step, and deciding when to stop. Read this when the user's request is vague or when an iteration loop isn't making progress.

This guide pairs with `SKILL.md` — that file owns the workflow; this file owns the *content* of conditions and the *shape* of the evaluator.

---

## 1. Anatomy of a Good Condition

A condition that survives the loop has four pieces. Drop any one and the loop drifts.

| Piece | What it answers | Example |
|---|---|---|
| **End state** | What's true when we're done? | `npm test` exits 0 |
| **Check** | How do we prove it from the transcript? | Run the test command; surface the exit code |
| **Constraints** | What must NOT change while reaching it? | No public API changes; no new dependencies |
| **Bound** | When do we give up? | Stop after 5 iterations or 15 minutes |

If you can't write all four in one paragraph, the condition isn't ready. Ask one more question.

---

## 2. Domain Cheat Sheet

Common shapes by output type. Use as starting points, not laws.

### Code

| Concern | Condition shape |
|---|---|
| Tests | `<test command>` exits 0 with all named tests passing |
| Performance | Benchmark `<name>` p50 ≤ `<target>` ms / function returns in ≤ `<target>` |
| Size / complexity | File under `<N>` lines / cyclomatic complexity ≤ `<N>` |
| Lint / style | `<linter>` reports 0 errors at level `<level>` |
| API stability | No change to function signatures listed in `<file>` / no new public exports |
| Dependency hygiene | No new entries in `package.json#dependencies` / no `import` from `<package>` |

### Prose

| Concern | Condition shape |
|---|---|
| Length | Under `<N>` words while preserving each item in `<key-claims>` |
| Reading level | Flesch-Kincaid ≤ `<grade>` |
| Tone / structure | Active voice in every paragraph / one idea per paragraph |
| Audience fit | A `<persona>` can summarize the piece in `<N>` words after one read |
| Coverage | Mentions every term in `<glossary>` at least once |

### Data / Config

| Concern | Condition shape |
|---|---|
| Schema | Validates against `<schema>` with zero errors |
| Completeness | Every required field in `<list>` is non-null |
| Security | No secret patterns matching `<regex>` / least-privilege per `<policy>` |
| Consistency | All keys follow `<naming-convention>` / sorted alphabetically |

### Design / Visual (markup, styles, templates)

| Concern | Condition shape |
|---|---|
| Accessibility | All interactive elements have ARIA labels / contrast ≥ 4.5:1 measured by `<tool>` |
| Responsive | Renders without horizontal scroll at widths in `<list>` |
| Hierarchy | One `h1`, no skipped heading levels |
| Asset weight | Bundle under `<N>` KB measured by `<tool>` |

---

## 3. Self-Evaluator Pattern

The evaluator step lives in the same skill turn as the improvement. After each iteration's improve+verify, write one block in the transcript:

```
Iteration N — <one-line change summary>
Verdict: met | not met
Reason: <one sentence describing what the proof shows>
```

Rules for the verdict block:

- **`met` requires the proof to be visible in the transcript.** "Tests pass" isn't enough; the test output (or at least the exit code line) must be there.
- **`not met` must say what's missing**, not what's left to do. "3/12 tests still failing on TZ offsets" — not "need to fix timezone handling".
- **One sentence only.** If the reason needs a paragraph, the condition was too broad — pause and renegotiate.
- **No hedging.** "Mostly met" is `not met`. There's no `partial` — that's what the next iteration is for.

The `Reason` from `not met` becomes the directive for iteration N+1. So write it as the next-turn instruction would want to read it: specific, actionable, no fluff.

---

## 4. Vague → Better Rewrites

When the user's phrasing is vague, the skill (or the user) needs to rewrite it before the loop starts.

| Vague request | Concrete condition |
|---|---|
| "Make this cleaner" | Reduce to ≤ 100 lines while `npm test` keeps exiting 0 — stop after 5 iterations |
| "Faster" | Bench `parseRow` p50 ≤ 50ms with no change to its signature — stop after 3 iterations |
| "Better docs" | Every exported function in `<file>` has a JSDoc block with one `@example` — stop after 4 iterations |
| "Fix this config" | `yamllint` exits 0 and the app boots without warnings — stop after 3 iterations |
| "More secure" | No hardcoded secrets per `<regex>`; no IAM wildcards in policy doc — stop after 3 iterations |
| "Smaller bundle" | `dist/main.js` < 200KB gzipped, no removed public exports — stop after 4 iterations |
| "Tighter prose" | Paragraph under 40 words while keeping the key claim about `<X>` — stop after 3 iterations |
| "Looks nicer" | Always too vague to act on — ask: size? alignment? color? hierarchy? then rewrite |

---

## 5. Bound Selection

Default to **5 iterations** unless context suggests otherwise:

| Signal | Bound |
|---|---|
| Single test, small file | 3 iterations |
| Default / general improvement | 5 iterations |
| Large refactor with multiple sub-goals | 8 iterations |
| Time-boxed exploration | Wall-clock instead: 10 / 20 / 30 minutes |
| User specifies | Whatever they say |

Never run without a bound. Never let "just one more iteration" override the bound silently — when the bound hits, stop and surface the gap.

---

## 6. Stall Detection

A stall is **3 consecutive iterations** where the *condition* doesn't move (not the artifact — the artifact may keep changing, but if it doesn't bring the condition any closer, it's a stall).

Examples:

- Condition: "≤ 100 lines". Iterations 3→4→5 produced 412→410→409 lines. Stall (and bound-blocked).
- Condition: "tests pass". Iteration 3→4→5 fix one failing test each but introduce another each time. Stall (no net progress).
- Condition: "no eslint errors". Iterations swap one error class for another (`no-unused-vars` → `prefer-const` → `no-unused-vars`). Stall.

When a stall fires, surface three options:

1. **Relax the condition** — change the target or drop a constraint
2. **Change approach** — restart the loop with a different strategy
3. **Accept current state** — stop and ship what we have

Don't pick for the user; let them choose.

---

## 7. When to Tell the User the Condition Is Bad

Stop the loop early and renegotiate the condition when any of these hit:

- **The check isn't actually visible in the transcript.** "Renders responsively at 1920px" — you can't prove that from text. Either change the check (CSS rule grep, viewport calculation) or accept the condition is unverifiable here.
- **The constraint contradicts the end state.** "Cut the file by 50% with no public API changes" when the public API is 80% of the file.
- **The bound is too small for the work.** If iteration 0's baseline is so far from the end state that 5 focused changes can't reasonably close the gap, say so before iterating.
- **The condition keeps mutating during the loop.** If the user keeps adding "oh, also…" after every iteration, pause: the condition isn't stable, and the loop isn't the right tool. Drop back to `/brainstorm`.

---

## 8. Anti-Patterns

| Anti-pattern | Why it breaks the loop |
|---|---|
| "Improve" with no condition | Becomes drift — every iteration optimizes for whatever Claude noticed last |
| Multiple conditions joined by AND | Each iteration tries to advance both, neither lands. Force-rank into one primary condition and reduce the rest to constraints |
| Condition the evaluator can't see | "It feels cleaner" — no proof, no exit |
| Iterating before reading the artifact | Changes blindly; usually adds problems |
| Skipping the verify step | `met` claimed with no proof — `met` always needs evidence in the transcript |
| Continuing past 3 stalled iterations | Wastes turns. Stall is a signal, not a hurdle |
| Treating the bound as advisory | The bound exists so the loop terminates. If you need more, ask the user to extend it — don't extend it silently |
| Mixing improvement with discovery mid-loop | If the user starts brainstorming new directions, exit the loop, run `/brainstorm`, then re-enter |

---

## 9. Iteration Log Format

After the loop ends (any reason), present this block to the user:

```
| Iteration | Change | Verdict | Reason |
|---|---|---|---|
| 0 (baseline) | — | not met | <baseline reason> |
| 1 | <change> | not met | <reason> |
| 2 | <change> | met | <reason> |

Final: <met | stalled | bound reached | user stopped>
```

If the loop ran 3+ iterations, write the log to `improve-history.md` in the working directory as a backup. Use the same format. This way, if the user resumes later, the history is recoverable even if the conversation context resets.
