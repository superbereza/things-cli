---
name: things
description: Use this skill to read and write tasks in Things 3 (the macOS task manager) via the `things` CLI. Trigger whenever the user mentions Things, asks "what's on today", "what's in my inbox", "what's due", "what do I need to do"; mentions tasks/todos/projects/areas/tags/deadlines; or wants to add, complete, cancel, update, search, or batch-edit tasks. Also use proactively at the start of a session — run `things today` so you know what's on the user's plate. Output is JSON; pass `--pretty` for indented output while debugging, omit it when parsing.
---

# Things 3 CLI (`things`)

Reads from Things via the [`things.py`](https://github.com/thingsapi/things.py) library (direct SQLite), writes via the [Things URL scheme](https://culturedcode.com/things/help/url-scheme/) (`osascript`). Every command returns JSON on stdout.

## Running the CLI

Use `things` if it's on your PATH (it is after `install.sh`). If it isn't — e.g. when this skill was pulled in as a plugin — run the bundled launcher instead: `${CLAUDE_PLUGIN_ROOT}/bin/things` (or `./bin/things` from the repo). It builds its own Python venv on first run, so there's no separate setup step. Everything below works the same either way — substitute the launcher path for `things`.

## Cheat sheet

```bash
# Reads
things today                         # JSON array
things today --pretty                # indented
things today --grep "report" --limit 5
things projects --items              # projects + their task titles (open only by default)
things projects --items --status done   # ...including completed/canceled tasks
things areas --items                 # areas + their projects
things tags
things search "meeting" --limit 10

# General query — filter by project/area/tag/status (this is the one that reads CLOSED tasks)
things tasks --project "Work" --status done       # audit what's done in a project
things tasks --status done --limit 20             # recent logbook (completed + canceled)
things tasks --tag urgent --status incomplete     # open tasks with a tag

# Single write
things add "Buy milk" --when today --tags shopping --wait

# Batch write (JSON array OR NDJSON on stdin)
echo '[
  {"title": "T1", "notes": "n1"},
  {"title": "T2", "deadline": "2026-07-01", "list": "Work"}
]' | things add --stdin --wait

# Update / move / cancel / complete
things update UUID --list "Other Project"       # move
things update UUID --append-checklist "Item"    # add a checklist line (keeps existing + their ✓)
things complete UUID1 UUID2 UUID3               # variadic
things cancel UUID                              # mark ✗ (not done)
things tag-add UUID urgent important            # ADD without replacing
things tag-remove UUID someday                  # remove subset

# Open in app
things show today
things show <uuid>

# Diagnose install
things doctor --pretty
```

## Output contract

### Reads — JSON array of items

Todos (`inbox`/`today`/`upcoming`/`anytime`/`someday`/`search`):

```json
{
  "uuid": "3aEmFg6pBm1Vihy5DofYdR",      // 22-char base62, stable
  "title": "Buy milk",                    // may be empty string
  "type": "to-do",                        // "to-do" | "project"
  "status": "incomplete",                 // "incomplete" | "completed" | "canceled"
  "list": "Inbox",                        // "Inbox" | "Anytime" | "Someday" | ... (optional)
  "notes": "see https://...",             // optional
  "start_date": "2026-06-02",             // optional, ISO date
  "deadline": "2026-06-10",               // optional, ISO date
  "tags": ["urgent", "work"],             // optional, list of strings
  "checklist": [...],                     // optional
  "project": "Work",                      // optional, resolved name
  "project_uuid": "abc...",               // optional, paired with `project`
  "area": "Home",                         // optional, resolved name
  "area_uuid": "def..."                   // optional, paired with `area`
}
```

Projects (`projects`):
```json
{
  "uuid": "...",
  "title": "Renovate kitchen",
  "type": "project",
  "notes": "...",                         // optional
  "area": "Home",                         // optional
  "area_uuid": "...",                     // optional
  "tasks": ["Measure walls", "..."]       // only with --items
}
```

Areas (`areas`):
```json
{
  "uuid": "...",
  "title": "Home",
  "projects": ["Renovate kitchen", "..."] // only with --items
}
```

Tags (`tags`):
```json
{ "uuid": "...", "title": "urgent" }
```

### Writes — single status object (or array for batch)

```json
{ "status": "ok", "title": "Buy milk", "uuid": "..." }   // --wait fills "uuid"
{ "status": "ok", "uuid": "...", "completed": true }
{ "status": "ok", "uuid": "...", "canceled": true }
{ "status": "ok", "uuid": "...", "tags": ["a", "b"] }    // tag-add/remove
```

Errors are always:
```json
{ "status": "error", "code": "MISSING_TITLE" | "INVALID_UUID" | "NOT_FOUND" | ..., "message": "..." }
```

Exit code 1 on error.

## Cross-cutting flags

| Flag | On which | Effect |
|---|---|---|
| `--pretty`, `-p` | all | Indent JSON |
| `--grep PAT`, `-g PAT` | reads (except `search`) | Case-insensitive substring filter on title |
| `--limit N` | reads | Truncate to N items |
| `--wait` | `add` | Poll SQLite after URL fires; return real `uuid` once the todo appears (timeout ~3s) |
| `--stdin` | `add` | Read items from stdin as JSON array or NDJSON |
| `--list`/`--area` | `add`/`add-project`/`update` | Accepts **either** the project/area name OR its 22-char UUID — auto-detected (UUID skips the by-name lookup) |

## Date semantics

`--when`: `today` | `tomorrow` | `evening` | `anytime` | `someday` | `YYYY-MM-DD`
`--deadline`: `YYYY-MM-DD` (or `clear` via URL scheme, not exposed here)

- All dates are interpreted in the **local timezone** by Things.
- `today` means "today's date as Things sees it" — at 23:55 it's still today; at 00:01 it's the next day.
- `YYYY-MM-DD` works for both past and future. Setting a past date doesn't backdate the task; it just lands it where you put it.
- `--when` and `--deadline` are **different**: `when` is "I plan to start on this date" (drives the Today/Upcoming lists), `deadline` is "must be done by" (shows a red flag near the date).

## Reading closed tasks — `tasks` (the general filter)

The list commands (`today`/`inbox`/`upcoming`/…) and `projects --items` show **only
open** todos by default — they're views of "what's actionable". To read **completed
or canceled** tasks (audit "what got done", logbook, etc.), use `tasks`, the general
query that exposes the underlying filter:

```bash
things tasks --project <name|uuid> --status done     # everything closed in a project
things tasks --status completed --limit 50           # the logbook
things tasks --area Home --status all                # any status in an area
```

| Flag | Meaning |
|---|---|
| `--project <name\|uuid>` | scope to a project (name auto-resolved to UUID) |
| `--area <name\|uuid>` | scope to an area |
| `--tag <tag>` | scope to a tag |
| `--status` | `incomplete` (default) · `completed` · `canceled` · `done` (= completed+canceled) · `all` |

Same `--grep` / `--limit` / `--pretty` as the other reads. `projects --items` also
takes `--status` to control which task titles it lists per project.

> Without scope (`--project`/`--area`/`--tag`), `--status completed`/`done`/`all`
> returns your **entire** logbook — pass `--limit`.

## Common workflows

### Capture multiple items quickly

```bash
echo '[
  {"title": "Email Alice",        "when": "today", "tags": "comms"},
  {"title": "Review PR #1234",    "when": "today"},
  {"title": "Pay credit card",    "deadline": "2026-06-15", "list": "Personal"}
]' | things add --stdin --wait --pretty
```

Returns an array of `{status, title, uuid}`. Each item is a separate URL-scheme call; Things may briefly take focus on the first one.

### Complete several at once

```bash
things complete UUID1 UUID2 UUID3
```

If you have them in a variable from a previous query, **don't quote** the expansion:

```bash
uuids=$(things search "milk" | jq -r '.[].uuid')
things complete $uuids           # correct
things complete "$uuids"         # WRONG: argparse sees one space-separated string,
                                 # the validator will reject it with INVALID_UUID
```

### Move a task between projects

```bash
# By name (case-sensitive, must match exactly)
things update <uuid> --list "Other Project"

# By UUID (unambiguous)
things update <uuid> --list MDs59magzJkPhhpPSnZSq
```

If the name matches both a project and an area, projects win.

### Add a tag without losing existing ones

```bash
things tag-add <uuid> urgent reviewed     # adds 'urgent' and 'reviewed'
things tag-remove <uuid> draft            # removes 'draft' only
things update <uuid> --tags "x,y"         # REPLACES all tags (advanced)
```

### `--checklist` for `add`

Repeat the flag for multiple lines:

```bash
things add "Trip prep" \
    --checklist "Pack toothbrush" \
    --checklist "Charge headphones" \
    --checklist "Confirm taxi"
```

The values become bullet items inside the new todo.

### Edit the checklist of an *existing* todo (`update`)

`update` can also touch a todo's checklist. Repeat the flag for multiple items:

```bash
things update <uuid> --append-checklist "New item"     # add to the end, leave existing items + their ✓ untouched
things update <uuid> --prepend-checklist "First item"  # add to the start
things update <uuid> --checklist "Only" --checklist "These"   # REPLACE the whole checklist
```

- **`--append-checklist` / `--prepend-checklist`** are the safe ones: existing items
  and their completion state are preserved — use these to "fill in what's missing".
- **`--checklist`** REPLACES the entire checklist. That **drops the completion state**
  of existing items (the URL scheme can't re-check individual items), so reach for it
  only when you really want a clean slate.

### Verify a write actually landed

Use `--wait`:

```bash
result=$(things add "Buy milk" --wait)
uuid=$(echo "$result" | jq -r .uuid)
[ -n "$uuid" ] && echo "ok: $uuid" || echo "the write didn't show up in SQLite within 3s"
```

If `--wait` times out the response is `{"status":"pending","title":"...","message":"..."}` rather than `ok` — the URL fired but Things didn't materialize the row in time. Usually Things is just slow or paused — **or two Things instances are running** (see the single-instance rule below).

## Tips for the agent

- **Run `things today` once at session start** — it gives you context on what the user is juggling, lets you offer relevant help unprompted, and the UUIDs you see can be reused for `complete`/`update`/`cancel` without re-querying.
- **Use `--wait` for any add the user might immediately want to manipulate** (e.g. they say "add Buy milk and tag it urgent" → `things add ... --wait`, then `things tag-add <returned uuid> urgent`).
- **Batch through `--stdin`** when adding more than 2 items — N URL-scheme calls is N pops of Things' menubar; batching keeps it to one stream.
- **`things doctor`** if anything write-related fails: it checks Things 3 is reachable, the auth token is available (needed for `complete`/`update`/`cancel`/`tag-*`), the SQLite read path works, and that **only one Things instance is running** (a duplicate stalls Things Cloud sync).
- **Don't quote `$uuids`** when forwarding from a query (`things complete $uuids`) — the validator will reject space-joined strings with a clear hint.
- **No `trash` command** — Things' URL scheme can't delete; use `cancel` to mark "won't do" (✗) or `complete` to mark done (✓). Real deletion is GUI-only.

## Only one Things instance

**Never run two copies of the Things app at once.** Only one instance owns the
Things Cloud sync connection; a second instance can grab that connection and then go
stale, so the app looks open and writable but **silently stops syncing to Things
Cloud** (other devices never receive the changes, and changes from them never arrive).
Local writes still land in the SQLite DB, which masks the problem.

- Symptom: writes succeed / `--wait` returns `ok`, the task is in the local DB and in
  the app, but it **never reaches the phone/other devices** (and vice-versa).
- Check: `pgrep -x Things3` — if it returns **more than one PID**, that's the bug.
- Fix: quit the duplicate (keep one), or quit Things entirely and reopen a single
  instance, then it resyncs. This is a *sync* problem, not a CLI problem — the CLI
  read/write path keeps working either way.

## Limitations

- Writes are fire-and-forget through the URL scheme — without `--wait` you can't tell if Things accepted them.
- Tag mutations via the URL scheme always pass a full list; `tag-add` and `tag-remove` read the current tags via `things.py` first, then send the new full set.
- `--grep` filters in Python after fetching everything — no SQL-side pushdown. Fine for typical Things-sized lists (hundreds of items), not for huge personal databases.
- `search` accepts only one query string; for compound queries pipe to `jq`.
