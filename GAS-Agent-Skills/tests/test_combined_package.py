"""The combined package has its own schema; do not apply pure-mode templates."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "gas-combined-development"
SKILLS = ("gas-centralized-development", "gas-decentralized-development", NAME)


class CombinedPackageChecks(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gas-combined-package-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name) / "package"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))

    def check(self, expected, name=NAME):
        result = subprocess.run([sys.executable, "-B", str(ROOT / "verify_bundle.py"),
                                 "--root", str(self.root), "--skill", name],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stdout + result.stderr)

    def change_run(self, change):
        path = self.root / NAME / "templates/run.example.json"
        record = json.loads(path.read_text(encoding="utf-8"))
        change(record)
        path.write_text(json.dumps(record), encoding="utf-8")

    def test_combined_schema_is_validated_without_pure_mode_tasks(self):
        self.check(0)

    def test_fabricated_delivery_is_rejected(self):
        self.change_run(lambda r: r["delivery"].update(status="RELEASED", gates_verified=True))
        self.check(1)

    def test_outer_peers_cannot_be_subordinates(self):
        self.change_run(lambda r: r["bridge"].update(outer_peers_outside_inner_command=False))
        self.check(1)

    def test_five_identity_default_is_rejected(self):
        self.change_run(lambda r: r["runtime"].update(required_distinct_identities_minimum=5))
        self.check(1)

    def test_broken_reference_is_rejected(self):
        path = self.root / NAME / "SKILL.md"
        path.write_text(path.read_text(encoding="utf-8").replace(
            "references/protocol.md", "references/missing.md"), encoding="utf-8")
        self.check(1)

    def test_malformed_bridge_fails_without_crash(self):
        self.change_run(lambda r: r.update(bridge=True))
        self.check(1)

    def reject_mutation(self, name, relative, change):
        path = self.root / name / relative
        original = path.read_bytes()
        record = json.loads(original)
        change(record)
        path.write_text(json.dumps(record), encoding="utf-8")
        try:
            self.check(1, name)
        finally:
            path.write_bytes(original)

    def test_all_runtime_examples_remain_valid_unexecuted_templates(self):
        for name in SKILLS:
            with self.subTest(name=name):
                self.check(0, name)

    def test_runtime_examples_reject_execution_or_invented_evidence(self):
        mutations = (
            ("live_record", lambda r: r.update(example_only=False)),
            ("binding", lambda r: r["binding"].update(recipient="fabricated")),
            ("check_execution", lambda r: r["checks"][0].update(execution="COMPLETED")),
            ("check_result", lambda r: r["checks"][0].update(result="PASS")),
            ("preflight", lambda r: r["critical_capability_preflight"][0].update(result="PASS")),
            ("preflight_assessed", lambda r: r["preflight_applicability"].update(status="NOT_APPLICABLE")),
            ("evidence", lambda r: r.update(evidence=[{"id": "fabricated"}])),
            ("receipt", lambda r: r["lifecycle"]["sent"].update(host_receipt_ref="fabricated")),
            ("retry", lambda r: r["checkpoint"].update(retry_requested=True)),
            ("progress", lambda r: r["progress"].update(execution="COMPLETED")),
            ("reviewer", lambda r: r["review_method"].update(reviewer_identity="fabricated")),
            ("risk_acceptance", lambda r: r["risk_acceptance"].update(status="ACCEPTED")),
            ("human_decision", lambda r: r["human_adjudication"].update(identity="fabricated")),
            ("delivery", lambda r: r["delivery"].update(execution="COMPLETED")),
            ("measurement", lambda r: r["metrics"].update(elapsed_seconds=0)),
        )
        for name in SKILLS:
            for label, change in mutations:
                with self.subTest(name=name, mutation=label):
                    self.reject_mutation(name, "templates/runtime.example.json", change)

    def test_malformed_runtime_sections_fail_without_crashing(self):
        for name in SKILLS:
            for field in ("binding", "checks", "critical_capability_preflight", "lifecycle",
                          "checkpoint", "review_method", "metrics"):
                with self.subTest(name=name, field=field):
                    self.reject_mutation(name, "templates/runtime.example.json",
                                         lambda r, key=field: r.update({key: True}))

    def test_runtime_scenarios_reject_fabricated_observations(self):
        mutations = (
            ("live_record", lambda r: r.update(example_only=False)),
            ("execution", lambda r: r.update(execution_status="PASS")),
            ("case", lambda r: r["cases"][0].update(status="PASS")),
            ("result", lambda r: r["cases"][0].update(observed_result={"passed": True})),
            ("elapsed", lambda r: r["cases"][0].update(elapsed_seconds=0)),
            ("tokens", lambda r: r["cases"][0].update(tokens=0)),
            ("cost", lambda r: r["cases"][0].update(cost=0)),
            ("malformed_cases", lambda r: r.update(cases=True)),
        )
        for name in SKILLS:
            for label, change in mutations:
                with self.subTest(name=name, mutation=label):
                    self.reject_mutation(name, "evals/runtime-scenarios.json", change)

    def test_reuse_examples_reject_fabricated_execution_and_checker(self):
        mutations = (
            ("status", lambda r: r["evidence_reuse"][0].update(status="PASS")),
            ("checker", lambda r: r["evidence_reuse"][0].update(checker_identity="fabricated")),
            ("environment", lambda r: r["evidence_reuse"][0]["environment_applicability"].update(status="VERIFIED")),
            ("dependency_check", lambda r: r["dependency_details"].update(check_execution="COMPLETED")),
            ("dependency_checker", lambda r: r["dependency_details"].update(checked_by_identity="fabricated")),
            ("malformed_entries", lambda r: r.update(evidence_reuse=True)),
            ("malformed_entry", lambda r: r.update(evidence_reuse=[True])),
        )
        for label, change in mutations:
            with self.subTest(mutation=label):
                self.reject_mutation(NAME, "templates/review-reuse.example.json", change)


if __name__ == "__main__":
    unittest.main()
