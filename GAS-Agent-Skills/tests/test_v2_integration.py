"""The bundle entry point must enforce the commander v3 record contract."""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify_bundle import validate

NAME = "gas-centralized-development"


class CommanderV3IntegrationTests(unittest.TestCase):
    def copy_package(self):
        temporary = tempfile.TemporaryDirectory(prefix="gas-v3-bundle-")
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / "package"
        shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns("__pycache__"))
        return root

    def test_bundle_rejects_fabricated_management_acceptance(self):
        root = self.copy_package()
        path = root / NAME / "templates/decision.example.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        record["decision"] = "ACCEPT"
        path.write_text(json.dumps(record), encoding="utf-8")
        report = validate(root, [NAME])
        self.assertTrue(any(c["check"].endswith(":v3:decision-not-decided")
                            and not c["passed"] for c in report["checks"]))

    def test_missing_v3_validator_fails_closed(self):
        root = self.copy_package()
        (root / NAME / "scripts/validate_skill.py").unlink()
        report = validate(root, [NAME])
        self.assertTrue(any(c["check"].endswith(":v3:validator")
                            and not c["passed"] for c in report["checks"]))

    def test_malformed_run_objects_report_failure_without_crashing(self):
        root = self.copy_package()
        path = root / NAME / "templates/run.example.json"
        original = path.read_bytes()
        for key in ("approval", "budget", "runtime", "controls", "dispatch"):
            for invalid in (None, [], True, "broken", 0):
                with self.subTest(key=key, invalid=invalid):
                    record = json.loads(original)
                    record[key] = invalid
                    path.write_text(json.dumps(record), encoding="utf-8")
                    self.assertFalse(validate(root, [NAME])["passed"])

    def test_malformed_scenario_containers_fail_without_crash(self):
        root = self.copy_package()
        path = root / NAME / "evals/scenarios.json"
        original = path.read_bytes()
        for invalid in (None, [None], ["broken"], {"x": []}):
            with self.subTest(invalid=invalid):
                record = json.loads(original)
                record["cases"] = invalid
                path.write_text(json.dumps(record), encoding="utf-8")
                self.assertFalse(validate(root, [NAME])["passed"])


if __name__ == "__main__":
    unittest.main()
