"""Exercise the generated Z3 install rule in a disposable prefix."""
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "z3/scripts"))
from mk_util import MakeRuleCmd
sys.path.pop(0)


class BuildInstallTests(unittest.TestCase):
    def test_python_library_link_can_be_installed_repeatedly(self):
        with tempfile.TemporaryDirectory(prefix="highdiv-install-") as directory:
            root = Path(directory)
            (root / "library.so").write_text("local build")
            rule = io.StringIO()
            MakeRuleCmd.create_symbolic_link(rule, "library.so", "binding.so")
            makefile = root / "Makefile"
            makefile.write_text("PREFIX := " + directory + "\n.PHONY: install\ninstall:\n" + rule.getvalue())
            for _ in range(2):
                result = subprocess.run(["make", "-f", str(makefile), "install"],
                                        capture_output=True, text=True, timeout=10)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((root / "binding.so").read_text(), "local build")
