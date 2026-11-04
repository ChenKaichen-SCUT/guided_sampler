#!/usr/bin/env bash
# Compatibility entry point; the project build no longer uninstalls Z3 first.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
exec bash "$repo_dir/scripts/build.sh" "$@"
