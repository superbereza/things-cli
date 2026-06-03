# things-cli — agent guide

A CLI for **Things 3** (macOS task manager). Reads via the `things.py` library
(direct SQLite), writes via the Things URL scheme. Every command returns JSON.

The same skill is wired up for several coding agents from one source:

- **Claude Code / Cursor / Codex** — load the skill at [`skills/things/SKILL.md`](skills/things/SKILL.md)
  (auto-discovered via `.claude-plugin/`, `.cursor-plugin/`, `.codex-plugin/`).
- **Gemini** — reads this file (`gemini-extension.json` → `contextFileName: AGENTS.md`).
- Full, authoritative usage: [`skills/things/SKILL.md`](skills/things/SKILL.md).

## Invoking the CLI

`things` is on PATH after `./install.sh`. Otherwise call `./bin/things` from this
repo (or `${CLAUDE_PLUGIN_ROOT}/bin/things` when loaded as a plugin). The launcher
builds its own venv on first run — no setup step.

## Cheat sheet

```bash
# Reads (JSON array)
things today
things today --grep "report" --limit 5
things inbox | upcoming | anytime | someday
things projects --items          # projects + their task titles
things areas --items
things tags
things search "meeting" --limit 10

# Writes
things add "Buy milk" --when today --tags shopping --wait
echo '[{"title":"T1"},{"title":"T2","deadline":"2026-07-01","list":"Work"}]' \
  | things add --stdin --wait
things update <uuid> --list "Other Project"     # move
things complete <uuid1> <uuid2>                 # variadic
things cancel <uuid>
things tag-add <uuid> urgent                    # add without replacing
things doctor                                   # diagnose
```

Notes: `--wait` returns the real `uuid` after an add; don't quote `$uuids` when
forwarding from a query (`things complete $uuids`); `--when` = start date,
`--deadline` = due date. Full output contract and edge cases: see the skill file.
## Maintainer note

Changing a skill or its payload? It reaches installed plugins **only after a release** —
`scripts/bump.sh <v>` → commit → tag `vX.Y.Z` → GitHub release → `/plugin update`. A commit on
`main` alone propagates nothing (Claude/Codex cache plugins by version string). Full rule and the
MAJOR/MINOR/PATCH guidance: the `skill-builder` skill, §7.
