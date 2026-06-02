# things-cli

A small Python CLI for [Things 3](https://culturedcode.com/things/) — read your inbox / today / upcoming / projects / areas / tags, search, add todos and projects, complete, cancel, update, batch-edit. Outputs JSON, designed for piping into `jq` or being driven by an AI agent.

Ships an agent **skill** at [`skills/things/SKILL.md`](skills/things/SKILL.md) so an agent can read and update Things tasks automatically — run `things today` proactively at the start of a session and reach for `things add` / `things complete` when the conversation turns to tasks. The same skill is wired up for **Claude Code, Cursor, Codex and Gemini** from one source (see [Install](#install)).

## How it works

- **Reads** go through [`thingsapi/things.py`](https://github.com/thingsapi/things.py), which queries the local Things SQLite database directly (fast, no AppleScript round-trips).
- **Writes** go through the [Things URL scheme](https://culturedcode.com/things/help/url-scheme/) via `osascript` so Things processes them natively.
- **Auth token** for `update` / `complete` / `cancel` / `tag-*` is fetched via `things.token()`.

CLI logic is a small Python package (`src/things_cli/`, declared in `pyproject.toml` with a `things` entry point). `bin/things` is a thin self-bootstrapping launcher that creates a dedicated `.venv/`, installs the package editable on first run, and execs the `things` entry point (works whether called directly, via symlink, or from a plugin dir). Both `uv` and stdlib `venv` + `pip` are supported.

## Install

Requirements:

- Python 3.10+
- macOS (Things 3 is Mac-only)
- Things 3 with URL scheme enabled — open Things → Settings → General → "Enable Things URLs"

There are three ways to install — pick one. All end with the same `things` CLI and `things` skill; the `.venv/` is built automatically on first run.

### 1. Standalone (clone + symlinks)

```bash
git clone https://github.com/superbereza/things-cli ~/dev/things-cli
cd ~/dev/things-cli
./install.sh
```

`install.sh` is idempotent and just creates two symlinks:

- `~/.local/bin/things` → `bin/things` (CLI on your `$PATH` — the installer warns if `~/.local/bin` isn't on it)
- `~/.claude/skills/things` → `skills/things` (skill for new Claude Code sessions)

### 2. As a Claude Code plugin (this repo is its own marketplace)

```text
/plugin marketplace add superbereza/things-cli
/plugin install things@things-cli
```

No symlinks, no clone — Claude pulls the repo, loads `skills/things/SKILL.md`, and the first `things …` call builds the venv. The skill calls the bundled `${CLAUDE_PLUGIN_ROOT}/bin/things` launcher when `things` isn't on PATH.

### 3. From an aggregate marketplace

If this plugin is listed in a shared marketplace (e.g. `superbereza/superbereza-skills`):

```text
/plugin marketplace add superbereza/superbereza-skills
/plugin install things@superbereza-skills
```

### Other agents

The same `skills/` directory is exposed to **Cursor** (`.cursor-plugin/`), **Codex** (`.codex-plugin/`) and **Gemini** (`gemini-extension.json` → [`AGENTS.md`](AGENTS.md)). One skill, one source of truth — see [`AGENTS.md`](AGENTS.md).

Run `things doctor --pretty` after install to verify everything's wired up:

```
  ✓ things.py library        ok           version 1.0.1
  ✓ Things 3 app             ok           version 3.22.11
  ✓ SQLite read access       ok           reads work — 65 inbox items
  ✓ Auth token               ok           22-char token available

Overall: ALL OK
```

## Usage

### Reads

```bash
things today                          # JSON array
things today --pretty                 # indented
things today --grep "report" --limit 5
things inbox --grep "buy"
things projects --items               # include each project's task titles
things areas --items                  # include each area's projects
things tags
things search "meeting" --limit 10
```

| Flag | On which read | Effect |
|---|---|---|
| `--pretty`, `-p` | all | Indent JSON |
| `--grep PATTERN`, `-g` | all except `search` | Case-insensitive substring filter on title |
| `--limit N` | all | Truncate to N items |
| `--items`, `-i` | `projects`, `areas` | Include children titles |

### Single writes

```bash
things add "Buy milk"
things add "Read article" --notes "https://..." --when today --tags reading
things add "Task" --list "Work" --tags "urgent,important"
things add "Trip prep" \
    --checklist "Pack toothbrush" --checklist "Charge headphones"

# Verify the write actually landed and capture the real UUID:
things add "Buy milk" --when today --tags shopping --wait
# → {"status":"ok","title":"Buy milk","uuid":"3aEmFg6pBm1Vihy5DofYdR"}

# Add a project with initial tasks
things add-project "Renovate kitchen" --area "Home" \
    --todos "Measure walls" --todos "Pick paint color"

# Move / update
things update <uuid> --title "New title"
things update <uuid> --list "Other Project"       # move (name OR UUID)
things update <uuid> --list MDs59magzJkPhhpPSnZSq  # UUID also works
things update <uuid> --when tomorrow --deadline 2026-07-01

# Complete / cancel — both accept multiple UUIDs
things complete <uuid1> <uuid2> <uuid3>
things cancel <uuid>

# Tags — preserve existing
things tag-add <uuid> urgent reviewed
things tag-remove <uuid> draft

# Open something in the Things UI
things show today
things show <uuid>
```

### Batch writes via `--stdin`

`things add --stdin` accepts either a JSON array or NDJSON (one JSON object per line) — saves N round-trips when adding many items:

```bash
echo '[
  {"title": "Email Alice",     "when": "today", "tags": "comms"},
  {"title": "Review PR #1234", "when": "today"},
  {"title": "Pay credit card", "deadline": "2026-06-15", "list": "Personal"}
]' | things add --stdin --wait --pretty
```

Returns an array of `{status, title, uuid}` records (`uuid` populated only with `--wait`).

NDJSON form is also accepted:

```bash
{"title": "T1"}
{"title": "T2", "deadline": "2026-07-01"}
{"title": "T3", "list": "Work"}
```

Per-item fields supported (mirror the single-add flags): `title` (required), `notes`, `when`, `deadline`, `tags` (string, comma-separated), `list` (name OR UUID), `checklist` (list of strings).

### Diagnostics

```bash
things --version
things doctor               # JSON
things doctor --pretty      # human-readable table
```

`doctor` checks: things.py library, Things 3 app reachable, SQLite reads, auth token. Exit code 1 if anything fails.

## Output contract (for agents / scripts)

Reads return a JSON **array** of items; the full schema is documented in [skills/things/SKILL.md](skills/things/SKILL.md#output-contract).

Common todo fields:

```json
{
  "uuid": "3aEmFg6pBm1Vihy5DofYdR",      // 22-char base62, stable
  "title": "Buy milk",
  "type": "to-do",                        // "to-do" | "project"
  "status": "incomplete",                 // "incomplete" | "completed" | "canceled"
  "list": "Inbox",                        // smart-list this todo is parked in
  "notes": "...",                         // optional
  "start_date": "2026-06-02",             // optional
  "deadline": "2026-06-10",               // optional
  "tags": ["urgent", "work"],             // optional
  "project": "Work",                      // optional, resolved name
  "project_uuid": "...",                  // optional, paired
  "area": "Home",                         // optional, resolved name
  "area_uuid": "..."                      // optional, paired
}
```

Writes return a status object:

```json
{ "status": "ok", "title": "Buy milk", "uuid": "..." }
{ "status": "ok", "uuid": "...", "completed": true }
{ "status": "ok", "uuid": "...", "tags": ["urgent", "reviewed"] }
```

Errors are always structured (exit code 1):

```json
{ "status": "error", "code": "INVALID_UUID" | "MISSING_TITLE" | "NOT_FOUND" | ..., "message": "..." }
```

## Subcommand reference

| Command | Action | Needs `things.py` lib |
|---|---|---|
| `inbox`, `today`, `upcoming`, `anytime`, `someday` | List todos in that smart list | yes |
| `projects [--items]` | List projects (and their tasks) | yes |
| `areas [--items]` | List areas (and their projects) | yes |
| `tags` | List all tags | yes |
| `search <query>` | Substring search | yes |
| `add <title> [...]` | Add a todo | no (URL scheme) |
| `add --stdin` | Add many todos (JSON array or NDJSON) | no |
| `add-project <title> [...]` | Add a project | no |
| `update <uuid> [...]` | Update existing todo (incl. move via `--list`) | yes (auth token) |
| `complete <uuid> [<uuid>...]` | Mark complete (✓) | yes (auth token) |
| `cancel <uuid> [<uuid>...]` | Mark canceled (✗, won't do) | yes (auth token) |
| `tag-add <uuid> <tag>...` | Add tags, preserve existing | yes |
| `tag-remove <uuid> <tag>...` | Remove specific tags, keep the rest | yes |
| `show <id\|inbox\|today\|...>` | Open in Things app UI | no |
| `doctor` | Self-check installation | mostly no |

Run `things <command> --help` for per-command flags.

## Caveats

- **Writes are fire-and-forget** unless you pass `--wait`. The CLI returns `{"status":"ok"}` as soon as the URL is dispatched; if Things rejects the URL, the CLI never sees the error. `--wait` polls SQLite for up to ~3 s to confirm.
- **No `trash`** subcommand — Things' URL scheme can't delete. `cancel` marks "won't do" (✗), `complete` marks done (✓). Real deletion is GUI-only.
- **Tag mutations** through Things' URL scheme always replace the full set; `tag-add` / `tag-remove` work around this by reading existing tags first via `things.py` and sending the merged set.
- **UUIDs are 22-char base62.** The validator on `complete` / `cancel` / `update` / `tag-*` rejects anything else with a clear `INVALID_UUID` error — usually the cause is forgetting to leave a shell variable unquoted: use `things complete $uuids`, not `things complete "$uuids"`.
- **`--grep` filters in Python** after fetching everything from SQLite. Fine for the typical Things database (hundreds of items), not a substitute for SQL pushdown on huge collections.

## The skill

The skill lives at `skills/things/SKILL.md` — the single source of truth, shared
across agents:

- **Claude Code** — `install.sh` symlinks `skills/things` into `~/.claude/skills/`,
  or the plugin install exposes it. New sessions pick it up (the current one does
  not — skills load at session start).
- **Cursor / Codex** — `.cursor-plugin/plugin.json` and `.codex-plugin/plugin.json`
  point at the same `./skills/`.
- **Gemini** — reads [`GEMINI.md`](GEMINI.md) (declared in `gemini-extension.json`).

The skill description tells the agent to use `things` whenever the user mentions
tasks/today/inbox/etc., and to run `things today` proactively at the start of a
session.

Disable the Claude symlink temporarily: `rm ~/.claude/skills/things` (leaves the
repo copy).

## Uninstall

```bash
./scripts/uninstall.sh
```

Removes the launcher, the skill symlink, and the `.venv/`. The cloned repo stays.

## Credits

CLI logic ported from [hald/things-mcp](https://github.com/hald/things-mcp) (an MCP server for Things 3). Uses [thingsapi/things.py](https://github.com/thingsapi/things.py) for SQLite reads.

## OpenCode

This skill also supports [OpenCode](https://opencode.ai) — see [`.opencode/INSTALL.md`](.opencode/INSTALL.md).
