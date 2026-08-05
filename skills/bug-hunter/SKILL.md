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
  failing test or an evidence-backed note on why it cannot be triggered; confirmed findings include
  copy-pasteable reproduce steps and a proposed fix, then go to the BUG flow (do not fix in the
  hunt). Not for a reported bug (`diagnosing-bugs`), a diff review (`code-review`), or auditing a
  gate (`falsifying`).
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
- **A candidate is not a finding.** Close it by making the code do the wrong thing, by a run that
  shows the behaviour is right, or by recording with evidence why it cannot be reached — the three
  statuses the loop below assigns. A `file:line` citation is none of them; it is what a candidate
  is made of. Impact and severity belong to CONFIRMED rows only, and a candidate that has not been
  through the loop has no status to carry them.
- **Never fix in the hunt.** A confirmed finding goes to the BUG flow: `diagnosing-bugs` for the
  cause, `tdd` for the repro. The report **must** include how to reproduce and a proposed fix so
  the hand-off is actionable — write those, do not apply them. Hunting and editing production code
  in one pass produces neither.

## The hunt loop

The six grounds below are **sources, not steps**. The hunt itself is a loop that closes one
candidate at a time, because the shape that keeps failing is the other one: sweep all six grounds,
collect forty candidates, then label them from memory at the end. Status decided at the end is
status decided by narrative.

**SWEEP** — run the ground commands, collect candidates. Nothing is judged yet; a sweep produces a
list, not an opinion.

**TRIAGE** — rank the list and **declare a budget out loud before the first iteration**. Ground 5
alone measured ~70 hits on one service, so an unbudgeted hunt does not finish. Rank by how wrong
the behaviour would be if the candidate is real, not by how cheap it is to check — cheapness-first
ordering spends the whole budget on the shallow end. Eight iterations is a reasonable opening bid
when nothing argues for another number.

**LOOP — one candidate per iteration.** Never open the next one until the current one has a status:

1. Take the top candidate.
2. Build the check that must go red if it is real — a failing test, a request, a call with the
   boundary value. Borrow the construction techniques in `diagnosing-bugs` Phase 1 rather than
   restating them here, but not its completion criterion: a hunt has no user-reported symptom to
   assert, and a candidate that resists every check becomes BLOCKED and yields the iteration
   instead of stopping the session to ask.
3. Run it. Red → **CONFIRMED**. Green → **KILLED**, with what the green run proves — and keep the
   check: a candidate that came from a coverage gap dies as a defect while leaving behind the test
   that was missing, which is the whole yield of that iteration. Cannot be run at all → **BLOCKED**,
   with the specific reason it is unreachable — "looks fine" is not one.
4. On **CONFIRMED**, before leaving the iteration, capture two fields the BUG flow needs:
   - **Reproduce** — the concrete steps (or command) that made it go red, copy-pasteable. Prefer
     the failing check you just ran; include inputs, expected vs actual, and the `file:line` that
     misbehaves.
   - **Proposed fix** — one concrete approach (where to change, what should happen instead). A
     sketch, not a patch. Do not edit production code here.
5. Write the entry to the ledger, then pick the next candidate.

**EXIT** — budget spent, queue empty, or a CONFIRMED finding whose impact is loss of money, loss of
data, or a security hole, which is handed over immediately instead of finishing the queue. Say
which of the three ended it. A hunt stopped by a stated budget is a complete hunt with a stated
stopping point, not a failed one.

### The ledger

The ledger lives in the conversation, not in a file. One row per candidate, written the moment its
status is decided:

| # | ground | candidate | status | evidence | impact | reproduce | proposed fix |
|---|---|---|---|---|---|---|---|
| 1 | 3 | `Round` on refund split | CONFIRMED | `go test -run TestRefundSplit` — red, 0.01 lost | payout short by a cent per split | `go test ./internal/refund -run TestRefundSplit` with parts `[10.005,10.005]`; want 20.01 got 20.00 at `split.go:42` | round half-up per part with banker's only on the final total; cover in `TestRefundSplit` |
| 2 | 2 | `LIMIT_EXCEEDED` declared, never returned | CONFIRMED | new e2e forces the limit — got `INTERNAL_ERROR` | clients cannot distinguish a limit from an outage | POST create until count=limit+1; expect `LIMIT_EXCEEDED`, got `INTERNAL_ERROR` from `handler.go:88` | map the domain limit error to `LIMIT_EXCEEDED` in the handler; assert in e2e |
| 3 | 6 | gateway retry on partial body | BLOCKED | upstream cannot be made to truncate from the test harness | unknown until a proxy fixture exists | — | — |

