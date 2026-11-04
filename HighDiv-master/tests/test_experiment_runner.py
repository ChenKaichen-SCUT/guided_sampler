"""Exercise the runner's filesystem/process contract without compiling Z3."""
import csv
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/run_benchmarks.py"


class ExperimentRunnerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="highdiv test ")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.inputs = self.root / "inputs"
        self.inputs.mkdir()
        self.output = self.root / "run"
        # The real sampler is expensive to build and nondeterministic. This tiny
        # executable implements its CLI/file boundary, including failure modes.
        self.binary = self.root / "sampler double"
        self.binary.write_text(
            "#!" + sys.executable + "\n"
            "import argparse, os, pathlib, sys, time\n"
            "p = argparse.ArgumentParser()\n"
            "for flag in ['-i', '-o', '-n', '-t', '-s']:\n"
            "    p.add_argument(flag, required=True)\n"
            "a = p.parse_args()\n"
            "kind = pathlib.Path(a.i).read_text().strip()\n"
            "if kind == 'fail': sys.exit(7)\n"
            "if kind == 'sleep':\n"
            "    (pathlib.Path(a.o) / 'started.pid').write_text(str(os.getpid()))\n"
            "    time.sleep(10)\n"
            "if kind != 'empty':\n"
            "    output = pathlib.Path(a.o) / (pathlib.Path(a.i).name + '.samples')\n"
            "    output.write_text('0: x:' + a.s + ';\\n')\n"
            "print('sampling finished')\n"
        )
        self.binary.chmod(0o755)

    def instance(self, name, content="ok"):
        path = self.inputs / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        return path

    def run_runner(self, *args):
        return subprocess.run(
            [sys.executable, str(RUNNER), str(self.inputs), str(self.output),
             "--binary", str(self.binary), *args],
            cwd=self.root, text=True, capture_output=True, timeout=15,
        )

    def rows(self):
        with (self.output / "summary.csv").open() as f:
            return sorted(csv.DictReader(f), key=lambda row: row["instance"])

    def test_nested_duplicate_names_and_spaces_are_kept_separate(self):
        self.instance("family one/same.smt2")
        self.instance("family two/same.smt2")
        self.instance("family one/odd;name.smt2")
        result = self.run_runner("--jobs", "2", "--seed", "23", "--samples", "3")
        self.assertEqual(result.returncode, 0, result.stderr)
        for name in ("family one/same.smt2", "family two/same.smt2", "family one/odd;name.smt2"):
            self.assertEqual((self.output / "samples" / (name + ".samples")).read_text(), "0: x:23;\n")
            self.assertIn("sampling finished", (self.output / "logs" / (name + ".log")).read_text())
        self.assertEqual([r["status"] for r in self.rows()], ["ok", "ok", "ok"])
        manifest = json.loads((self.output / "manifest.json").read_text())
        self.assertEqual(manifest["settings"]["seed"], 23)
        self.assertEqual(len(manifest["instances"]), 3)

    def test_dry_run_does_not_create_outputs_or_require_built_binary(self):
        self.instance("one.smt2")
        self.binary.unlink()
        result = self.run_runner("--dry-run")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("one.smt2", result.stdout)
        self.assertFalse(self.output.exists())

    def test_existing_run_is_never_overwritten(self):
        self.instance("one.smt2")
        self.output.mkdir()
        sentinel = self.output / "keep.txt"
        sentinel.write_text("published data")
        result = self.run_runner()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(sentinel.read_text(), "published data")
        self.assertFalse((self.output / "summary.csv").exists())

    def test_failure_timeout_and_missing_samples_are_visible(self):
        self.instance("a-fail.smt2", "fail")
        self.instance("b-timeout.smt2", "sleep")
        self.instance("c-empty.smt2", "empty")
        result = self.run_runner("--timeout", "0.2", "--jobs", "2")
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue((self.output / "summary.csv").is_file(), result.stderr)
        rows = self.rows()
        self.assertEqual([r["status"] for r in rows], ["error", "timeout", "empty"])
        self.assertEqual(rows[0]["returncode"], "7")

    def test_invalid_limits_and_empty_input_fail_before_writing(self):
        self.instance("one.smt2")
        for args in [("--samples", "0"), ("--samples", "4294967296"),
                     ("--time-limit", "nan"), ("--time-limit", "inf"),
                     ("--jobs", "0"), ("--timeout", "-1")]:
            with self.subTest(args=args):
                result = self.run_runner(*args)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("error:", result.stderr)
                self.assertFalse(self.output.exists())
        (self.inputs / "one.smt2").unlink()
        result = self.run_runner()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.output.exists())

    def test_interrupt_stops_running_and_queued_instances(self):
        self.instance("a-sleep.smt2", "sleep")
        self.instance("b-sleep.smt2", "sleep")
        process = subprocess.Popen(
            [sys.executable, str(RUNNER), str(self.inputs), str(self.output),
             "--binary", str(self.binary), "--jobs", "1"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            start_new_session=True,
        )
        pidfile = self.output / "samples/started.pid"
        try:
            deadline = time.monotonic() + 3
            while not pidfile.exists() and time.monotonic() < deadline:
                time.sleep(0.02)
            self.assertTrue(pidfile.exists(), "sampler must have started")
            child_pid = int(pidfile.read_text())
            process.send_signal(signal.SIGINT)
            try:
                process.communicate(timeout=3)
            except subprocess.TimeoutExpired:
                self.fail("interrupt must stop active and queued sampling promptly")
            self.assertEqual(process.returncode, 130)
            with self.assertRaises(ProcessLookupError):
                os.kill(child_pid, 0)
            self.assertFalse((self.output / "logs/b-sleep.smt2.log").exists())
            self.assertEqual([r["status"] for r in self.rows()], ["cancelled", "cancelled"])
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGKILL)
            process.communicate(timeout=3)


if __name__ == "__main__":
    unittest.main()
