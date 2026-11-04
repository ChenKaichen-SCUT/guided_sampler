"""Integration checks for result evaluation using the locally built Z3."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "venv/bin/python3"
BUILT_Z3 = ROOT / "venv/lib/libz3.so"


@unittest.skipUnless(BUILT_Z3.is_file(), "run make build to enable metric integration checks")
class EvaluationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="highdiv-metrics-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.formula = self.root / "tiny.smt2"
        self.formula.write_text("(declare-const x Int)\n(assert (>= x 0))\n")
        self.run = self.root / "run"
        (self.run / "samples").mkdir(parents=True)
        self.samples = self.run / "samples/tiny.smt2.samples"
        self.samples.write_text("0: x:0;\n1: x:1;\n")
        (self.run / "manifest.json").write_text(json.dumps({
            "input_root": str(self.root),
            "instances": [{"path": "tiny.smt2", "sha256": hashlib.sha256(self.formula.read_bytes()).hexdigest()}],
        }))
        self.summary("ok")

    def summary(self, status):
        with (self.run / "summary.csv").open("w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["instance", "status", "sample_file"])
            writer.writeheader()
            writer.writerow({"instance": "tiny.smt2", "status": status,
                             "sample_file": "samples/tiny.smt2.samples"})

    def evaluate(self, metric="satisfies"):
        return subprocess.run([str(PYTHON), str(ROOT / "scripts/evaluate.py"),
                               str(self.run), "--metric", metric],
                              text=True, capture_output=True, timeout=15)

    def row(self, metric="satisfies"):
        path = self.run / (metric + ".csv")
        self.assertTrue(path.is_file(), "evaluation must write a result row")
        with path.open() as f:
            return next(csv.DictReader(f))

    def test_satisfying_samples_are_checked_and_reported_as_percentage(self):
        result = self.evaluate()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.row()["Percentage"], "100.00%")
        self.assertEqual(self.row()["Status"], "ok")

    def test_invalid_samples_make_validation_fail(self):
        self.samples.write_text("0: x:0;\n1: x:-1;\n")
        result = self.evaluate()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.row()["Percentage"], "50.00%")
        self.assertEqual(self.row()["Status"], "invalid_samples")

    def test_timeout_samples_are_not_reported_as_valid_measurements(self):
        self.summary("timeout")
        result = self.evaluate()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.row()["Percentage"], "")
        self.assertEqual(self.row()["Status"], "sampling_timeout")

    def test_changed_formula_is_detected_before_evaluation(self):
        self.formula.write_text("(declare-const x Int)\n(assert (< x 0))\n")
        result = self.evaluate()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.row()["Status"], "input_changed")

    def test_existing_metrics_are_not_overwritten(self):
        output = self.run / "satisfies.csv"
        output.write_text("keep original\n")
        result = self.evaluate()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(output.read_text(), "keep original\n")


if __name__ == "__main__":
    unittest.main()
