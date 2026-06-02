#!/usr/bin/env bash
# Remove things-cli launcher, skill symlink and venv.
# The cloned repo itself is left untouched.

set -euo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
venv_dir="$repo_dir/.venv"
launcher="$HOME/.local/bin/things"
skill_dir="$HOME/.claude/skills/things"
skill_link="$skill_dir/SKILL.md"

[[ -f "$launcher" ]] && rm -v "$launcher" || true
[[ -L "$skill_link" ]] && rm -v "$skill_link" || true
[[ -d "$skill_dir" ]] && rmdir -v "$skill_dir" 2>/dev/null || true
[[ -d "$venv_dir" ]] && rm -rf "$venv_dir" && echo "removed dir: $venv_dir" || true

echo "Uninstalled."
