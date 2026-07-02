---
name: atlassian
description: >
  Interact with Jira and Confluence from the terminal via the `acli` (Atlassian CLI) —
  view/search/create/edit/transition/assign/comment on Jira work items, manage sprints,
  boards, and projects, and read Confluence pages or manage spaces, all without a browser.
  Also the acli reference the `neo` skill points to: the command map plus the judgment
  `--help` can't give (JQL, workflows, safety); run `acli <path> --help` for exact flags.
  Trigger on a direct, ad-hoc Jira/Confluence CLI action — "ดู issue ของฉัน",
  "view my issues", "transition ไป In Progress", "move ticket to In Progress",
  "สร้าง bug ใน Jira", "create a Jira task", "search ด้วย JQL", "find unassigned bugs",
  "ดู sprint ปัจจุบัน", "assign ให้ฉัน", "ดู Confluence page", "list spaces", or any raw
  acli operation. Route elsewhere: verifying AC/test-cases/design against a JIRA card, or
  any read-only card workflow → the `neo` skill (runs read-only acli inline); publishing
  generated API docs to Confluence → `confluence-api-doc` (acli cannot write pages).
compatibility:
  environment: claude-code
  tools:
    - Bash
    - Read
effort: low
metadata:
  version: "2.0"
---

# Atlassian CLI (acli) Skill

Use the `acli` CLI (installed at `/opt/homebrew/bin/acli`) to drive Jira and Confluence
from the terminal. This skill is the plugin's **acli reference** — the `neo` skill names it
as the source for acli usage.

It is a **thin shell over `acli --help`**: this file gives you the *command map*, the
*JQL / workflow domain knowledge*, and the *safety discipline* — none of which `--help`
provides. It deliberately does **not** re-list every flag, because `acli`'s own help
already documents them better and stays current with the installed binary.

## Self-discovery protocol (read first)

Before composing any `acli` command whose subcommands or flags you are not 100% sure of:

1. **Run `acli <path> --help` first.** Walk the tree top-down:
   `acli jira --help` → `acli jira workitem --help` → `acli jira workitem search --help`.
2. **Treat the installed binary's `--help` as the source of truth** over any example in
   this file. The CLI evolves and may run ahead of this file; the binary is authoritative
   for exact flag names, defaults, and examples.
3. Most commands print runnable **examples** in their `--help` — copy that shape rather
   than guessing.

## Command map (where things live — run `--help` for the flags)

**Jira** — `acli jira <group> <cmd>`:

| Group | Commands |
|-------|----------|
| `auth` | `status`, `login`, `logout`, `switch` |
| `workitem` | `view`, `search`, `create`, `create-bulk`, `edit`, `transition`, `assign`, `comment`, `clone`, `link`, `watcher`, `attachment`, `archive`, `unarchive`, `delete` |
| `sprint` | `view`, `create`, `update`, `delete`, `list-workitems` |
| `board` | `search`, `get`, `create`, `delete`, `list-sprints`, `list-projects` |
| `project` | `list`, `view`, `create` |
| `field` / `filter` / `dashboard` | metadata lookups — run `--help` for subcommands |

**Confluence** — `acli confluence <group> <cmd>`:

| Group | Commands |
|-------|----------|
| `auth` | `status`, `login`, `logout`, `switch` |
| `page` | `view` **only** — acli cannot create/update pages (see *Confluence limits*) |
| `space` | `list`, `view`, `create`, `update`, `archive`, `restore` |
| `blog` | run `--help` for subcommands |

## Auth bootstrap

```bash
acli jira auth status          # or: acli confluence auth status
```

If not authenticated, the fastest path is an API token:

```bash
echo <token> | acli jira auth login --site "yoursite.atlassian.net" --email "you@example.com" --token
# or browser OAuth:
acli jira auth login --web
```

If `acli` is missing entirely: `brew install atlassian/tap/acli`.

## Safety gates (always apply)

`acli` mutations are real and often irreversible. Reads are free; **writes need care.**

