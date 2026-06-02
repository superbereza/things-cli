#!/usr/bin/env bash
# bump.sh <new-version> — set the version everywhere it lives, so they never drift.
# Run from the repo root: ./scripts/bump.sh 1.1.0
set -euo pipefail
[ $# -eq 1 ] || { echo "usage: scripts/bump.sh <new-version>" >&2; exit 2; }
new="$1"
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$root"

perl -0pi -e 's/^(version\s*=\s*")[^"]+(")/${1}'"$new"'${2}/m' pyproject.toml
perl -0pi -e 's/(__version__\s*=\s*")[^"]+(")/${1}'"$new"'${2}/' src/things_cli/cli.py
for f in .claude-plugin/plugin.json .claude-plugin/marketplace.json \
         .cursor-plugin/plugin.json .codex-plugin/plugin.json gemini-extension.json; do
  perl -0pi -e 's/("version"\s*:\s*")[^"]+(")/${1}'"$new"'${2}/g' "$f"
done
echo "bumped to $new. Next: uv lock && git commit && git tag v$new"
