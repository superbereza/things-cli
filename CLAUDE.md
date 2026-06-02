# things-cli — Claude Code context

This repo ships a Claude Code **skill** at [`skills/things/SKILL.md`](skills/things/SKILL.md)
that drives the `things` CLI (read/write Things 3 tasks, JSON output).

- When installed (via `./install.sh` or `/plugin install things@...`), Claude
  auto-loads the skill — follow it whenever the user mentions Things, tasks,
  today/inbox/upcoming, deadlines, etc.
- The CLI is `things` (on PATH after `install.sh`). If it isn't on PATH, run it
  from this repo as `./bin/things` (or `${CLAUDE_PLUGIN_ROOT}/bin/things` when
  loaded as a plugin) — it builds its own venv on first run.

The skill file is the single source of truth for usage; this file is just the
project pointer.
