# acli Workflows

Multi-command recipes. Single-issue actions are safe to run directly; **bulk and
destructive steps follow the safety gates in `SKILL.md` — preview, confirm, then mutate.**
Run `acli <path> --help` if any flag is unfamiliar.

## Daily standup — what am I working on?

```bash
acli jira workitem search \
  --jql "assignee = currentUser() AND sprint in openSprints() AND status != Done" \
  --fields "key,summary,status"
```

Read-only — just present the result.

## Start working on an issue

```bash
acli jira workitem transition --key "KEY-123" --status "In Progress" --yes
acli jira workitem assign     --key "KEY-123" --assignee "@me"
acli jira workitem view       --key "KEY-123" --fields "status,assignee" --json   # verify it landed
```

Single, named issue → safe to run. The final `view` confirms the write (verify-after-write).

## Finish an issue / mark done

```bash
acli jira workitem transition --key "KEY-123" --status "Done" --yes
acli jira workitem comment create --key "KEY-123" --body "Completed. PR: #456"
```

## Bulk-close sprint items (destructive — gate it)

Closing many items at once is irreversible-ish (re-opening is manual). **Preview first:**

```bash
# 1. PREVIEW — how many, and exactly which?
acli jira workitem search \
  --jql "sprint in openSprints() AND status = 'In Review' AND assignee = currentUser()" \
  --count
acli jira workitem search \
  --jql "sprint in openSprints() AND status = 'In Review' AND assignee = currentUser()" \
  --fields "key,summary,status"
```

Show the user the count + keys and get explicit confirmation. **Only then** run the
mutation with the *same* JQL:

```bash
# 2. MUTATE (after confirmation)
acli jira workitem transition \
  --jql "sprint in openSprints() AND status = 'In Review' AND assignee = currentUser()" \
  --status "Done" --yes --ignore-errors
```

`--ignore-errors` keeps one bad transition from halting the rest.

## Find unassigned bugs in open sprints

```bash
acli jira workitem search \
  --jql "issuetype = Bug AND sprint in openSprints() AND assignee is EMPTY" \
  --fields "key,summary,priority,status"
```

Read-only. To then claim them, treat the assign as a bulk mutation — preview, confirm,
then `acli jira workitem assign --jql "<same JQL>" --assignee "@me" --yes`.
