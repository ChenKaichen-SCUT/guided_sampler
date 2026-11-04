#!/usr/bin/env bash
# Build and install the bundled Z3 inside this checkout, then build HighDiv.
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
jobs="${JOBS:-4}"

usage() {
    echo "Usage: bash scripts/build.sh [--jobs N]"
    echo "Build the bundled Z3 and HighDiv locally (default: JOBS=4)."
}

while (($#)); do
    case "$1" in
        --jobs|-j)
            if (($# < 2)); then usage >&2; exit 2; fi
            jobs="$2"
            shift 2
            ;;
        --help|-h) usage; exit 0 ;;
        *) usage >&2; exit 2 ;;
    esac
done
if [[ ! "$jobs" =~ ^[1-9][0-9]*$ ]]; then
    echo "The job count must be a positive integer." >&2
    exit 2
fi

cd "$repo_dir"
if [[ ! -x venv/bin/python3 ]]; then
    python3 -m venv venv
fi
python_bin="$repo_dir/venv/bin/python3"

(
    cd z3
    "$python_bin" scripts/mk_make.py --python --prefix="$repo_dir/venv"
)
make -C z3/build -j "$jobs"
make -C z3/build install
make -C HighDiv -j "$jobs" Z3_PREFIX="$repo_dir/venv"
echo "Built $repo_dir/HighDiv/highdiv"
