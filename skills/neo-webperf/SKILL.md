---
name: neo-webperf
description: >
  Entry point for a web performance audit in the neo workflow — targets web apps
  only, not libraries or CLIs. Detects Deep mode (a Lighthouse/PSI/CrUX JSON, a
  DevTools trace, or a live URL with the chrome-devtools MCP) vs Quick mode
  (source-only; findings tagged potential impact). On Claude Code it spawns the
  `web-performance-auditor` subagent; on tools without an Agent tool it runs that
  same audit inline using references/performance-checklist.md, and hands
  remediation to `performance-optimization`. Use when auditing a web app for Core
  Web Vitals, loading, rendering, or network issues, or when you invoke
  /neo-webperf. Deeper remediation is `performance-optimization`.
---

# Neo Webperf — web performance audit entry point

## Overview

This is the neo entry point for a web performance audit. It targets web
applications only and wraps the `web-performance-auditor` specialist — spawning it
as a subagent where an Agent tool exists, and running the same audit inline where
one doesn't (so the audit travels to every tool). Remediation of confirmed issues
is handed to `performance-optimization`. It does **not** reimplement the
optimization method.

## When to Use

- When auditing a web app for Core Web Vitals, loading, rendering, or network
  issues.
- When you invoke `/neo-webperf`.
- Route elsewhere: for utility libraries, CLIs, or server-only code with no
  browser output → not applicable; to *fix* a confirmed bottleneck →
  `performance-optimization`.

## The Workflow

1. **Scope check.** Web apps only. Do not use for utility libraries, CLIs, or
   server-only code with no browser-facing output.
2. **Determine the mode.**
   - **Deep mode** — a Lighthouse JSON, a PageSpeed Insights JSON, a CrUX API
     response, a DevTools performance trace, or a live URL plus the
     `chrome-devtools` MCP configured (capture metrics directly).
   - **Quick mode** (default when none of the above) — scan source for structural
     anti-patterns; label every finding `potential impact`.
3. **Run the audit — branch on capability.**
   - **Agent tool available (e.g. Claude Code):** spawn the
     `web-performance-auditor` subagent, passing the files/diff under review, any
     artifact paths (Lighthouse/PSI/CrUX/trace) or pasted JSON, the target URL,
     and the expected mode.
   - **No Agent tool (e.g. pi, cursor, opencode):** run the same audit inline
     using `references/performance-checklist.md` as the baseline — same Deep/Quick
     modes, same metric-honesty rule (only report sourced values), same scorecard
     and ranked-findings shape.
4. **Return the report** — a scorecard (only populated with sourced values), a
   ranked list of findings, positive observations, and proactive recommendations.
   Hand remediation of confirmed issues to `performance-optimization`.

## Common Rationalizations

| Excuse | Reality |
|---|---|
| "I'll audit this CLI/library for perf too." | This entry is web-app-only; there are no Core Web Vitals to measure off a browser. |
| "No Lighthouse data, but I'll report scores anyway." | Metric honesty: in Quick mode label findings `potential impact` and only report values you actually sourced. |
| "No Agent tool here, so I can't audit." | The audit runs inline via `references/performance-checklist.md` — capability is a branch, not a blocker. |

## Red Flags

- Running against a non-web target (library / CLI / server-only).
- A scorecard populated with unsourced or invented metric values.
- Skipping the audit entirely on tools without an Agent tool.
- Reporting bottlenecks with no remediation hand-off to `performance-optimization`.

## Verification

- The target is a web app; the mode (Deep/Quick) matches the available inputs.
- The scorecard contains only sourced values; Quick-mode findings are labeled
  `potential impact`.
- A ranked findings list is returned, with remediation routed to
  `performance-optimization`.
