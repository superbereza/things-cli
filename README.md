# things-cli

A small Python CLI for [Things 3](https://culturedcode.com/things/) — read your inbox / today / upcoming / projects / areas / tags, search, add todos and projects, mark complete, update. Outputs JSON, designed for piping into `jq` or for being driven by an AI agent.

Ships with a [Claude Code skill](https://code.claude.com/docs/en/skills) (`SKILL.md`) so an agent can read and update Things tasks automatically. Once installed, Claude will be told to run `things today` proactively at the start of a session and to reach for `things add` / `things complete` when the conversation turns to tasks.

## How it works

- **Reads** go through [`thingsapi/things.py`](https://github.com/thingsapi/things.py), which queries the local Things SQLite database directly (fast, no AppleScript round-trips).
- **Writes** go through the [Things URL scheme](https://culturedcode.com/things/help/url-scheme/) via `osascript` so Things processes them natively.
- **Auth token** for `update` / `complete` is fetched via `things.token()`.

CLI logic is a single Python script (`bin/things`) and runs inside a dedicated `.venv/` created by `install.sh`. Both `uv` and stdlib `venv`+`pip` are supported.

## Install

Requirements:

- Python 3.10+
- macOS (Things 3 is Mac-only)
- Things 3 with URL scheme enabled — open Things → Settings → General → "Enable Things URLs"

```bash
git clone https://github.com/<you>/things-cli ~/dev/things-cli
cd ~/dev/things-cli
./install.sh
```

`install.sh` is idempotent and does three things:

1. Creates `.venv/` inside the repo and installs `things.py` from `requirements.txt`. Uses `uv` if available, falls back to `python3 -m venv` + `pip` otherwise.
2. Writes a one-line launcher at `~/.local/bin/things` that invokes the script through the venv's Python.
3. Symlinks `SKILL.md` into `~/.claude/skills/things/` so new Claude Code sessions pick it up.

`~/.local/bin` must be on your `$PATH`. The installer warns if it isn't.

## Usage

```bash
things today                          # human-readable: things today --pretty
things inbox --pretty
things projects --items
things search "meeting"
things add "Buy milk"
things add "Read article" --notes "https://example.com" --when today --tags "reading"
things add "Task" --list "Work" --tags "urgent,important"
things add-project "Renovate kitchen" --area "Home" \
    --todos "Measure walls" --todos "Pick paint color"
things complete <uuid>
things update <uuid> --when tomorrow
things show today
```

All commands print JSON. Add `--pretty` / `-p` for indented output.

## Subcommands

| Command | Action | Needs `things.py` lib |
|---|---|---|
| `inbox`, `today`, `upcoming`, `anytime`, `someday` | List todos in that smart list | yes |
| `projects [--items]` | List projects, optionally with their tasks | yes |
| `areas [--items]` | List areas, optionally with their projects | yes |
| `tags` | List all tags | yes |
| `search <query>` | Full-text search | yes |
| `add <title> [...]` | Add a todo | no (URL scheme) |
| `add-project <title> [...]` | Add a project | no |
| `update <uuid> [...]` | Update existing todo | yes (auth token) |
| `complete <uuid>` | Mark complete | yes (auth token) |
| `show <id\|inbox\|...>` | Open in Things app | no |

Run `things <command> --help` for per-command flags.

## Claude Code skill

`SKILL.md` lives in the repo root and is symlinked into `~/.claude/skills/things/SKILL.md` by `install.sh`. New Claude Code sessions will pick it up automatically — the current session won't (skills are loaded at session start).

The skill description tells Claude to use `things` whenever the user mentions tasks, today, inbox, etc., and to run `things today` proactively at the start of a session to know what's on the user's plate.

To temporarily disable: `rm ~/.claude/skills/things/SKILL.md` (removes the symlink only).

## Uninstall

```bash
./uninstall.sh
```

Removes:

- `~/.local/bin/things` launcher
- `~/.claude/skills/things/SKILL.md` symlink (and the empty `things/` dir)
- `.venv/` inside the repo

The cloned repo itself stays — `rm -rf ~/dev/things-cli` to remove that too.

## Credits

CLI logic is a port-to-CLI of [hald/things-mcp](https://github.com/hald/things-mcp) (an MCP server for Things 3). Uses [thingsapi/things.py](https://github.com/thingsapi/things.py) for SQLite reads.
