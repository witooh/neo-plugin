---
name: bug-hunter
description: >-
  Hunts for latent defects in product code that no gate covers and nobody has reported — the gap
  between "every acceptance criterion passes" and "the code is right". Works six grounds, each
  with a runnable command that lists candidates: requirement fidelity against `docs/knowledge/`
  (did the spec misread the card or the upstream contract, so the code faithfully implements a
  misunderstanding), contract surface never exercised, money and decimal arithmetic, calendar and
  timezone arithmetic, idempotency and concurrency, and unvalidated upstream responses. Use when a
  card is built and green and you want to know what it still gets wrong, before a risky release,
  when inheriting unfamiliar code, or periodically against a service. Every finding must be a
  failing test or an evidence-backed note on why it cannot be triggered; confirmed findings go to
  the BUG flow. Not for a reported bug (`diagnosing-bugs`), a diff review (`code-review`), or
  auditing a gate (`falsifying`).
---

# Bug Hunter

The AC gate proves every acceptance criterion has a test. It says nothing about the behaviour the
criteria never mentioned — and that is where the defects live once a card goes green.

Measured on a real card: it passed its AC gate with zero uncovered criteria while
`BOT_LIMIT_EXCEEDED` — an error code named in its own acceptance criterion, present in the API
contract, implemented in Go — was asserted by exactly **zero** tests. Nothing was broken according
to any gate.

Scope is the **product**. For defects in the gates themselves, use `falsifying`.

## Rules of the hunt

- **Every ground starts with a command**, not with reading. If a ground cannot produce a candidate
  list mechanically, it does not belong here.
- **A candidate is not a finding.** Confirm it by making the code do the wrong thing, or record
  why it cannot be reached, with evidence.
- **Never fix in the hunt.** A confirmed finding goes to the BUG flow: `diagnosing-bugs` for the
  cause, `tdd` for the repro. Hunting and fixing in one pass produces neither.

## Ground 1 — requirement fidelity (start here)

`docs/tasks/<card>/spec.md` is an **interpretation**. If it misread the card or an upstream
contract, the code implements that misunderstanding faithfully, every test agrees with it, and
every gate is green. This is the deepest defect class and the only one no gate can reach — the
source of truth for it is `docs/knowledge/`, which holds the ingested originals: contracts,
verbatim requirement captures, and their provenance.

```
code ← api-spec ← spec.md ← docs/knowledge/{contracts,requirements}/ ← the card
```

The mechanical half — every enum, code, and constant the contract promises that appears **nowhere**
in the ingested originals. Each hit was invented downstream by a person or a model, and no test
ever disagreed with it:

```bash
for c in $(grep -rhoE '"[A-Z_]{6,}"' docs/api/*/*.yaml | tr -d '"' | sort -u); do
  grep -rqi "$c" docs/knowledge/ || echo "$c"
done
```

An empty result is a real result here, so confirm the check still bites before trusting it: add a
fake code to a scratch copy of the spec and check it is listed.

The judgment half — walk the chain and compare meaning, not shape:

Ask, for each rule the code enforces:

- **Is it in the ingested source at all?** A rule the code enforces that appears nowhere upstream
  was invented — by a person or a model — and nobody noticed because it never contradicted a test.
- **Did a value survive the trip?** Thresholds, enums, error codes, field names, units, and
  currency scale are where interpretation quietly changes a number. Compare the literal in the code
  against the literal in the ingested contract.
- **Did a conditional get flattened?** "Required when X" becoming "required", "at most one of"
  becoming "exactly one", an optional field treated as mandatory — each passes review and changes
  behaviour.
- **Did a decision drift from what was decided?** `spec.md` records decisions with dates. Check the
  code matches the *latest* one; a superseded decision that stayed implemented is invisible to
  every gate.
- **Is the ingested copy stale?** Check `fetched_at`/version against the live source. A contract
  re-issued upstream since ingest means the code is correct against a document that no longer
  exists.

