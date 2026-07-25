---
name: falsifying
description: >-
  Attacks a green signal to find out whether it can go red at all. Audits the measuring apparatus
  — a gate, checker, coverage number, CI job, or test suite — rather than the product: constructs
  the case that must fail and checks that it does, and diffs every independent source of the same
  fact against the others. Use when a gate or checker is written or changed, when a metric looks
  better than the work feels, before trusting a number in an MR, or when a suite passes on code
  nobody has exercised. Produces a failing case or a source-disagreement table as evidence; a
  confirmed finding is handed to the BUG flow, not fixed in place. Not for a reported bug with a
  symptom (that is `diagnosing-bugs`), not a diff review (`code-review`), and not a hunt through
  product code for latent defects (`bug-hunter`).
---

# Falsifying

Every gate in this repo reports success. None of them proves it could have reported failure.

A gate that cannot fail is not a gate — it is a decoration that costs trust twice: once when it
passes something broken, and again when people learn to ignore it. This skill assumes the green
light is lying and tries to prove it.

Scope is the **apparatus**: checkers, gates, coverage numbers, CI jobs, test suites, dashboards.
For latent defects in the product itself, use `bug-hunter`.

## Technique 1 — make it go red

Take the claim the signal makes, construct the smallest input that **must** contradict it, and run
it. If the signal stays green, the signal is broken.

1. **State the claim in one sentence.** "This gate fails when unit coverage is below 80%."
   Vague claims cannot be falsified; sharpen until the claim names a threshold, a set, or a rule.
2. **Design the counter-case.** The cheapest thing that must trip it: a threshold set above the
   current value, a fixture with the defect deliberately present, an empty input, a duplicate id,
   a value one past the boundary.
3. **Run it and read the exit code**, not the console text. A checker that prints `FAIL` and exits
   0 is worse than one that says nothing.
4. **Ask what a false green would look like** and test that shape specifically. Most broken gates
   fail on a *category* of input, not on a value: matched by a bare name where the name is not
   unique, trusting a subprocess exit code that is always 0, scanning a file range that stops
   short.

Real findings from this technique:

- a coverage gate reported PASS at any percentage because it read `make`'s exit code, and that
  target only printed the number — caught by re-running with the threshold set above the measured
  value
- an AC tripwire matched criterion ids across the whole suite, so a card with no tests at all
  reported full coverage off another card's `AC-001` — caught by running it against a card whose
  test files did not exist

## Technique 2 — diff every source of the same fact

A fact stated in more than one place is a fact that has already drifted somewhere.

1. **Enumerate every source.** For an endpoint path: the router, the router test, the e2e specs,
   the API spec YAML, the generated index, the Bruno collection. Six places, one fact.
2. **Diff them pairwise** and write the table. Do not stop at the first disagreement — measured
   once: three sources disagreed with each other in three different ways.
3. **Decide which one is the truth from evidence**, not from hierarchy. Running code with a
   passing test that exercises it beats a document that describes it.
4. **Check the citations resolve.** A reference to a path, a card, a decision, or an upstream
   contract is a claim; open it. A citation pointing at nothing reads as proof and is not.

## Artifacts — no artifact means it did not happen

A falsification pass reports one of exactly two things:

- **the counter-case**, verbatim, with the output showing the signal going red — or staying green,
  which is the finding; or
- **the source table**, listing each place the fact appears and what it says.

"I reviewed it and it looks correct" is not a result. If a signal could not be falsified, say what
you tried and why it held — that is the useful half of a negative result.

## When to run it

- **Mandatory**: whenever a gate, checker, or verification script is written or changed. Every
  defect this skill was built from lived in a gate, not in the product.
- Before quoting a number in an MR or a status report.
- When a suite passes on code nobody has run, or a metric improves without work that explains it.
- When a task is handed to a subagent whose success criterion is "make the gate green" — that
  brief is satisfiable by an empty test, so audit the result rather than the report.

## Hand-off

A confirmed finding stops here. Fixing it is the **BUG flow**: `diagnosing-bugs` for the cause,
`tdd` for the failing repro, then the fix. This skill produces the symptom that flow needs; it
does not skip ahead to the patch.

## Rationalizations

| Thought | Reality |
|---|---|
| "The gate passed, so we're covered" | The gate passed. Whether it *could* fail is a separate, unasked question. |
| "I wrote the checker, I know it works" | Every gate defect found so far was written by someone who believed that. |
| "The docs and the code disagree, docs are stale" | Maybe. Decide from what runs, and write down which source you picked and why. |
| "Constructing a fake failing case is a waste of time" | It is the only evidence that the gate has any power at all. |
| "One source of truth, nothing to diff" | Count them. Endpoint paths lived in six places. |