Because it is not persisted, restate the whole table at EXIT — that restatement is the report's
spine. A session that ends or compacts mid-hunt takes the ledger with it; that is the cost of
keeping it out of the repo, and re-sweeping is cheaper than a stale file nobody trusts.

## The advisor gate — mandatory, twice

A hunt ends in judgment calls made alone: which candidates count, how hard to label them, when to
stop. That is exactly the shape of work that ships overclaimed. When the `advisor` tool is present
in the session, calling it is not optional here:

1. **Before you leave the loop** — the exit condition has hit and you are about to call the hunt
   done and attach impact. Consult before you write those labels, not after.
2. **Before the report leaves your hands** — draft it first so it survives the round trip, then
   consult, then send. Waiting until someone asks "did you consult?" is the failure this gate
   exists for.

Also consult mid-loop when a candidate will not resolve either way — neither red nor honestly
killed — before writing it off as BLOCKED, or when you are about to abandon the triage order you
declared.

Put what came back into the report: the correction, the reframing, the labels it pushed back on.
If `advisor` is not in the session, do not substitute anything for it — state plainly in the
report that no advisor was available and the findings had no outside reader.

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

The report is the ledger, rendered — not a fresh summary written from memory over it. CONFIRMED
rows first, then BLOCKED, then KILLED (short: what was ruled out and by what run). Severity attaches
to CONFIRMED rows only.

Each **CONFIRMED** row expands beyond the table into a short block — mandatory, not optional:

```
### C<n> — <candidate one-liner>
- **Impact:** …
- **Evidence:** failing check / command and its red output (verbatim enough to re-run)
- **Reproduce:** numbered steps or a single copy-pasteable command + inputs + expected vs actual
- **Proposed fix:** where to change and what correct behaviour looks like (sketch, not a patch)
- **Hand-off:** BUG flow (`diagnosing-bugs` → `tdd` repro first). Do not fix in this hunt.
```

A CONFIRMED finding without **Reproduce** and **Proposed fix** is an incomplete report — the BUG
flow should not have to rediscover either. Reproduce must be something another session can run;
"see above" or a bare `file:line` is not enough. Proposed fix stays advisory: naming the seam and
the intended behaviour is enough; writing the patch is the BUG flow's job.

Around the table: which grounds were swept and what each turned up — including the ones that turned
up nothing, so the next hunt starts elsewhere — how the loop ended (budget / queue / hand-over), and
what is still in the queue unchecked. An unchecked candidate is reported as unchecked, never
dropped.

One line on the advisor gate: consulted (and what it changed), or not available in this session.

## Rationalizations

| Thought | Reality |
|---|---|
| "All ACs pass, the card is done" | The ACs are the questions someone thought to ask. This hunts the rest. |
| "The spec says so" | The spec is an interpretation of the card. Ground 1 exists because it can be wrong. |
| "That error code can't happen in practice" | It is in the contract. Either prove it is unreachable, or test it. |
| "Money maths is simple" | Rounding, scale, and wire format each have a boundary, and money is where a boundary costs. |
| "I'll fix it while I'm here" | Confirm, write reproduce + proposed fix, hand to the BUG flow, keep hunting. Applying the patch mid-hunt loses both threads. |
| "Reproduce is obvious from evidence" | Evidence proves it failed once. Reproduce is the recipe someone else runs cold — write the steps. |
| "Proposed fix means I'm fixing it" | A sketch in the report is hand-off fuel. A patch in the tree is a fix. Only the second is forbidden here. |
| "Nothing found, so nothing's wrong" | Record which grounds you worked. An unworked ground is not a clean one. |
| "I have the file:line, that is my evidence" | It is evidence the code *says* that. A finding claims the code *does* the wrong thing, and that needs a run. |
| "The report is ready — I'll get a second opinion if it's questioned" | The consult belongs before the report, not after the pushback. Afterwards it is damage control. |
| "I'll label the whole sweep once I've looked through it" | That is the batch shape the loop replaced. Forty open candidates end up labelled from memory, and memory grades generously. |
| "Budget's spent but the queue isn't empty" | Then the hunt ends with a queue, stated. Overrunning the budget silently is how a hunt becomes endless. |
