#!/usr/bin/env bash
set -euo pipefail

# Sync the GitHub Pages publish folder (`docs/`) from the canonical static frontend (`frontend/`).
# This repo deploys GitHub Pages from the `docs/` folder on main.
#
# Usage:
#   ./scripts/sync_docs.sh
#
# Then commit + push.

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [[ ! -d "frontend" ]]; then
  echo "Error: frontend/ not found in $ROOT_DIR" >&2
  exit 1
fi

mkdir -p docs

copy_file() {
  local src="$1"
  local dst="$2"
  if [[ ! -f "$src" ]]; then
    echo "Error: missing source file: $src" >&2
    exit 1
  fi
  mkdir -p "$(dirname "$dst")"
  cp -f "$src" "$dst"
}

copy_dir() {
  local src="$1"
  local dst="$2"
  if [[ ! -d "$src" ]]; then
    echo "Error: missing source dir: $src" >&2
    exit 1
  fi
  rm -rf "$dst"
  mkdir -p "$(dirname "$dst")"
  cp -R "$src" "$dst"
}

echo "Syncing docs/ from frontend/..."

copy_file "frontend/index.html" "docs/index.html"
copy_file "frontend/main.js" "docs/main.js"
copy_file "frontend/utils.js" "docs/utils.js"
copy_file "frontend/config.js" "docs/config.js"
copy_file "frontend/favicon.ico" "docs/favicon.ico"
copy_dir "frontend/css" "docs/css"
copy_dir "frontend/vendor" "docs/vendor"

echo "Done."
echo
echo "Next:"
echo "  - run tests: pytest -q"
echo "  - commit:    git add docs && git commit -m \"docs: sync publish bundle\""
