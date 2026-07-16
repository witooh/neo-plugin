# Review, Simplify, Commit, Webperf, and Ship Contracts

Read only the section selected by `using-neo`.

## Review

Review staged changes or recent commits across correctness, readability,
architecture, security, performance, and project conventions.

- With a subagent capability, invoke `code-reviewer` in fresh context. Pass the
  diff, claimed spec/ACs, and the additional Conventions & Style axis.
- Without it, invoke `code-review-and-quality` inline across the same six axes.
- Use Critical / Important / Suggestion severity and anchor every actionable
  finding to `file:line` with a concrete fix.

### Acceptance-criteria gate (conditional)

1. Locate the linked Jira card, task spec, or other source of intent and
   enumerate every claimed AC. If a claimed source cannot be read, mark the AC
   gate blocked; never infer its contents.
2. If no AC exists after checking the linked sources, mark the AC gate `N/A`;
   do not invent ACs.
3. If ACs exist, verify both implementation behavior and test evidence for
   every AC. Emit an `AC -> evidence` table with the AC, implementation
   evidence, test level, test evidence, and status.
4. Classify test evidence as `e2e`, `integration`, `unit-only`, or `none`. For
   every HTTP-observable AC, follow `e2e-playwright`: an active passing E2E test
   is required, and `unit-only` evidence is incomplete. Record why a
   non-HTTP-observable AC uses lower-level evidence.
5. A failed, uncovered, falsely claimed, or HTTP-observable unit-only AC is at
   least an Important finding and forces REQUEST CHANGES. A missing E2E harness
   does not waive this gate.

### Project-wide unit coverage gate

1. Discover and run the project's canonical unit-test coverage command. For a
   project with multiple unit-test stacks, run and report each stack unless the
   repository already defines a canonical aggregate.
2. Require at least 80% project-wide unit line coverage across all first-party
   source. Changed-lines, changed-package, or passing-test counts cannot
   substitute for project-wide coverage, and legacy uncovered code remains in
   scope for the current MR.
3. Respect only existing generated, vendor, and third-party exclusions. Treat a
   new or expanded coverage exclusion in the MR as a finding unless it has an
   independent technical justification; never use exclusions to manufacture
   the threshold.
4. Report the command, measured percentage, scope/exclusions, and verdict. If
   coverage is below 80%, cannot be reproduced, or omits a project unit-test
   stack, raise at least an Important finding and force REQUEST CHANGES; the MR
   must add tests until the whole project reaches the threshold.

**Exit evidence:** all six axes were assessed; the AC gate is complete or `N/A`;
project-wide unit line coverage is reproducibly at least 80%; and no Critical
finding is hidden or silently accepted.

## Simplify

Invoke `code-simplification` on recently changed or explicitly scoped code.

1. Read repository guidance, callers, edge cases, and tests first.
2. Reduce unnecessary nesting, naming ambiguity, duplication, or abstraction
   without changing behavior.
3. Apply one simplification at a time and test after each; revert any step that
   changes behavior.
4. Run the build and re-review through `code-review-and-quality`.

**Exit evidence:** behavior is unchanged, tests/build pass, and the resulting
diff is smaller or clearer rather than merely different.

## Commit

Invoke `git-workflow-and-versioning` for the principles, then act only with user
authorization.

1. Inspect status, staged/unstaged diffs, branch, upstream, and unpushed commits.
2. Group one logical concern per commit and stage precise paths or hunks; never
   use blind `git add -A` or `git commit -am`.
3. Scan staged content for secrets and run the project's test, lint, type-check,
   and build gates.
4. Use a conventional message that explains intent.
5. Verify status and history after committing.

Rebase only local, unshared history and only with confirmation. Treat uncertain
history as shared; never plain-force push.

## Webperf

Use only for browser-facing web apps.

1. Select **Deep** when a Lighthouse/PSI/CrUX report, DevTools trace, or live URL
   with browser tooling exists; otherwise use **Quick** source analysis.
2. With subagents, invoke `web-performance-auditor`; otherwise audit inline
   against `references/performance-checklist.md`.
3. Report only sourced metric values. Label Quick findings `potential impact`.
4. Return a sourced scorecard, ranked findings, positive observations, and
   recommendations. Hand confirmed remediation to `performance-optimization`.

## Ship

Invoke `shipping-and-launch` for the launch checklist.

### Parallel specialist gate

Unless the change is at most two files and under 50 lines with no auth,
payments, data access, or config/env impact, run these three reviews in parallel:

1. `code-reviewer` — correctness, readability, architecture, security,
   performance;
2. `security-auditor` — threat model, OWASP, secrets, auth/authz, dependencies;
3. `test-engineer` — happy paths, edges, errors, concurrency, and coverage.

When parallel subagents are unavailable, run the same passes sequentially. The
main context, never a specialist, merges their results.

### Merge and decision

1. Synthesize Code Quality, Security, Performance, Accessibility,
   Infrastructure, Documentation, and test/build status.
2. If `docs/api/` exists, check implementation drift. Reconcile structural
   drift with `api-spec` Update-from-code while preserving hand-authored
   business fields; refresh `open-collection` and `confluence-api-doc` only when
   those deliverables are maintained.
3. Output `Ship Decision: GO | NO-GO`, blockers, recommended fixes,
   acknowledged risks, specialist reports, and a mandatory rollback plan with
   triggers, procedure, and recovery-time objective.
4. Any Critical finding defaults to NO-GO unless the user explicitly accepts
   the risk. Shipping or deploying always requires explicit authorization.

**Exit evidence:** applicable specialists completed, blockers are visible,
rollback is executable, API deliverables are consistent, and GO has explicit
authorization.
