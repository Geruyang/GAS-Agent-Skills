"""2026-10-04 static/mutation checks; do not prove agent behavior or real readings."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

class RoleUpdateContract(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "skill"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__"))
    def edit(self, name, change):
        path = self.root / name
        value = json.loads(path.read_text(encoding="utf-8-sig"))
        change(value)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
    def validate(self):
        spec = importlib.util.spec_from_file_location("role_checker", ROOT / "scripts/validate_skill.py")
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        return checker.validate(self.root)
    def reject(self, fragment):
        result = self.validate()
        failures = [c["name"] for c in result["checks"] if not c["ok"]]
        self.assertFalse(result["ok"], failures)
        self.assertTrue(any(fragment in item for item in failures), failures)
    def test_default_valid(self):
        self.assertTrue(self.validate()["ok"])
    def test_three_executors_configurable(self):
        def configure(d):
            d["execution_team"].update(executor_count=3, count_source="proposed", planned_distinct_subagents=6)
            d["budget"]["max_active_workers"] = 3
        self.edit("templates/run.example.json", configure)
        self.assertTrue(self.validate()["ok"])
    def test_user_count_configurable(self):
        self.edit("templates/run.example.json", lambda d: d["execution_team"].update(executor_count=2, count_source="user", planned_distinct_subagents=5))
        self.assertTrue(self.validate()["ok"])
    def test_count_must_be_positive_integer(self):
        for invalid in (0, -1, True, None, "3"):
            with self.subTest(invalid=invalid):
                self.edit("templates/run.example.json", lambda d: d["execution_team"].update(executor_count=invalid))
                self.reject("positive-count")
    def test_wrong_team_formula(self):
        self.edit("templates/run.example.json", lambda d: d["execution_team"].update(executor_count=3, count_source="user", planned_distinct_subagents=4))
        self.reject("team-formula")
    def test_multiple_count_not_default(self):
        self.edit("templates/run.example.json", lambda d: d["execution_team"].update(executor_count=3, planned_distinct_subagents=6))
        self.reject("count-source")
    def test_reviewer_cannot_write_code(self):
        self.edit("templates/run.example.json", lambda d: d["review_policy"].update(reviewer_may_write_verification_code=True))
        self.reject("code-owner")
    def test_review_record_cannot_allow_writing(self):
        self.edit("templates/review.example.json", lambda d: d.update(reviewer_may_write_verification_code=True))
        self.reject("analysis-only")
    def test_rerun_existing_is_permitted(self):
        doc = json.loads((self.root / "templates/review.example.json").read_text(encoding="utf-8"))
        self.assertIn("rerun_existing_commands", doc["allowed_methods"])
        self.assertTrue(self.validate()["ok"])
    def test_reviewer_input_categories_required(self):
        self.edit("templates/run.example.json", lambda d: d["review_policy"].update(primary_inputs=["executor_outputs"]))
        self.reject("review-policy:inputs")
    def test_task_owner_binding_required(self):
        self.edit("templates/task.example.json", lambda d: d["execution_assignment"].update(task_id="other"))
        self.reject("development-verification-binding")
    def test_no_fabricated_test_owner(self):
        self.edit("templates/task.example.json", lambda d: d["test_plan"].update(code_owner_identity="invented"))
        self.reject("verification-code-owner-unknown")
    def test_monitoring_cannot_claim_observation(self):
        self.edit("templates/supervision.example.json", lambda d: d["monitoring"]["board_current"].update(status="PASS", observations=[{"value":0.1}]))
        self.reject("board_current:unobserved")
    def test_monitoring_cannot_claim_safety(self):
        self.edit("templates/supervision.example.json", lambda d: d["monitoring_capabilities"].update(safety_guaranteed=True))
        self.reject("no-safety-claim")
    def test_monitoring_unknown_threshold_required(self):
        self.edit("templates/supervision.example.json", lambda d: d["monitoring"]["board_voltage"].update(threshold_ref="invented"))
        self.reject("threshold-unknown")
    def test_all_subordinate_status_coverage_required(self):
        self.edit("templates/supervision.example.json", lambda d: d["monitoring"].pop("subordinate_agent_status"))
        self.reject("monitoring-dimensions")
    def test_resource_constraints_required(self):
        self.edit("templates/run.example.json", lambda d: d["parallel_dispatch"].update(constraints=["dependencies"]))
        self.reject("constraints")
    def test_global_serial_strategy_rejected(self):
        self.edit("templates/run.example.json", lambda d: d["parallel_dispatch"].update(strategy="always_serial"))
        self.reject("parallel-dispatch:strategy")
    def test_malformed_additions_rejected_without_crash(self):
        for key in ("execution_team", "review_policy", "parallel_dispatch"):
            with self.subTest(key=key):
                path = self.root / "templates/run.example.json"
                original = path.read_bytes()
                self.edit("templates/run.example.json", lambda d: d.update({key: None}))
                self.reject("object")
                path.write_bytes(original)
    def test_shared_runtime_owner_declaration_required(self):
        self.edit("templates/runtime.example.json", lambda d: d.pop("verification_ownership"))
        self.reject("runtime:verification-owner-unknown")
    def test_new_scenarios_remain_not_run(self):
        doc = json.loads((self.root / "evals/scenarios.json").read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(doc["cases"]),58)
        self.assertTrue(all(case["status"]=="NOT_RUN" for case in doc["cases"]))

    def test_monitoring_freshness_fields_unknown(self):
        doc = json.loads((self.root / "templates/supervision.example.json").read_text(encoding="utf-8"))
        for dimension in doc["monitoring"].values():
            for field in ("sampled_at", "evaluated_at", "freshness_rule_ref", "validity_window"):
                self.assertIn(field, dimension)
                self.assertIsNone(dimension[field])
    def test_freshness_rule_omission_rejected(self):
        self.edit("templates/supervision.example.json", lambda d: d["monitoring"]["board_voltage"].pop("freshness_rule_ref",None))
        self.reject("board_voltage:freshness-unknown")
    def test_fabricated_sample_time_rejected(self):
        self.edit("templates/supervision.example.json", lambda d: d["monitoring"]["board_current"].update(sampled_at="2026-10-04T00:00:00Z"))
        self.reject("board_current:freshness-unknown")
    def test_freshness_and_replacement_cases_not_run(self):
        doc = json.loads((self.root / "evals/scenarios.json").read_text(encoding="utf-8"))
        tags = {tag for case in doc["cases"] for tag in case.get("tags",[])}
        self.assertTrue({"telemetry-freshness", "telemetry-gap-scope", "executor-replacement-fencing"} <= tags)
        self.assertTrue(all(case["status"]=="NOT_RUN" for case in doc["cases"]))

if __name__ == "__main__":
    unittest.main(verbosity=2)
