"""Data-contract acceptance and negative cases for commander v3, not model behavior."""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CommanderContract(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name) / "skill"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("__pycache__"))

    def doc(self, name):
        return json.loads((self.root / name).read_text(encoding="utf-8"))

    def edit(self, name, change):
        path = self.root / name
        obj = self.doc(name)
        change(obj)
        path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")

    def validate(self):
        spec = importlib.util.spec_from_file_location("v3_checker", ROOT / "scripts/validate_skill.py")
        checker = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(checker)
        return checker.validate(self.root)

    def rejected(self, fragment):
        result = self.validate()
        failures = [c["name"] for c in result["checks"] if not c["ok"]]
        self.assertFalse(result["ok"])
        self.assertTrue(any(fragment in c for c in failures), failures)

    def test_three_subordinate_roles_and_commander_delivery(self):
        run = self.doc("templates/run.example.json")
        self.assertEqual(run["schema_version"], 3)
        self.assertEqual(set(run["command_scope"]["roles"]), {"executor", "reviewer", "supervisor"})
        self.assertEqual(run["delivery_responsibility"], {"owner_role": "coordinator", "separate_integrator_required": False})

    def test_supervisor_covers_subordinates_and_human_covers_commander(self):
        config = self.doc("templates/run.example.json")["supervision"]
        self.assertEqual(set(config["target_roles"]), {"executor", "reviewer"})
        self.assertEqual(config["reports_to"], "coordinator")
        self.assertEqual(config["commander_supervised_by"], "human-only")
        self.assertEqual(set(config["coverage_requirements"]), {"rule_compliance", "unsafe_actions", "instruction_alignment"})

    def test_supervision_record_is_unrun_and_bound(self):
        report = self.doc("templates/supervision.example.json")
        self.assertEqual(report["schema_version"], 3)
        self.assertEqual(report["record_type"], "supervision")
        self.assertEqual(report["status"], "NOT_RUN")
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["task_id"], self.doc("templates/task.example.json")["id"])

    def test_missing_supervision_template_rejected(self):
        path = self.root / "templates/supervision.example.json"
        if path.exists():
            path.unlink()
        self.rejected("supervision:json")

    def test_supervising_commander_rejected(self):
        self.edit("templates/run.example.json", lambda d: d["supervision"]["target_roles"].append("coordinator"))
        self.rejected("supervision:target-roles")

    def test_supervisor_reporting_to_peer_rejected(self):
        self.edit("templates/run.example.json", lambda d: d["supervision"].update(reports_to="reviewer"))
        self.rejected("supervision:reports-to")

    def test_nonhuman_commander_oversight_rejected(self):
        self.edit("templates/run.example.json", lambda d: d["supervision"].update(commander_supervised_by="supervisor"))
        self.rejected("supervision:human-oversight")

    def test_ungranted_pause_authority_rejected(self):
        self.edit("templates/run.example.json", lambda d: d["supervision"]["pause_authority"].update(granted=True))
        self.rejected("supervision:pause-ungranted")

    def test_supervisor_self_release_permission_rejected(self):
        self.edit("templates/run.example.json", lambda d: d["supervision"].update(can_release=True))
        self.rejected("supervision:limited-authority")

    def test_reintroduced_integrator_rejected(self):
        self.edit("templates/run.example.json", lambda d: d["delivery_responsibility"].update(owner_role="integrator"))
        self.rejected("delivery:commander-owner")

    def test_noncommander_delivery_recipient_rejected(self):
        self.edit("templates/release.example.json", lambda d: d["command"].update(recipient_role="supervisor"))
        self.rejected("delivery:commander-recipient")

    def test_noncommander_delivery_execution_rejected(self):
        self.edit("templates/release.example.json", lambda d: d["execution"].update(executor_role="integrator"))
        self.rejected("delivery:commander-executor")

    def test_fake_supervision_satisfaction_rejected(self):
        self.edit("templates/decision.example.json", lambda d: d["acceptance_preconditions"].update(supervision_satisfied=True))
        self.rejected("decision:supervision-default")

    def test_invalid_supervision_config_rejected_without_crash(self):
        self.edit("templates/run.example.json", lambda d: d.update(supervision=None))
        self.rejected("supervision")

    def test_empty_scenario_id_rejected(self):
        self.edit("evals/scenarios.json", lambda d: d["cases"][0].update(id=""))
        self.rejected("scenarios:valid-ids")

    def test_null_scenario_rules_rejected_without_crash(self):
        self.edit("evals/scenarios.json", lambda d: d["cases"][0].update(rules=None))
        self.rejected("scenarios")

    def test_malformed_markdown_is_reported_without_crash(self):
        (self.root / "README.zh-CN.md").write_bytes(b"\xff\xfe\xff")
        self.rejected("file:")

    def test_nested_contract_objects_reject_scalars(self):
        objects = {
            "command": ("scope", "budget"), "release": ("target",),
            "run": ("dispatch",), "task": ("budget", "test_plan", "dispatch", "integration", "release"),
        }
        for name, fields in objects.items():
            path = self.root / f"templates/{name}.example.json"
            original = path.read_bytes()
            for field in fields:
                for invalid in (None, [], True, "broken", 0):
                    with self.subTest(name=name, field=field, invalid=invalid):
                        path.write_bytes(original)
                        self.edit(path.relative_to(self.root), lambda d: d.update({field: invalid}))
                        self.rejected("object")
            path.write_bytes(original)

    def test_fabricated_completion_defaults_rejected(self):
        fields = [
            ("release", ["preconditions", "independent_review_satisfied"]),
            ("release", ["preconditions", "platform_approvals_satisfied"]),
            ("review", ["required_checks_passed"]),
            ("task", ["verification", "independent_review_satisfied"]),
            ("decision", ["acceptance_preconditions", "platform_approvals_satisfied"]),
            ("run", ["runtime", "budget_enforcement_verified"]),
            ("run", ["runtime", "isolated_workspaces_verified"]),
        ]
        for name, keys in fields:
            path = self.root / f"templates/{name}.example.json"
            original = path.read_bytes()
            with self.subTest(name=name, keys=keys):
                record = json.loads(original)
                parent = record if len(keys) == 1 else record[keys[0]]
                parent[keys[-1]] = True
                path.write_text(json.dumps(record), encoding="utf-8")
                self.assertFalse(self.validate()["ok"])
            path.write_bytes(original)

    def test_deploy_requires_target_verification_scope(self):
        self.edit("templates/release.example.json", lambda d: d["preconditions"].update(verification_scope="accepted-source-tasks"))
        self.rejected("delivery:verification-scope")


if __name__ == "__main__":
    unittest.main()
