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

**Exit evidence:** all six axes were assessed and no Critical finding is hidden
or silently accepted.

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
