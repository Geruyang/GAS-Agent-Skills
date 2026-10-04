"""Regression checks for external-review findings; no live agent execution."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify_bundle import COMBINED, MODES, validate

NAMES = (*MODES, COMBINED)
CENTRAL = "gas-centralized-development"


class ReviewValidatorChecks(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gas-review-validator-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "package"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def rejected(self, name, suffix):
        report = validate(self.root, [name])
        failures = [item for item in report["checks"] if not item["passed"]]
        self.assertTrue(any(item["check"].endswith(suffix) for item in failures), failures)

    def test_combined_common_skill_checks_cannot_be_bypassed(self):
        path = self.root / COMBINED / "SKILL.md"
        original = path.read_text(encoding="utf-8")
        mutations = (
            (":frontmatter", original.replace("---", "removed", 1)),
            (":name", original.replace("name: " + COMBINED, "name: wrong-name", 1)),
            (":description", original.replace("description: Use when ", "description: Invalid ", 1)),
            (":heading:## 权责边界", original.replace("## 权责边界", "## Removed", 1)),
            (":main-size", original + "\n" * 201),
        )
        for suffix, content in mutations:
            with self.subTest(suffix=suffix):
                path.write_text(content, encoding="utf-8")
                self.rejected(COMBINED, suffix)
        path.write_bytes(b"\xff")
        self.rejected(COMBINED, ":utf8")

    def test_combined_must_declare_its_own_common_rules_and_limits(self):
        for relative in ("SKILL.md", "references/protocol.md"):
            path = self.root / COMBINED / relative
            content = path.read_text(encoding="utf-8").replace("AUTH-01", "REMOVED_RULE").replace("worktree", "removed")
            path.write_text(content, encoding="utf-8")
        self.rejected(COMBINED, ":common-rules")
        self.rejected(COMBINED, ":enforcement-limits")

    def test_combined_existing_sibling_links_and_eleven_cases_remain_valid(self):
        path = self.root / COMBINED / "evals/scenarios.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        data["cases"] = data["cases"][:11]
        path.write_text(json.dumps(data), encoding="utf-8")
        report = validate(self.root, [COMBINED])
        self.assertTrue(report["passed"], [item for item in report["checks"] if not item["passed"]])

    def test_eval_metadata_is_required_for_every_mode(self):
        for name in NAMES:
            path = self.root / name / "evals/scenarios.json"
            original = path.read_bytes()
            data = json.loads(original)
            mutations = (("schema_version", None), ("schema_version", True),
                         ("schema_version", 99), ("skill", "wrong"),
                         ("purpose", " "), ("procedure", []))
            for field, value in mutations:
                with self.subTest(name=name, field=field, value=value):
                    changed = dict(data, **{field: value})
                    path.write_text(json.dumps(changed), encoding="utf-8")
                    self.rejected(name, ":eval-metadata")
            path.write_bytes(original)

    def test_eval_structure_assertions_and_rule_references_for_every_mode(self):
        mutations = (
            (":eval-structure", lambda d: d.update(cases=[True])),
            (":eval-structure", lambda d: d["cases"][0].update(id=" ")),
            (":eval-structure", lambda d: d["cases"][0].update(rules=[])),
            (":eval-unique", lambda d: d["cases"][1].update(id=d["cases"][0]["id"])),
            (":eval-not-run", lambda d: d["cases"][0].update(status="PASS")),
            (":eval-assertions", lambda d: d["cases"][0].update(prompt=" ")),
            (":eval-assertions", lambda d: d["cases"][0].update(expected_actions="looks truthy")),
            (":eval-assertions", lambda d: d["cases"][0].update(failure_actions=[" "])),
            (":eval-rule-coverage", lambda d: d["cases"][0]["rules"].append("UNDEFINED-99")),
        )
        for name in NAMES:
            path = self.root / name / "evals/scenarios.json"
            original = path.read_bytes()
            for suffix, mutate in mutations:
                with self.subTest(name=name, suffix=suffix):
                    data = json.loads(original)
                    mutate(data)
                    path.write_text(json.dumps(data), encoding="utf-8")
                    self.rejected(name, suffix)
            path.write_bytes(original)

    def test_eval_schema_versions_are_independent_of_run_contracts(self):
        for name, version in zip(NAMES, (1, 3, 1)):
            # MODES order is decentralized then centralized; evals use 1/3/1,
            # while run contracts use 2/3/1.
            path = self.root / name / "evals/scenarios.json"
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))["schema_version"], version)
            report = validate(self.root, [name])
            self.assertTrue(report["passed"], [item for item in report["checks"] if not item["passed"]])

    def test_pressures_are_optional_for_each_case(self):
        path = self.root / COMBINED / "evals/scenarios.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        for case in data["cases"]:
            case.pop("pressures", None)
        path.write_text(json.dumps(data), encoding="utf-8")
        report = validate(self.root, [COMBINED])
        self.assertTrue(report["passed"], [item for item in report["checks"] if not item["passed"]])

    def test_pure_mode_count_and_pressure_baselines_are_preserved(self):
        for name in MODES:
            path = self.root / name / "evals/scenarios.json"
            original = path.read_bytes()
            data = json.loads(original)
            data["cases"] = data["cases"][:11]
            path.write_text(json.dumps(data), encoding="utf-8")
            self.rejected(name, ":eval-count")
            data = json.loads(original)
            for case in data["cases"]:
                case.pop("pressures", None)
            path.write_text(json.dumps(data), encoding="utf-8")
            self.rejected(name, ":eval-pressure")
            path.write_bytes(original)

    def test_description_limit_applies_to_field_not_entire_frontmatter(self):
        for name in NAMES:
            path = self.root / name / "SKILL.md"
            original = path.read_text(encoding="utf-8")
            for length, expected in ((1024, True), (1025, False)):
                with self.subTest(name=name, length=length):
                    content = re.sub(r"^description: .*$", "description: Use when " + "x" * (length - 9), original, flags=re.M)
                    content = content.replace("\n---\n", "\nmetadata:\n  note: " + "x" * 1200 + "\n---\n", 1)
                    path.write_text(content, encoding="utf-8")
                    report = validate(self.root, [name])
                    check = next(item for item in report["checks"] if item["check"] == name + ":description-size")
                    self.assertEqual(check["passed"], expected)
                    self.assertFalse(any(item["check"].endswith(":frontmatter-size") for item in report["checks"]))
                    if expected:
                        self.assertTrue(report["passed"], [item for item in report["checks"] if not item["passed"]])
            path.write_text(original, encoding="utf-8")

    def test_validator_defects_are_structured_failures_with_type(self):
        path = self.root / CENTRAL / "scripts/validate_skill.py"
        for exception in ("NameError", "ImportError", "ZeroDivisionError", "IndexError", "RecursionError"):
            with self.subTest(exception=exception):
                path.write_text("raise " + exception + "('regression probe')\n", encoding="utf-8")
                report = validate(self.root, [CENTRAL])
                check = next(item for item in report["checks"] if item["check"] == CENTRAL + ":v3:validator")
                self.assertFalse(check["passed"])
                self.assertIn(exception, check["detail"])

    def test_missing_validator_loader_is_explicit_failure(self):
        for spec in (None, SimpleNamespace(loader=None)):
            with self.subTest(spec=spec):
                with patch("verify_bundle.importlib.util.spec_from_file_location", return_value=spec):
                    report = validate(self.root, [CENTRAL])
                check = next(item for item in report["checks"] if item["check"] == CENTRAL + ":v3:validator")
                self.assertFalse(check["passed"])
                self.assertIn("loader", check["detail"])

    def test_control_flow_exceptions_are_not_swallowed(self):
        path = self.root / CENTRAL / "scripts/validate_skill.py"
        path.write_text("raise KeyboardInterrupt()\n", encoding="utf-8")
        with self.assertRaises(KeyboardInterrupt):
            validate(self.root, [CENTRAL])

    def test_explicit_root_validates_copied_package_manifest(self):
        files = {path.relative_to(self.root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                 for path in self.root.rglob("*") if path.is_file() and path.name != "manifest.sha256.json"}
        (self.root / "manifest.sha256.json").write_text(json.dumps({"files": files}), encoding="utf-8")
        clean = validate(self.root, list(MODES), package=True)
        self.assertTrue(clean["passed"], [item for item in clean["checks"] if not item["passed"]])
        rel = "gas-decentralized-development/SKILL.md"
        with (self.root / rel).open("a", encoding="utf-8") as stream:
            stream.write("\nTampered only in copied package.\n")
        report_path = self.root.parent / "report.json"
        result = subprocess.run([sys.executable, "-B", str(ROOT / "verify_bundle.py"),
                                 "--root", str(self.root), "--report", str(report_path)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertTrue(any(item["check"] == "package:sha256:" + rel and not item["passed"]
                            for item in report["checks"]))

    def test_installer_default_and_absolute_path_checks(self):
        path = self.root / "Install-GAS-Skills.ps1"
        original = path.read_text(encoding="utf-8-sig")
        mutations = (
            (":installer-default", original.replace("GetFolderPath('UserProfile')", "GetFolderPath('Desktop')")),
            (":installer-absolute-destination", original.replace("IsPathRooted($Destination)", "IsPathRooted('C:\\')")),
        )
        for suffix, content in mutations:
            with self.subTest(suffix=suffix):
                path.write_text(content, encoding="utf-8")
                report = validate(self.root, list(MODES), package=True)
                self.assertTrue(any(item["check"].endswith(suffix) and not item["passed"]
                                    for item in report["checks"]))

    def test_repository_root_misuse_has_actionable_diagnostic(self):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "verify_bundle.py"),
                                 "--root", str(ROOT.parent)], capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--root", result.stdout)
        self.assertIn("GAS-Agent-Skills", result.stdout)


if __name__ == "__main__":
    unittest.main()
