#!/usr/bin/env bash
# Compatibility wrapper for the former three-argument batch command.
# Outputs use the run layout documented in README.md.
set -euo pipefail
if [[ $# -ne 3 ]]; then
    echo "Usage: $0 <n_samples> <input_directory> <new_output_directory>" >&2
    exit 2
fi
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
exec python3 "$repo_dir/scripts/run_benchmarks.py" "$2" "$3" \
    --samples "$1" --time-limit 3600 --jobs "${JOBS:-1}"
