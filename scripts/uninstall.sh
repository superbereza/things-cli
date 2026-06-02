#!/usr/bin/env bash
# Remove the standalone things-cli symlinks (CLI + skill) and the venv.
# The cloned repo itself is left untouched.

set -euo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
venv_dir="$repo_dir/.venv"
launcher="$HOME/.local/bin/things"
skill_link="$HOME/.claude/skills/things"

[[ -L "$launcher" || -f "$launcher" ]] && rm -v "$launcher" || true
[[ -L "$skill_link" ]] && rm -v "$skill_link" || true
[[ -d "$venv_dir" ]] && rm -rf "$venv_dir" && echo "removed dir: $venv_dir" || true

echo "Uninstalled."
