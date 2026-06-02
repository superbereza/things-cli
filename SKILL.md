---
name: things
description: Use this skill to read and write tasks in Things 3 (the macOS task manager) via the `things` CLI. Trigger whenever the user mentions Things, asks "what's on today", "what's in my inbox", "what's due", "what do I need to do"; mentions tasks/todos/projects/areas/tags/deadlines; or wants to add, complete, update, or search for a task. Also use proactively at the start of a session — run `things today` to know what's on the user's plate so you can offer relevant help unprompted.
---

# Things 3 CLI

The `things` command reads and writes data in the [Things 3](https://culturedcode.com/things/) macOS task manager.

- **Reads** go through the [`things.py`](https://github.com/thingsapi/things.py) library, which queries the local Things SQLite database directly.
- **Writes** go through the [Things URL scheme](https://culturedcode.com/things/help/url-scheme/) via `osascript` so Things processes them natively.

All commands return JSON on stdout — pipe to `jq` for filtering or parse it directly.

## Subcommands

### Reading

| Command | Returns |
|---------|---------|
| `things inbox` | Todos in Inbox |
| `things today` | Todos due/started today |
| `things upcoming` | Scheduled todos |
| `things anytime` | "Anytime" list |
| `things someday` | "Someday" list |
| `things projects [--items]` | All projects, optionally with their todo titles |
| `things areas [--items]` | All areas, optionally with their projects |
| `things tags` | All tags |
| `things search <query>` | Full-text search across todos |

### Writing

| Command | Effect |
|---------|--------|
| `things add <title> [--notes --when --deadline --tags --list --checklist]` | Add a todo. `--when`: `today \| tomorrow \| evening \| anytime \| someday \| YYYY-MM-DD`. `--list` is project or area name. `--checklist` can repeat. |
| `things add-project <title> [--notes --when --deadline --tags --area --todos]` | Add a project. `--todos` can repeat — initial tasks under the project. |
| `things update <uuid> [--title --notes --when --deadline --tags]` | Update an existing todo by UUID. |
| `things complete <uuid>` | Mark a todo complete. |
| `things show <id\|inbox\|today\|...>` | Open something in the Things app UI (useful when the user asked to "open" or "show" something). |

### Output flag

| Flag | Effect |
|------|--------|
| `--pretty`, `-p` | Indent JSON output (humans). Without it: single-line JSON. |

## Examples

```bash
# What's on today
things today --pretty

# Add a quick capture to Inbox
things add "Buy milk"

# Add to a specific project with tags and a deadline
things add "Draft Q3 report" --list "Work" --tags "urgent,reports" --deadline 2026-07-15

# Add a project with initial tasks
things add-project "Renovate kitchen" \
    --area "Home" \
    --todos "Measure walls" \
    --todos "Pick paint color" \
    --todos "Order tiles"

# Search and complete
uuid=$(things search "milk" | jq -r '.[0].uuid')
things complete "$uuid"

# Open Today in the Things UI
things show today
```

## How to parse output

Reads return a JSON **array** of objects:

```json
[
  {
    "uuid": "ABCD-1234-...",
    "title": "Buy milk",
    "type": "to-do",
    "status": "incomplete",
    "list": "inbox"
  }
]
```

Common fields you'll see: `uuid`, `title`, `type`, `status`, `notes`, `list`, `start_date`, `deadline`, `tags`, `checklist`, `project`, `area`.

Writes return a single status object:

```json
{ "status": "ok", "title": "Buy milk" }
```

## Notes for the agent

- **Start-of-session check**: when a session opens, run `things today` once and skim the titles. This gives context — if the user asks about something on that list, you already have the UUID.
- **UUIDs are stable** — once you've fetched one in a session, you can reuse it for `complete` / `update`.
- **Date format**: prefer `YYYY-MM-DD` for `--when` and `--deadline` over natural-language strings.
- **Don't spam Things app**: each write triggers a URL handler; batch via `add-project --todos` when adding several tasks under one parent.
- **No write confirmations**: `add` / `complete` are fire-and-forget — Things processes them async. The CLI returns immediately with `{"status": "ok"}`. If the write fails inside Things, the CLI won't know.
- **Auth token for update/complete** is fetched automatically via `things.token()` from the library. If those commands return an "auth token not available" error, the user needs to enable Things URL scheme in app preferences (Settings → General → "Enable Things URLs").
