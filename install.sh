#!/usr/bin/env bash
# things-cli — standalone installer. Just two symlinks; the venv is built
# lazily by bin/things on first run, so there is nothing else to set up.
#
#   1. bin/things    -> ~/.local/bin/things       (CLI on your PATH)
#   2. skills/things -> ~/.claude/skills/things    (skill for Claude Code)
#
# Idempotent. (To use via the plugin marketplace instead of symlinks, see README.)

set -euo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
bin_dir="$HOME/.local/bin"
skills_dir="$HOME/.claude/skills"

mkdir -p "$bin_dir" "$skills_dir"
chmod +x "$repo_dir/bin/things"

# 1. CLI launcher (symlink; -f replaces an older launcher file if present)
ln -sfn "$repo_dir/bin/things" "$bin_dir/things"
echo "[things-cli] CLI:   $bin_dir/things -> bin/things"

# 2. Skill (symlink the whole skill dir; replace whatever is there)
rm -rf "$skills_dir/things"
ln -s "$repo_dir/skills/things" "$skills_dir/things"
echo "[things-cli] skill: $skills_dir/things -> skills/things"

# PATH check
if ! printf '%s\n' "$PATH" | tr ':' '\n' | grep -qxF "$bin_dir"; then
    echo
    echo "[things-cli] NOTE: $bin_dir is not on \$PATH. Add to ~/.zshrc:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo
echo "Done. The first 'things today' will build the venv automatically."
