"""CLI errors must preserve existing experiment results."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name("run_runtime_experiments.py")


class ExperimentCliTests(unittest.TestCase):
    def test_existing_output_is_a_usage_error_and_is_not_modified(self):
        with tempfile.TemporaryDirectory(prefix="gas-experiment-cli-") as temporary:
            root = Path(temporary)
            for kind in ("directory", "file"):
                with self.subTest(kind=kind):
                    output = root / kind
                    if kind == "directory":
                        output.mkdir()
                        preserved = output / "summary.json"
                    else:
                        preserved = output
                    preserved.write_bytes(b"previous result")
                    result = subprocess.run([sys.executable, "-X", "utf8", "-B", str(SCRIPT), "--output", str(output)],
                                            capture_output=True, text=True, encoding="utf-8")
                    self.assertEqual(preserved.read_bytes(), b"previous result")
                    if kind == "directory":
                        self.assertEqual(list(output.iterdir()), [preserved])
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("error:", result.stderr)
                    self.assertIn("already exists", result.stderr)
                    self.assertNotIn("Traceback", result.stderr)


if __name__ == "__main__":
    unittest.main()
