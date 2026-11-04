"""Regression checks for real sampling, model types, and distinct assignments."""
import os
from pathlib import Path
import resource
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREFIX = ROOT / "venv"
BINARY = ROOT / "HighDiv/highdiv"


def no_core_dump():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


@unittest.skipUnless(BINARY.is_file() and (PREFIX / "lib/libz3.so").is_file(),
                     "run make build to enable sampler integration checks")
class SamplerRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="highdiv-runtime-tests-")
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.probe = cls.root / "sampler_runtime"
        command = [*shlex.split(os.environ.get("CXX", "g++")), "-std=c++20", "-O0",
                   "-fno-access-control", "-I", str(PREFIX / "include"),
                   "-I", str(ROOT / "HighDiv/src"), str(ROOT / "tests/sampler_runtime.cpp"),
                   str(ROOT / "HighDiv/src/sampler/liasampler.cpp"),
                   str(ROOT / "HighDiv/src/sampler/sampler.cpp"),
                   "-L", str(PREFIX / "lib"), "-Wl,-rpath," + str(PREFIX / "lib"),
                   "-lz3", "-o", str(cls.probe)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if result.returncode:
            raise AssertionError("C++ runtime probe compilation failed:\n" + result.stderr)

    def check_probe(self, case):
        result = subprocess.run([str(self.probe), case, str(self.root / (case + ".samples"))],
                                capture_output=True, text=True, timeout=5, preexec_fn=no_core_dump)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def sample(self, name, formula, count=8, limit=2):
        source = self.root / (name + ".smt2")
        source.write_text("(set-logic QF_LIA)\n" + formula)
        result = subprocess.run([str(BINARY), "-i", str(source), "-o", str(self.root),
                                 "-n", str(count), "-t", str(limit), "-s", "0"],
                                capture_output=True, text=True, timeout=5, preexec_fn=no_core_dump)
        self.assertEqual(result.returncode, 0, result.stdout[-2000:] + result.stderr)
        return (self.root / (source.name + ".samples")).read_text().splitlines()

    def test_distinct_assignments_survive_fingerprint_collision(self):
        self.check_probe("distinct_samples")

    def test_ls_api_rejects_false(self):
        self.check_probe("ls_false")

    def test_ls_model_preserves_asserted_boolean_units(self):
        self.check_probe("ls_boolean_model")

    def test_boolean_guidance_preserves_the_variable_sort(self):
        lines = self.sample("bool", "(declare-const b Bool)\n(declare-const x Int)\n"
                            "(assert (or b (> x 0)))\n(assert (>= x 0))\n(assert (<= x 10))\n")
        self.assertGreaterEqual(len(lines), 4)
        for line in lines:
            values = dict(item.split(":", 1) for item in line.split(": ", 1)[1].split(";") if item)
            self.assertIn(values["b"], ("true", "false"))
            x = int(values["x"])
            self.assertTrue(0 <= x <= 10 and (values["b"] == "true" or x > 0), line)

    def test_unsatisfiable_formula_produces_no_samples(self):
        lines = self.sample("unsat", "(declare-const x Int)\n(assert (< x 0))\n(assert (> x 0))\n",
                            limit=0.2)
        self.assertEqual(lines, [], "an inconsistent formula has no valid samples")

    def test_zero_time_budget_produces_no_samples(self):
        lines = self.sample("zero", "(declare-const x Int)\n(assert (> x 0))\n", limit=0)
        self.assertEqual(lines, [])

    def test_model_conversion_preserves_original_formula(self):
        lines = self.sample("converted", "(declare-const x Int)\n(assert (> x 0))\n", limit=0.2)
        self.assertTrue(lines)
        for line in lines:
            values = dict(item.split(":", 1) for item in line.split(": ", 1)[1].split(";") if item)
            self.assertGreater(int(values["x"]), 0, line)
