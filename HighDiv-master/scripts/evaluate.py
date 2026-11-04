#!/usr/bin/env python3
"""Evaluate a recorded run with the artifact's original metric implementation."""
import argparse
import csv
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys

from run_benchmarks import ROOT, positive_float, sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    parser.add_argument("--metric", choices=["wire_coverage", "satisfies"], default="wire_coverage")
    parser.add_argument("--timeout", type=positive_float, default=300,
                        help="seconds allowed per metric calculation (default: 300)")
    args = parser.parse_args()
    run = args.run.resolve()
    output = run / (args.metric + ".csv")
    if output.exists():
        parser.error(f"metric output already exists: {output}")
    try:
        manifest = json.loads((run / "manifest.json").read_text())
        source = Path(manifest["input_root"])
        instances = manifest["instances"]
        with (run / "summary.csv").open() as f:
            rows = {r["instance"]: r for r in csv.DictReader(f)}
    except (OSError, ValueError, KeyError) as exc:
        parser.error(f"cannot read run metadata: {exc}")
    try:
        import z3
        z3.get_version_string()
    except (ImportError, AttributeError):
        parser.error("Z3 Python bindings are missing; use venv/bin/python3 after make build")

    failed = 0
    with output.open("x", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["Filename", "Percentage", "Status"])
        writer.writeheader()
        for instance in instances:
            name = instance["path"]
            row = rows.get(name, {"status": "missing"})
            formula = source / name
            value = ""
            status = "ok"
            if row["status"] != "ok":
                status = "sampling_" + row["status"]
            elif not formula.is_file() or sha256(formula) != instance["sha256"]:
                status = "input_changed"
            else:
                command = [sys.executable, str(ROOT / "HighDiv/my_scripts/calc_metric.py"),
                           "-f", str(formula), "-s", str(run / row["sample_file"]),
                           "-m", args.metric]
                # The existing SMT-LIB path redeclares variables already loaded
                # from the formula; the existing C API path avoids that error.
                if args.metric == "satisfies":
                    command.append("--use-c-api")
                log = run / "metric-logs" / args.metric / (name + ".log")
                log.parent.mkdir(parents=True, exist_ok=True)
                try:
                    result = subprocess.run(command, text=True, capture_output=True,
                                            timeout=args.timeout)
                    log.write_text(result.stdout + result.stderr)
                    if result.returncode:
                        status = "metric_error"
                    else:
                        text = result.stdout.strip()
                        percentage = (Fraction(text[:-1]) if args.metric == "wire_coverage"
                                      and text.endswith("%") else Fraction(text) * 100)
                        if not 0 <= percentage <= 100:
                            raise ValueError(f"metric result is out of range: {text}")
                        value = f"{float(percentage):.2f}%"
                        if args.metric == "satisfies" and percentage != 100:
                            status = "invalid_samples"
                except subprocess.TimeoutExpired:
                    status = "metric_timeout"
                    log.write_text(f"Metric timed out after {args.timeout} seconds.\n")
                except (OSError, ValueError, ZeroDivisionError) as exc:
                    status = "metric_error"
                    with log.open("a") as detail:
                        detail.write(f"\nEvaluation error: {exc}\n")
            writer.writerow({"Filename": name, "Percentage": value, "Status": status})
            f.flush()
            failed += status != "ok"
            print(f"{name}: {value or '-'} ({status})", flush=True)
    print(f"Saved {output}; {failed}/{len(instances)} instances need attention.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
