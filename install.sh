#!/usr/bin/env bash
# things-cli — put the `things` CLI on your shell PATH (~/.local/bin/things).
# The venv is built lazily by bin/things on first run, so there is nothing else
# to set up. The skill is delivered by the plugin/marketplace (see README), so
# this does NOT symlink it.
# Idempotent.

set -euo pipefail

repo_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
bin_dir="$HOME/.local/bin"

mkdir -p "$bin_dir"
chmod +x "$repo_dir/bin/things"

# CLI launcher (symlink; -f replaces an older launcher file if present)
ln -sfn "$repo_dir/bin/things" "$bin_dir/things"
echo "[things-cli] CLI:   $bin_dir/things -> bin/things"

# PATH check
if ! printf '%s\n' "$PATH" | tr ':' '\n' | grep -qxF "$bin_dir"; then
    echo
    echo "[things-cli] NOTE: $bin_dir is not on \$PATH. Add to ~/.zshrc:"
    echo "    export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo
echo "Done. The first 'things today' will build the venv automatically."