When the card itself is reachable, read it (`atlassian`) and compare against the knowledge entry —
ingestion is a transcription step and transcriptions lose things.

## Ground 2 — contract surface never exercised

Everything the contract promises but nothing tests. Mechanically diffable:

```bash
# error codes declared in the API spec
grep -h "code:" docs/api/*/*.yaml | sed 's/.*code: *//;s/[",]//g' | sort -u > /tmp/declared
# error codes any e2e actually asserts
grep -rhoE '"[A-Z_]{6,}"' tests/e2e/specs/*.ts | tr -d '"' | sort -u > /tmp/asserted
comm -23 /tmp/declared /tmp/asserted
```

For each code left: does Go ever return it (`grep -rl <CODE> internal/ --include=*.go`)? Three
outcomes, three different bugs — declared and implemented but untested; declared and never
implemented; implemented and undeclared.

## Ground 3 — money and decimal arithmetic

```bash
grep -rn "float\|Round\|Trunc\|ParseFloat\|/ 100\|\* 100" internal/ --include=*.go | grep -v _test
```

Rounding direction and half-way behaviour; the boundary between wire format and domain type;
values at the scale limit (two decimal places, the largest amount the field accepts); a sum of
rounded parts against a rounded sum; negative and zero where only positive was imagined.

## Ground 4 — calendar and timezone arithmetic

```bash
grep -rn "AddDate\|time.Now\|LoadLocation\|Truncate(24\|civil\|Date(" internal/ --include=*.go | grep -v _test
```

Go's `AddDate(0, 1, 0)` on 31 January yields 2 or 3 March, not 28 February — normalisation, not a
bug, and surprising enough that specs acknowledge it in prose and tests skip it. Hunt month-end
dates, month lengths, leap day, the boundary between a civil date and an instant, and any place a
local date is derived from a UTC clock without an explicit location.

## Ground 5 — idempotency and concurrency

```bash
grep -rn "idempotenc\|PENDING\|Transactor\|BEGIN\|FOR UPDATE\|sync\.\|go func" internal/ --include=*.go | grep -v _test
```

The broadest ground — measured at ~70 hits on one service, so narrow to the paths that write, then
widen only if nothing turns up.

The same request twice, concurrently rather than sequentially; a retry after a timeout whose
outcome is unknown; a partial write when the second statement fails; a state machine entered twice
from different transitions. Races need a failing concurrent repro before any lock — a speculative
mutex hides the bug rather than fixing it.

## Ground 6 — upstream responses taken on trust

```bash
grep -rn "json.Unmarshal\|Decode(" internal/adapters/gateway/ --include=*.go | grep -v _test
```

A field the upstream marks optional but the code dereferences; an enum with a value the switch
does not handle; an empty list versus a null; a numeric string; an HTTP 200 carrying a business
error in the body. Compare against the ingested contract in `docs/knowledge/contracts/`, not
against what a sample response happened to contain.

## Report

Per finding: the ground, the candidate command that surfaced it, the confirmation (a failing test,
or why it cannot be reached), and the impact in one line. Then the grounds worked and what each
turned up — including the ones that turned up nothing, so the next hunt starts elsewhere.

## Rationalizations

| Thought | Reality |
|---|---|
| "All ACs pass, the card is done" | The ACs are the questions someone thought to ask. This hunts the rest. |
| "The spec says so" | The spec is an interpretation of the card. Ground 1 exists because it can be wrong. |
| "That error code can't happen in practice" | It is in the contract. Either prove it is unreachable, or test it. |
| "Money maths is simple" | Rounding, scale, and wire format each have a boundary, and money is where a boundary costs. |
| "I'll fix it while I'm here" | Confirm, hand to the BUG flow, keep hunting. Fixing mid-hunt loses both threads. |
| "Nothing found, so nothing's wrong" | Record which grounds you worked. An unworked ground is not a clean one. |
