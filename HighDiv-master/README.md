# HighDiv: SMT(LIA) Sampling with High Diversity

HighDiv combines CDCL(T) and local search to generate diverse satisfying
assignments for SMT formulas over linear integer arithmetic. Its local search
component, Context-Constrained Stochastic Search (CCSS), is implemented inside
the bundled, modified Z3.

This repository accompanies **SMT(LIA) Sampling with High Diversity**, by
Yong Lai, Junjie Li, and Chuan Luo, **TACAS 2026**, pp. 192–212.
[Paper / DOI](https://doi.org/10.1007/978-3-032-22752-2_10) ·
[Installation](#installation) · [Usage](#run-one-instance) ·
[Citation](CITATION.cff)

## Quick start

Use a 64-bit GNU/Linux system with GNU Make, a C++20 compiler, and Python 3
with `venv` support. Run these commands from the repository root:

```bash
make build JOBS=4
make smoke-test
```

The build installs the **bundled Z3 4.14.2** and its Python bindings into
`venv/`, then creates `HighDiv/highdiv`. The smoke test generates a small set
of samples, checks that they satisfy the input formula, and computes coverage.
Its outputs are retained in a fresh `runs/smoke-*/run/` directory.

## Installation

Requirements: 64-bit GNU/Linux, GNU Make, a C++20 compiler, and Python 3.10 or
newer with `venv` support. On Ubuntu or Debian:

```bash
sudo apt-get update
sudo apt-get install build-essential python3 python3-venv
make build JOBS=4
```

Use the modified Z3 included here: an upstream/system Z3 package does not
contain HighDiv's sampling extensions. The build creates `venv/`, compiles Z3
in `z3/build/`, installs it locally, and links `HighDiv/highdiv` to that library.
No environment activation or system-wide Z3 installation is required.
The first build compiles all of Z3; reduce `JOBS` on machines with limited memory.
Keep the checkout path free of spaces for Z3's build system.

The equivalent build command is `bash scripts/build.sh --jobs 4`.
`HighDiv/make-z3.sh` is a compatibility wrapper for the same build.
HighDiv uses `-g -O0 -Wall -std=c++20`; Z3 uses its release build settings.

## Run one instance

```bash
mkdir -p runs/example
./HighDiv/highdiv \
  -i HighDiv/LIA_bench/LIA_convert_query-1164.smt2 \
  -o runs/example -n 1000 -t 3600 -s 0
```

The output is `runs/example/LIA_convert_query-1164.smt2.samples`.
Create the output directory before calling the executable directly.

| Option | Meaning | Executable default |
| --- | --- | --- |
| `-i FILE` | Input SMT-LIB 2 formula; required | — |
| `-o DIR` | Existing directory for sample output | Current working directory |
| `-n N` | Target number of unique samples | `1000` |
| `-t SECONDS` | Sampling time budget, checked before solver calls | `3600` |
| `-s SEED` | Random seed | `0` |
| `-h` | Print help | — |

The executable's `-h` option exits with status 1 after printing help.

Sampling stops when the target count or time budget is reached. A run may
produce fewer than `-n` samples. Internal time checks are periodic, so `-t`
is not a strict wall-clock limit.

Each output line contains a sample index followed by variable assignments:

```text
0: x:3;y:-2;
1: x:5;y:0;
```

## Run and evaluate a batch

```bash
python3 scripts/run_benchmarks.py HighDiv/LIA_bench runs/demo \
  --samples 10 --time-limit 10 --seed 0 --jobs 2
venv/bin/python3 scripts/evaluate.py runs/demo --metric satisfies
venv/bin/python3 scripts/evaluate.py runs/demo --metric wire_coverage
```

The runner recursively finds `.smt2` files. Replace `HighDiv/LIA_bench` with
your input directory or `benchmarks/QF_LIA` to use the bundled benchmark suite.
Each run needs a **new output directory**.

| Option | Meaning | Default |
| --- | --- | --- |
| `--samples N` | Target number of unique samples per input | `1000` |
| `--time-limit SECONDS` | Sampling budget per input | `900` |
| `--seed N` | Random seed | `0` |
| `--jobs N` | Number of concurrent sampler processes | `1` |
| `--timeout SECONDS` | Hard process timeout per input | Time limit plus 65 seconds |
| `--dry-run` | Print commands without running them | Off |

The output directory contains:

```text
runs/demo/
  manifest.json       # Inputs, commands, hashes, and settings
  summary.csv         # Run status, elapsed time, and sample count per input
  samples/            # Sample files, preserving relative input paths
  logs/               # Sampler logs
  satisfies.csv       # Created by satisfaction evaluation
  wire_coverage.csv   # Created by coverage evaluation
  metric-logs/        # Evaluation logs
```

Check the status and sample count in `summary.csv`. A status of `ok` means
the sampler exited normally with nonempty output; it does not mean the target
count was reached. Other statuses include `empty`, `error`, `timeout`, and
`cancelled`. Ctrl-C stops active sampler processes.

Run evaluation with `venv/bin/python3`. A satisfaction result of
`100.00% (ok)` means every checked sample satisfies its input formula.
Failed or empty runs retain their status in the metric CSVs. Evaluation does
not overwrite an existing metric CSV. Use `--timeout SECONDS` to adjust the
per-input evaluation timeout (default: 300 seconds).

For command-line help:

```bash
python3 scripts/run_benchmarks.py --help
venv/bin/python3 scripts/evaluate.py --help
```

The original three-argument batch command is also supported:

```bash
bash HighDiv/my_scripts/run_benchmarks.sh 10 HighDiv/LIA_bench runs/legacy-command
```

This wrapper uses a 3600-second sampling budget and `JOBS` concurrent processes
(default: 1). It creates the same output layout as the Python runner.

To evaluate a single sample file directly:

```bash
venv/bin/python3 HighDiv/my_scripts/calc_metric.py \
  -f HighDiv/LIA_bench/LIA_convert_query-1164.smt2 \
  -s runs/example/LIA_convert_query-1164.smt2.samples \
  -m satisfies --use-c-api
```

This command prints a fraction (`1` means all samples satisfy the formula).

## Repository layout

| Path | Contents |
| --- | --- |
| `HighDiv/src/main/` | Command-line entry point |
| `HighDiv/src/sampler/` | HighDiv sampling framework and model output |
| `z3/` | Bundled modified Z3 4.14.2 source |
| `z3/src/sampler/` | CCSS implementation |
| `HighDiv/LIA_bench/` | Seven small-run test instances |
| `benchmarks/QF_LIA/` | 345 evaluation instances |
| `benchmarks/manifest.csv` | Instance hashes and mapping to archived result IDs |
| `results/` | 8 archived comparison CSVs; 345 rows each |
| `scripts/` | Supported build, sampling, evaluation, and smoke-test entry points |
| `tests/` | Initialization, movement, sampler runtime, runner, and metric checks |
| `HighDiv/my_scripts/` | Metric implementation and batch-command compatibility wrapper |
| `runs/` | Generated local runs, ignored by Git |

The repository provides the complete sampler, its benchmarks, and archived
comparison data.
Generated binaries, Python environments, editor caches, and new runs are
excluded from version control.

`benchmarks/manifest.csv` lists input paths relative to `benchmarks/QF_LIA/`,
their SHA-256 hashes, and the `ResultID` matching archived CSV `Filename` values.
The eight CSVs in `results/comparative_experiment/` contain archived measurements
in `Filename,Percentage` format. New evaluator output uses full relative paths
and adds a `Status` column; use the manifest when matching identifiers.

## Checks

```bash
make test
make smoke-test
```

Runner tests use the Python standard library; initialization tests compile the
actual C++ implementation. Metric integration tests use the
locally built Z3 and are skipped until `make build` has been run. The smoke test
requires the complete build.

## Troubleshooting

- **HighDiv sources changed:** run `make -C HighDiv`.
- **Z3 changed or the checkout moved:** run `make build JOBS=4` to reinstall
  and relink the local library.
- **Compiler flags changed:** remove the generated build directories before
  rebuilding; Make does not detect flag changes.
- **Missing `venv` or `ensurepip`:** install `python3-venv` and rebuild.
- **Unknown Z3 sampling parameters:** use `ldd HighDiv/highdiv` to check that
  it loads `venv/lib/libz3.so`. Check for a conflicting `LD_LIBRARY_PATH`.
- **Python cannot import Z3:** run the evaluator with `venv/bin/python3`.
- **Sample output cannot be opened:** create the output directory before
  calling the executable, or use the batch runner.

## Citation

```bibtex
@inproceedings{lai2026highdiv,
  author    = {Yong Lai and Junjie Li and Chuan Luo},
  title     = {{SMT(LIA)} Sampling with High Diversity},
  booktitle = {Tools and Algorithms for the Construction and Analysis of Systems},
  series    = {Lecture Notes in Computer Science},
  volume    = {16505},
  pages     = {192--212},
  publisher = {Springer},
  year      = {2026},
  doi       = {10.1007/978-3-032-22752-2_10}
}
```

Machine-readable citation metadata is provided in [CITATION.cff](CITATION.cff).

## Licensing

The bundled Z3 license is in [z3/LICENSE.txt](z3/LICENSE.txt). This checkout does
not yet specify a separate license for the HighDiv-specific code.
