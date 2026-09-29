"""Regression checks for the offline package validator, not model behavior."""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify_bundle import MODES, validate


class PackageChecks(unittest.TestCase):
    def copy_package(self):
        temporary = tempfile.TemporaryDirectory(prefix="gas-skill-test-")
        self.addCleanup(temporary.cleanup)
        target = Path(temporary.name) / "package"
        shutil.copytree(ROOT, target, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        return target

    @staticmethod
    def update_json(path, change):
        data = json.loads(path.read_text(encoding="utf-8"))
        change(data)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def assert_rejected(self, report, suffix):
        self.assertFalse(report["passed"])
        self.assertTrue(any(c["check"].endswith(suffix) and not c["passed"] for c in report["checks"]), report)

    def test_both_skills_have_valid_structure(self):
        report = validate(ROOT, list(MODES))
        self.assertTrue(report["passed"], report)

    def test_installer_has_no_overwrite_preflight(self):
        path = ROOT / "Install-GAS-Skills.ps1"
        self.assertTrue(path.is_file(), "Installer must be supplied before packaging.")
        text = path.read_text(encoding="utf-8-sig")
        self.assertIn("Refusing to overwrite", text)
        self.assertIn("ShouldProcess", text)
        self.assertIn("Directory]::Move", text)
        self.assertIn("Get-FileHash", text)
        self.assertIn("ReparsePoint", text)
        self.assertNotIn("Set-ExecutionPolicy", text)

    def test_missing_skill_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            report = validate(Path(folder), [next(iter(MODES))])
        self.assertEqual(report["failure_count"], 6)

    def test_metadata_name_mismatch_is_rejected(self):
        root = self.copy_package()
        name = "gas-decentralized-development"
        p = root / name / "SKILL.md"
        p.write_text(p.read_text(encoding='utf-8').replace(f"name: {name}", "name: another-skill", 1), encoding="utf-8")
        self.assert_rejected(validate(root, [name]), ":name")

    def test_broken_local_reference_is_rejected(self):
        root = self.copy_package()
        name = "gas-decentralized-development"
        p = root / name / "SKILL.md"
        p.write_text(p.read_text(encoding='utf-8').replace("(references/protocol.md)", "(references/missing.md)", 1), encoding="utf-8")
        self.assert_rejected(validate(root, [name]), "references/missing.md")

    def test_example_approval_cannot_be_fabricated(self):
        root = self.copy_package()
        name = "gas-decentralized-development"
        self.update_json(root / name / "templates/run.example.json", lambda d: d["approval"].update(approved=True))
        self.assert_rejected(validate(root, [name]), ":unapproved-example")

    def test_fake_review_pass_is_rejected(self):
        root = self.copy_package()
        name = "gas-centralized-development"
        self.update_json(root / name / "templates/review.example.json", lambda d: d.update(verdict="PASS"))
        self.assert_rejected(validate(root, [name]), ":review-not-executed")

    def test_fake_independence_is_rejected(self):
        root = self.copy_package()
        name = "gas-centralized-development"
        self.update_json(root / name / "templates/review.example.json", lambda d: d.update(independence_verified=True))
        self.assert_rejected(validate(root, [name]), ":no-fake-independence")

    def test_centralized_self_claim_is_rejected(self):
        root = self.copy_package()
        name = "gas-centralized-development"
        self.update_json(root / name / "templates/run.example.json", lambda d: d["dispatch"].update(method="atomic-self-claim"))
        self.assert_rejected(validate(root, [name]), ":dispatch-distinction")

    def test_fake_pressure_test_pass_is_rejected(self):
        root = self.copy_package()
        name = "gas-decentralized-development"
        self.update_json(root / name / "evals/scenarios.json", lambda d: d.update(execution_status="PASS"))
        self.assert_rejected(validate(root, [name]), ":eval-not-run")

    def test_undefined_rule_reference_is_rejected(self):
        root = self.copy_package()
        name = "gas-decentralized-development"
        self.update_json(root / name / "evals/scenarios.json", lambda d: d["cases"][0]["rules"].append("UNDEFINED-99"))
        self.assert_rejected(validate(root, [name]), ":eval-rule-coverage")

    def test_example_cannot_claim_an_owner(self):
        root = self.copy_package()
        name = "gas-centralized-development"
        self.update_json(root / name / "templates/task.example.json", lambda d: d.update(owner="invented-worker"))
        self.assert_rejected(validate(root, [name]), ":draft-no-fake-evidence")

    def test_manifest_detects_tampering(self):
        root = self.copy_package()
        manifest = root / "manifest.sha256.json"
        self.assertTrue(manifest.is_file())
        rel = "gas-decentralized-development/SKILL.md"
        with (root / rel).open("a", encoding="utf-8") as file:
            file.write("\nAdditional unmanifested content.\n")
        self.assert_rejected(validate(root, list(MODES), package=True), ":sha256:" + rel)

    def test_manifest_rejects_path_escape(self):
        root = self.copy_package()
        outside = root.parent / "outside.txt"
        outside.write_text("not part of the package", encoding="utf-8")
        digest = hashlib.sha256(outside.read_bytes()).hexdigest()
        manifest = root / "manifest.sha256.json"
        self.assertTrue(manifest.is_file())
        self.update_json(manifest, lambda d: d["files"].update({"../outside.txt": digest}))
        self.assert_rejected(validate(root, list(MODES), package=True), ":sha256:../outside.txt")


if __name__ == "__main__":
    unittest.main()
