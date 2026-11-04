#!/usr/bin/env python3
"""Run HighDiv on an SMT-LIB directory and retain an auditable run record."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import shlex
import signal
import subprocess
import tempfile
import threading
import time


ROOT = Path(__file__).resolve().parents[1]


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def positive_float(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("must be a finite positive number")
    return number


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_output(*args):
    try:
        return subprocess.check_output(
            ["git", "-C", str(ROOT), *args], stderr=subprocess.DEVNULL, text=True,
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="directory searched recursively for *.smt2")
    parser.add_argument("output", type=Path, help="new run directory (must not exist)")
    parser.add_argument("--binary", type=Path, default=ROOT / "HighDiv/highdiv")
    parser.add_argument("--samples", type=positive_int, default=1000)
    parser.add_argument("--time-limit", type=positive_float, default=900)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--jobs", type=positive_int, default=1)
    parser.add_argument("--timeout", type=positive_float,
                        help="wall-clock timeout per process (default: time-limit + 65 seconds)")
    parser.add_argument("--dry-run", action="store_true", help="print commands without writing or running")
    args = parser.parse_args()
    if args.samples > 4294967295:
        parser.error("--samples must fit HighDiv's unsigned 32-bit sample counter")
    if not 0 <= args.seed <= 2147483647:
        parser.error("--seed must be between 0 and 2147483647")

    source = args.input.resolve()
    output = args.output.resolve()
    binary = args.binary.resolve()
    if not source.is_dir():
        parser.error(f"input directory does not exist: {source}")
    instances = sorted(source.rglob("*.smt2"))
    instances = [p for p in instances if p.is_file()]
    if not instances:
        parser.error(f"no .smt2 files found in {source}")
    timeout = args.timeout if args.timeout is not None else args.time_limit + 65

    def command(instance):
        relative = instance.relative_to(source)
        return [str(binary), "-i", str(instance),
                "-o", str(output / "samples" / relative.parent),
                "-n", str(args.samples), "-t", str(args.time_limit),
                "-s", str(args.seed)]

    if args.dry_run:
        for instance in instances:
            print(shlex.join(command(instance)))
        return 0
    if output.exists():
        parser.error(f"output directory already exists: {output}; choose a new run directory")
    if not binary.is_file() or not os.access(binary, os.X_OK):
        parser.error(f"executable not found: {binary}; run make build first")

    settings = {"samples": args.samples, "time_limit": args.time_limit,
                "seed": args.seed, "jobs": args.jobs,
                "timeout": timeout}
    manifest = {
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "input_root": str(source), "binary": str(binary),
        "binary_sha256": sha256(binary), "platform": platform.platform(),
        "python": platform.python_version(), "git_commit": git_output("rev-parse", "HEAD"),
        "git_status": git_output("status", "--short", "--untracked-files=no"),
        "settings": settings,
        "instances": [{"path": str(p.relative_to(source)), "sha256": sha256(p),
                       "command": command(p)} for p in instances],
    }
    # mkdir without exist_ok also prevents concurrent launches from sharing a run.
    output.mkdir(parents=True)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    stopped = threading.Event()
    process_lock = threading.Lock()
    active = set()
    interrupted_signal = 0

    def kill_group(process):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass

    def cancel(signum, _frame):
        nonlocal interrupted_signal
        # Signals can interrupt another signal handler. Set a plain flag before
        # taking either lock so repeated interrupts cannot re-enter cancellation.
        if interrupted_signal:
            return
        interrupted_signal = signum
        stopped.set()
        with process_lock:
            for process in active:
                kill_group(process)

    def run_one(instance):
        relative = instance.relative_to(source)
        samples_dir = output / "samples" / relative.parent
        sample_file = samples_dir / (relative.name + ".samples")
        log_file = output / "logs" / (str(relative) + ".log")
        started = time.monotonic()
        status, returncode = "cancelled", 128 + interrupted_signal
        if not stopped.is_set():
            samples_dir.mkdir(parents=True, exist_ok=True)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            with log_file.open("w") as log, tempfile.TemporaryDirectory(prefix="highdiv-") as work:
                process = None
                try:
                    # Registration and cancellation share a lock so an interrupt
                    # cannot miss a child that is being started by another thread.
                    with process_lock:
                        if not stopped.is_set():
                            process = subprocess.Popen(command(instance), cwd=work, stdout=log,
                                                       stderr=subprocess.STDOUT, start_new_session=True)
                            active.add(process)
                    if process is not None:
                        returncode = process.wait(timeout=timeout)
                        status = "error" if returncode else "ok"
                        if stopped.is_set():
                            status, returncode = "cancelled", 128 + interrupted_signal
                except subprocess.TimeoutExpired:
                    kill_group(process)
                    process.wait()
                    status, returncode = "timeout", 124
                    log.write(f"\nRunner: wall-clock timeout after {timeout} seconds.\n")
                except OSError as exc:
                    status, returncode = "error", -1
                    log.write(f"\nRunner: {exc}\n")
                finally:
                    with process_lock:
                        active.discard(process)
        if status == "cancelled":
            returncode = 128 + interrupted_signal
        count = 0
        if sample_file.is_file():
            with sample_file.open() as f:
                count = sum(bool(line.strip()) for line in f)
        if status == "ok" and count == 0:
            status = "empty"
        print(f"{relative}: {status} ({count} samples)", flush=True)
        return {"instance": str(relative), "status": status, "returncode": returncode,
                "samples": count, "seconds": f"{time.monotonic() - started:.3f}",
                "sample_file": str(sample_file.relative_to(output)),
                "log_file": str(log_file.relative_to(output))}

    fields = ["instance", "status", "returncode", "samples", "seconds", "sample_file", "log_file"]
    failed = 0
    handlers = {sig: signal.signal(sig, cancel) for sig in (signal.SIGINT, signal.SIGTERM)}
    try:
        with (output / "summary.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            f.flush()
            with ThreadPoolExecutor(max_workers=args.jobs) as pool:
                futures = [pool.submit(run_one, instance) for instance in instances]
                for future in as_completed(futures):
                    row = future.result()
                    writer.writerow(row)
                    f.flush()
                    failed += row["status"] != "ok"
    finally:
        for sig, handler in handlers.items():
            signal.signal(sig, handler)
    print(f"Run saved to {output}; {failed}/{len(instances)} instances need attention.")
    if stopped.is_set():
        return 128 + interrupted_signal
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
