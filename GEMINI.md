# things-cli — Gemini context

A CLI for **Things 3** (macOS task manager). Reads via `things.py` (direct
SQLite), writes via the Things URL scheme. Every command returns JSON on stdout.

Gemini doesn't auto-load `skills/`, so the essentials are inlined here; the full
reference is in [`skills/things/SKILL.md`](skills/things/SKILL.md).

## Invoking

`things` is on PATH after `./install.sh`; otherwise run `./bin/things` from this
repo (it builds its own venv on first run).

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
