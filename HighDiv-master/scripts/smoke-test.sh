#!/usr/bin/env bash
# Generate a handful of samples and check them against the original formula.
set -euo pipefail
repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repo_dir"
if [[ ! -x HighDiv/highdiv || ! -x venv/bin/python3 ]]; then
    echo "Run make build before make smoke-test." >&2
    exit 1
fi
mkdir -p runs
smoke_dir="$(mktemp -d "$repo_dir/runs/smoke-XXXXXXXX")"
mkdir "$smoke_dir/input"
cp HighDiv/LIA_bench/LIA_convert_query-1164.smt2 "$smoke_dir/input/"
python3 scripts/run_benchmarks.py "$smoke_dir/input" "$smoke_dir/run" \
    --samples 5 --time-limit 10 --timeout 75 --seed 0
venv/bin/python3 scripts/evaluate.py "$smoke_dir/run" --metric satisfies
venv/bin/python3 scripts/evaluate.py "$smoke_dir/run" --metric wire_coverage
echo "Smoke test passed. Outputs: $smoke_dir/run"
