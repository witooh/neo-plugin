---
name: code-review
description: Review the changes since a fixed point (commit, branch, tag, or merge-base) along two axes — Standards (does the code follow this repo's documented coding standards?) and Spec (does the code match what the originating issue/PRD asked for?). Runs both reviews in parallel sub-agents and reports them side by side. Use when the user wants to review a branch, a PR, work-in-progress changes, or asks to "review since X".
---

Two-axis review of the diff between `HEAD` and a fixed point the user supplies:

- **Standards** — does the code conform to this repo's documented coding standards?
- **Spec** — does the code faithfully implement the originating issue / PRD / spec?

Both axes run as **parallel sub-agents** so they don't pollute each other's context, then this skill aggregates their findings.

A third axis, **Security**, runs only when the diff earns it (see step 3b).

## Process

### 1. Pin the fixed point

Whatever the user said is the fixed point — a commit SHA, branch name, tag, `main`, `HEAD~5`, etc. If they didn't specify one, ask for it.

Capture the diff command once: `git diff <fixed-point>...HEAD` (three-dot, so the comparison is against the merge-base). Also note the list of commits via `git log <fixed-point>..HEAD --oneline`.

Before going further, confirm the fixed point resolves (`git rev-parse <fixed-point>`) and the diff is non-empty. A bad ref or empty diff should fail here — not inside two parallel sub-agents.

### 2. Identify the spec source

Look for the originating spec, in this order:

1. `docs/tasks/<card>/spec.md` — the neo spec. The card comes from the branch name, the commit messages, or the user. This is the normal case; its **ACs** are what the Spec axis checks against.
2. A path the user passed as an argument.
3. A legacy `docs/design/<usecase>/` acceptance-criteria layout.
4. The JIRA card itself, read with `acli` (see the `atlassian` skill), when no spec file exists yet.
5. If nothing is found, ask the user where the spec is. If they say there isn't one, the **Spec** sub-agent will skip and report "no spec available".

### 3. Identify the standards sources

**`.kiro/steering/` is the standards source in this org's services** — not `CODING_STANDARDS.md` or `CONTRIBUTING.md`, which these repos do not have. Read `INDEX.md` (or `AGENTS.md`, depending on the repo) for the guide table, then select the guides whose `fileMatchPattern` matches paths in the diff — e.g. `internal/delivery/http/**` → `handler.md`, `**/*_test.go` → `testing.md`, `**/internal/core/usecase/**` → `usecase.md`. Add `new-feature-checklist.md` when the diff adds an endpoint or a domain.

Those guides are `fileMatch`-scoped, so they are **not** in your context by default and they are **not** in a sub-agent's — you must read them and paste the relevant ones into the sub-agent prompt. If the repo has no `.kiro/steering/`, fall back to any `CODING_STANDARDS.md` / `CONTRIBUTING.md` it does have.

On top of whatever the repo documents, the Standards axis always carries the **smell baseline** below — a fixed set of Fowler code smells (_Refactoring_, ch.3) that applies even when a repo documents nothing. Two rules bind it:

- **The repo overrides.** A documented repo standard always wins; where it endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic ("possible Feature Envy"), never a hard violation — and, like any standard here, skip anything tooling already enforces.

Each smell reads _what it is_ → _how to fix_; match it against the diff:

- **Mysterious Name** — a function, variable, or type whose name doesn't reveal what it does or holds. → rename it; if no honest name comes, the design's murky.
- **Duplicated Code** — the same logic shape appears in more than one hunk or file in the change. → extract the shared shape, call it from both.
- **Feature Envy** — a method that reaches into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps** — the same few fields or params keep travelling together (a type wanting to be born). → bundle them into one type, pass that.
- **Primitive Obsession** — a primitive or string standing in for a domain concept that deserves its own type. → give the concept its own small type.
- **Repeated Switches** — the same `switch`/`if`-cascade on the same type recurs across the change. → replace with polymorphism, or one map both sites share.
- **Shotgun Surgery** — one logical change forces scattered edits across many files in the diff. → gather what changes together into one module.
- **Divergent Change** — one file or module is edited for several unrelated reasons. → split so each module changes for one reason.
- **Speculative Generality** — abstraction, parameters, or hooks added for needs the spec doesn't have. → delete it; inline back until a real need shows.
- **Message Chains** — long `a.b().c().d()` navigation the caller shouldn't depend on. → hide the walk behind one method on the first object.
- **Middle Man** — a class or function that mostly just delegates onward. → cut it, call the real target direct.
- **Refused Bequest** — a subclass or implementer that ignores or overrides most of what it inherits. → drop the inheritance, use composition.

### 3b. Decide whether the Security axis runs

Run it when the diff touches **untrusted input, authentication/authorization, secrets, money amounts, or PII** — otherwise skip it and say so. Its brief:

- authorization checked on every new or changed route, not just authentication;
- untrusted input validated before it reaches a query, a shell, a template, or an outbound request;
- secrets and PII kept out of logs, error bodies, and traces;
- responses from an external system validated before use, not trusted by shape;
- new dependencies and version bumps: known advisories.

### 4. Spawn both sub-agents in parallel

Send a single message with two `Agent` tool calls. Use the `general-purpose` subagent for both.

**Standards sub-agent prompt** — include:

- The full diff command and commit list.
- The **contents** of the steering guides selected in step 3, pasted in full — the sub-agent cannot reach `fileMatch` steering on its own.
- The brief: "Report — per file/hunk where relevant — (a) every place the diff violates a documented standard: cite the standard (file + the rule); and (b) any baseline smell you spot: name it and quote the hunk. Distinguish hard violations from judgement calls — documented-standard breaches can be hard, but baseline smells are always judgement calls, and a documented repo standard overrides the baseline. Skip anything tooling enforces. Under 400 words."

**Spec sub-agent prompt** — include:

- The diff command and commit list.
- The path or fetched contents of the spec.
- The brief: "Report: (a) requirements the spec asked for that are missing or partial; (b) behaviour in the diff that wasn't asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 400 words."

**Security sub-agent prompt** (only when step 3b says it runs) — include the diff command, the brief from step 3b, and the api-spec files under `docs/api/` for any endpoint the diff touches. Ask for findings with a `file:line` and the concrete attack or leak each one enables, under 400 words.

If the spec is missing, skip the Spec sub-agent and note this in the final report.

### 5. Aggregate

Present the reports under `## Standards`, `## Spec`, and `## Security` headings, verbatim or lightly cleaned. Do **not** merge or rerank findings — the axes are deliberately separate (see _Why two axes_). State plainly when an axis was skipped and why.

End with a one-line summary: total findings per axis, and the worst issue _within each axis_ (if any). Don't pick a single winner across axes — that's the reranking the separation exists to prevent.

## Why two axes

A change can pass one axis and fail the other:

- Code that follows every standard but implements the wrong thing → **Standards pass, Spec fail.**
- Code that does exactly what the issue asked but breaks the project's conventions → **Spec pass, Standards fail.**

Reporting them separately stops one axis from masking the other.
