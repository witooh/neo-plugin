# JQL Patterns for Developers

## My Issues

```jql
# All my open issues
assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC

# My issues in active sprint
assignee = currentUser() AND sprint in openSprints() AND statusCategory != Done

# My issues updated today
assignee = currentUser() AND updated >= startOfDay()

# My issues due this week
assignee = currentUser() AND due >= startOfWeek() AND due <= endOfWeek()
```

## Sprint & Board

```jql
# All issues in active sprints
sprint in openSprints()

# Completed sprint issues
sprint in closedSprints() AND sprint = "Sprint 9"

# Unfinished work from last sprint
sprint in closedSprints() AND statusCategory != Done ORDER BY updated DESC

# Issues added to sprint after start (scope creep)
sprint in openSprints() AND sprint was EMPTY before startOfWeek()
```

## By Status

```jql
# In progress items (team-wide)
status = "In Progress" AND sprint in openSprints()

# Ready for review
status = "In Review" ORDER BY updated ASC

# Blocked issues
status = "Blocked" ORDER BY priority DESC

# All open issues (not done)
statusCategory != Done AND sprint in openSprints()
```

## By Type

```jql
# Open bugs in sprint
issuetype = Bug AND sprint in openSprints() AND statusCategory != Done

# High/critical bugs unassigned
issuetype = Bug AND priority in (High, Critical) AND assignee is EMPTY

# Epics in project
issuetype = Epic AND project = PROJ AND statusCategory != Done

# Sub-tasks assigned to me
issuetype = Sub-task AND assignee = currentUser()
```

## By Priority

```jql
# Urgent issues
priority = Critical AND statusCategory != Done ORDER BY created ASC

# High priority unassigned
priority in (High, Critical) AND assignee is EMPTY AND sprint in openSprints()
```

## Search & Filter

```jql
# Text search
text ~ "payment gateway" AND sprint in openSprints()

# By label
labels = "backend" AND sprint in openSprints()

# Recently created (last 7 days)
created >= -7d ORDER BY created DESC

# Recently updated
updated >= -1d ORDER BY updated DESC

# By reporter (issues I created)
reporter = currentUser() AND statusCategory != Done
```

## Useful JQL Functions

| Function | Description |
|----------|-------------|
| `currentUser()` | Logged-in user |
| `openSprints()` | All active sprints |
| `closedSprints()` | All completed sprints |
| `startOfDay()` | Today 00:00 |
| `endOfDay()` | Today 23:59 |
| `startOfWeek()` | Monday 00:00 |
| `endOfWeek()` | Sunday 23:59 |
| `startOfMonth()` | First day of month |
| `-7d` / `-1w` | Relative date: 7 days ago / 1 week ago |

## Operators

| Operator | Example |
|----------|---------|
| `=` / `!=` | `status = "Done"` |
| `in` / `not in` | `status in ("To Do", "In Progress")` |
| `is EMPTY` / `is not EMPTY` | `assignee is EMPTY` |
| `~` (contains) | `summary ~ "login"` |
| `>=` / `<=` | `created >= -7d` |
| `was` | `status was "In Progress"` |
| `AND` / `OR` / `NOT` | combine conditions |

## ORDER BY

```jql
ORDER BY created DESC       -- newest first
ORDER BY updated DESC       -- recently updated first
ORDER BY priority DESC      -- highest priority first
ORDER BY due ASC            -- earliest due date first
```
