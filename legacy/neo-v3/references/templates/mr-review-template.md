# MR Review Comment Template (neo)

Orchestrator composes the MR review comment from this template after **Code Reviewer ∥ Security ∥ QA** return (SKILL.md § MR Workflows), then posts via `Skill(gitlab)` ("Post a Comment"). **Table-first, scannable.** The **AC/TC Compliance** section appears **only in mode 8b** (MR has a JIRA card); omit in 8a.

## Template

```
## MR Review Result

| | |
|---|---|
| **MR** | !<mr_id> — <title> |
| **Branch** | <source> → <target> |
| **Mode** | Has JIRA card: <card IDs> / no card |
| **Verdict** | ✅ Approved / ❌ Changes required before merge |

### Findings

| Severity | Area | File:line | Issue | Suggestion |
|------|------|------------|---------|-----------|
| 🔴 Blocker | Code | path:line | <issue> | <fix> |
| 🟠 Critical | Security | path:line | <issue> | <remediation> |
| 🟡 Warning | Code | path:line | <issue> | <fix> |
| 🔵 Info | Code | path:line | <issue> | <suggestion> |

_(Area = Code / Security / QA. No findings at all → see § No findings)_

### Summary

| Severity | Count |
|------|------|
| 🔴 Must fix before merge (Blocker/Critical · Security Critical/High) | X |
| 🟡 Warning (Warning · Security Medium) | X |
| 🔵 Suggestion (Info · Security Low) | X |

### QA

- **E2E regression:** ✅ pass N/N / ❌ fail X/N (<failing tests>) / ⚠️ couldn't run (<reason>)
- **Regression from this MR:** <list / none>

### AC/TC Compliance — card mode only · JIRA: <card IDs>

| AC | Summary | Code matches? | TC | TC result | If mismatch (detail for the AI to fix) |
|----|------|---------|----|------|------------------------------|
| AC-001 | <ac summary> | ✅ | TC-001, TC-005 | 2/2 | — |
| AC-003 | <ac summary> | ❌ | TC-003 | 0/1 | <specific: expected what, got what, where to look> |
| AC-005 | <ac summary> | ⚠️ | — | — | <e.g. no TC trace / not found in diff — not implemented yet> |

---
*Reviewed by neo · Claude Code*
```

## Severity reconciliation

CR and Security use different scales. Keep each finding's **original label** (+emoji) in `Severity`, show its scale in `Area`, and roll up in **Summary** by merge impact:

| Merge impact | Code Reviewer | Security |
|--------------|---------------|----------|
| 🔴 block merge | Blocker, Critical | Critical, High |
| 🟡 Warning | Warning | Medium |
| 🔵 Suggestion | Info | Low |

**Verdict:** ❌ Changes required before merge if **any** 🔴 row exists (CR = Changes Required, Security = Blocked, QA = Blocked, or any AC ❌ in 8b); else ✅ Approved.

## No findings

If all 3 roles find nothing, drop the Findings table and use one line:

```
### Findings
No issues found in convention, security, or test coverage ✅
```

Mode 8b always shows the AC/TC Compliance table (evidence of whether the MR matches the card).
