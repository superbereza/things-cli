# things-cli — agent guide (cross-agent)

A CLI for **Things 3** (macOS task manager). Reads via the `things.py` library
(direct SQLite), writes via the Things URL scheme. Every command returns JSON.

This repo packages the same capability for several coding agents from one source:

- **Claude Code / Cursor / Codex** — load the skill at `skills/things/SKILL.md`
  (auto-discovered via `.claude-plugin/`, `.cursor-plugin/`, `.codex-plugin/`).
- **Gemini** — see [`GEMINI.md`](GEMINI.md).
- The full, authoritative usage lives in [`skills/things/SKILL.md`](skills/things/SKILL.md).

## Invoking the CLI

`things` is on PATH after `./install.sh`. Otherwise call `./bin/things` from this
repo (or `${CLAUDE_PLUGIN_ROOT}/bin/things` when loaded as a plugin). The launcher
builds its own venv on first run — no setup step.

```bash
things today           # what's on today (JSON)
things inbox
things add "Buy milk" --when today --wait
things complete <uuid>
things doctor          # diagnose Things reachability + auth token
```

Read the skill for the full command set, output contract, and batching.
