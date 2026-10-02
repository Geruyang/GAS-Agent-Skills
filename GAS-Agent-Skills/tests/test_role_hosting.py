"""Reject unsafe example declarations; these tests do not authenticate live agents."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify_bundle import validate

CONTRACTS = {
    "gas-centralized-development": (4, ["coordinator", "executor", "reviewer", "supervisor"]),
    "gas-decentralized-development": (3, ["legislator", "executor", "arbiter"]),
    "gas-combined-development": (6, ["outer.legislator", "outer.executor", "outer.arbiter",
                                     "inner.coordinator", "inner.executor", "inner.reviewer", "inner.supervisor"]),
}


class RoleHostingPackageTests(unittest.TestCase):
    names = tuple(CONTRACTS)

    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="gas-role-hosting-")
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.records = {}
        for name in self.names:
            shutil.copytree(ROOT / name, self.root / name,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
            path = self.root / name / "templates/run.example.json"
            record = json.loads(path.read_text(encoding="utf-8-sig"))
            minimum, roles = CONTRACTS[name]
            record["main_session"] = {"purpose": "progress_display", "identity": None,
                "governance_role": None, "counts_as_role": False, "business_execution_allowed": False}
            record["role_hosting"] = {"all_roles_must_be_subagents": True,
                "required_distinct_subagents_minimum": minimum, "required_roles": roles,
                "roster": [], "verified": False}
            if name == "gas-decentralized-development":
                record["governance"]["main_session_role"] = None
            if name == "gas-combined-development":
                record["runtime"]["main_session_role"] = None
            self.records[name] = record
            self.write(name, record)

    def write(self, name, record):
        path = self.root / name / "templates/run.example.json"
        path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def report(self, name):
        return validate(self.root, [name])

    def rejected(self, name, change, suffix):
        record = copy.deepcopy(self.records[name])
        change(record)
        self.write(name, record)
        try:
            report = self.report(name)
            failures = [item["check"] for item in report["checks"] if not item["passed"]]
            self.assertFalse(report["passed"], "unsafe example unexpectedly accepted: " + name)
            self.assertTrue(any(not item["passed"] and item["check"].endswith(suffix)
                                for item in report["checks"]), {"expected_check": suffix, "failures": failures})
        finally:
            self.write(name, self.records[name])

    def test_progress_only_main_and_unverified_subagents_are_valid(self):
        for name in self.names:
            with self.subTest(name=name):
                result = self.report(name)
                self.assertTrue(result["passed"], [item for item in result["checks"] if not item["passed"]])

    def test_main_session_cannot_take_role_identity_or_execute_business(self):
        changes = (("purpose", "coordinator"), ("identity", "root-agent"), ("governance_role", "executor"),
                   ("counts_as_role", True), ("business_execution_allowed", True),
                   ("counts_as_role", 0), ("business_execution_allowed", 0))
        for name in self.names:
            for field, value in changes:
                with self.subTest(name=name, field=field, value=value):
                    self.rejected(name, lambda r, k=field, v=value: r["main_session"].update({k: v}),
                                  ":main-session:display-only")

    def test_missing_or_malformed_main_session_fails_without_crashing(self):
        for name in self.names:
            self.rejected(name, lambda r: r.pop("main_session"), ":main-session:display-only")
            for field in self.records[name]["main_session"]:
                with self.subTest(name=name, missing_field=field):
                    self.rejected(name, lambda r, k=field: r["main_session"].pop(k), ":main-session:display-only")
            for value in (None, [], True, "progress_display", 1):
                with self.subTest(name=name, value=value):
                    self.rejected(name, lambda r, v=value: r.update(main_session=v), ":main-session:display-only")

    def test_no_non_subagent_hosting_or_bool_coercion(self):
        for name in self.names:
            for value in (False, None, 1, "true"):
                with self.subTest(name=name, value=value):
                    self.rejected(name, lambda r, v=value: r["role_hosting"].update(all_roles_must_be_subagents=v),
                                  ":role-hosting:subagents-only")

    def test_distinct_subagent_minimum_cannot_be_reduced_or_coerced(self):
        for name in self.names:
            minimum = CONTRACTS[name][0]
            for value in (minimum - 1, True, float(minimum), str(minimum), None):
                with self.subTest(name=name, value=value):
                    self.rejected(name, lambda r, v=value: r["role_hosting"].update(required_distinct_subagents_minimum=v),
                                  ":role-hosting:minimum-subagents")

    def test_required_governance_seats_cannot_be_missing_duplicated_or_root(self):
        for name in self.names:
            roles = CONTRACTS[name][1]
            for value in (roles[:-1], roles + [roles[0]], roles + ["main_session"],
                          roles[:-1] + [roles[0]], roles[:-1] + ["main_session"], True, [None]):
                with self.subTest(name=name, value=value):
                    self.rejected(name, lambda r, v=value: r["role_hosting"].update(required_roles=v),
                                  ":role-hosting:required-roles")

    def test_example_cannot_claim_verified_role_hosts(self):
        for name in self.names:
            for value in (True, 0, None, "false"):
                with self.subTest(name=name, value=value):
                    self.rejected(name, lambda r, v=value: r["role_hosting"].update(verified=v),
                                  ":role-hosting:unverified-example")

    def test_example_cannot_invent_roster_even_if_unverified(self):
        for name in self.names:
            for value in ([{"role": CONTRACTS[name][1][0], "agent_id": "fabricated-subagent"}],
                          {"root": "coordinator"}, None, "", False):
                with self.subTest(name=name, value=value):
                    self.rejected(name, lambda r, v=value: r["role_hosting"].update(roster=v),
                                  ":role-hosting:empty-roster")

    def test_missing_and_malformed_hosting_fails_without_crashing(self):
        for name in self.names:
            self.rejected(name, lambda r: r.pop("role_hosting"), ":role-hosting:subagents-only")
            for value in (None, [], True, "subagents", 4):
                with self.subTest(name=name, value=value):
                    self.rejected(name, lambda r, v=value: r.update(role_hosting=v), ":role-hosting:subagents-only")

    def test_legacy_main_session_role_must_be_explicitly_null(self):
        for name in self.names:
            parent = {"gas-decentralized-development": "governance", "gas-combined-development": "runtime"}.get(name)
            if parent is None:
                continue
            for value in ("legislator", "executor", "arbiter", "outer.legislator", False, []):
                with self.subTest(name=name, value=value):
                    self.rejected(name, lambda r, p=parent, v=value: r[p].update(main_session_role=v),
                                  ":main-session:no-legacy-role")
            self.rejected(name, lambda r, p=parent: r[p].pop("main_session_role"), ":main-session:no-legacy-role")


class RoleHostingStandaloneTests(RoleHostingPackageTests):
    names = ("gas-centralized-development",)
    # The centralized schema has no legacy main_session_role field.
    test_legacy_main_session_role_must_be_explicitly_null = None

    def report(self, name):
        path = ROOT / name / "scripts/validate_skill.py"
        spec = importlib.util.spec_from_file_location("gas_role_hosting_standalone", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        report = module.validate(self.root / name)
        return {"passed": report["ok"], "checks": [
            {"check": item["name"], "passed": item["ok"], "detail": item["detail"]}
            for item in report["checks"]]}


if __name__ == "__main__":
    unittest.main()