- **Default to read-only.** `view` / `search` / `--count` never need confirmation.
- **Preview before any bulk mutation.** For an edit / transition / assign / delete driven
  by `--jql`, first run the *same JQL* through search to see the exact set:
  ```bash
  acli jira workitem search --jql "<the JQL>" --count
  acli jira workitem search --jql "<the JQL>" --fields "key,summary,status"
  ```
  Show the user what will be affected and get explicit confirmation **before** mutating.
  Never fire `--jql ... --yes` on a mutation without previewing first.
- **Destructive ops** (`delete`, `archive`, bulk `transition` to a terminal state) — confirm
  with the user and name the affected keys.
- **Verify after write.** After an `edit` / `transition`, re-read the item to confirm the
  change landed: `acli jira workitem view KEY-123 --json`.
- Use `--yes` only *after* the user has confirmed; add `--ignore-errors` on bulk ops so a
  single failure doesn't halt the rest.

## Reading scope — never expand `tested by` links

When viewing or summarizing a Jira work item, its **`tested by`** links are **off-limits**.
Do not follow them, do not fetch the linked test item, and do not list or even mention
them — treat a `tested by` link as if it were not on the card. The user does not permit
reading test artifacts reached through a `tested by` link.

- **Identify it by link *type*, not by the target.** In `issuelinks` the restricted link
  is the one whose `type.name` is **`Tests`** — it renders as **`tested by`** on the card
  (the linked item is the Test Case / Test Scenario that tests this card). Only this type
  is restricted.
- **Every other link type is read normally** — `Relates` (`relates to`), `Dependency`
  (`dependencies with`), `Blocks`, … — *even when the linked item is itself a Test Case /
  Test Scenario*. The trigger is the link **type**, not the target's issue type. (So a
  Test Scenario reached via `relates to` is still in-bounds.)
- When you pull `issuelinks` (e.g. `--fields "issuelinks"`), **drop every entry whose
  `type.name == "Tests"`** before reading or reporting, and never run a follow-up
  `acli jira workitem view <KEY>` on an item you know only through that link.
- Everything else on the card — description, AC, status, and all non-`tested by` links —
  is read as usual.
- **Only exception:** the user, in a later message, *explicitly* names and asks for the
  `tested by` links. Absent that, never surface them.

## JQL

Search is the workhorse — `acli jira workitem search --jql "<query>"`. For ready-to-use
JQL (my issues, sprint scope, by status / type / priority, functions, operators), read
[`references/jql-patterns.md`](references/jql-patterns.md).

## Common workflows

For multi-command recipes (daily standup, start / finish an issue, bulk-close a sprint,
find unassigned bugs) — each with its safety steps inline — read
[`references/workflows.md`](references/workflows.md).

## Confluence limits

`acli confluence page` can only **view** — it cannot create or update pages. So:

- **Reading a page body:** `page view --id <ID>` alone prints only the metadata table —
  *not* the content. To get the body, request it explicitly and feed the **raw XHTML to
  the model** (don't strip the tags — you lose table / heading / code structure):
  ```bash
  acli confluence page view --id <ID> --body-format storage --json | jq -r '.body.storage.value'
  ```
  Use `storage` by default (leanest, structure-clean); if the page is macro-heavy and the
  output fills with `<ac:…>` tags, switch to `--body-format view` (fully rendered HTML).
- Creating / updating a Confluence page → use the Confluence REST API directly (curl).
- **Publishing generated API docs to Confluence → use the `confluence-api-doc` skill** (it owns the
  REST publish + round-trip verify). Do not reimplement that here.
- Space lifecycle (`list` / `view` / `create` / `update` / `archive` / `restore`) *is*
  supported via acli.

## Output tips

- `--json` — parse output or chain into another command.
- `--csv` — tabular reports.
- `--paginate` — fetch all results (required for `project list`; overrides `--limit`).
- `--fields "key,summary,status"` — trim columns to only what you need.
