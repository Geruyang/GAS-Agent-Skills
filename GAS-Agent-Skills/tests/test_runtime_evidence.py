"""Real file/CLI regression tests; these do not evaluate governance performance."""
from __future__ import annotations

import copy
from contextlib import contextmanager
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MODES = ("centralized", "decentralized", "combined")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def valid_record(folder, digest):
    """Known completed local observation, without any governance acceptance."""
    (folder / "observed.txt").write_bytes(b"observed\n")
    binding = {"run_id": "run-1", "task_id": "task-1", "command_or_claim_id": "command-1",
               "recipient": "worker-1", "epoch": 1, "contract_version": "v1",
               "candidate_digest": digest, "idempotency_key": "run-1/task-1/attempt-1"}
    return {"schema_version": 1, "example_only": False, "binding": binding,
            "checks": [{"id": "required-check", "required": True, "execution": "COMPLETED",
                        "result": "PASS", "input_digest": digest, "evidence_refs": ["observation"]}],
            "evidence": [{"id": "observation", "path": "observed.txt", "sha256": sha(b"observed\n"),
                          "input_digest": digest}],
            "critical_capability_preflight": [], "lifecycle": {},
            "preflight_applicability": {"status": "NOT_APPLICABLE", "reason": "local bookkeeping fixture",
                                        "contract_ref": "fixture-contract"},
            "checkpoint": {"side_effect_status": "NONE", "retry_requested": False,
                           "reconciliation_execution": "NOT_RUN", "reconciliation_evidence_refs": []},
            "risk_acceptance": {"status": "NOT_DECIDED", "record_ref": None},
            "human_adjudication": {"status": "NOT_DECIDED", "record_ref": None},
            "delivery": {"execution": "NOT_RUN", "result": "UNKNOWN", "evidence_refs": []}}


class RuntimeEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="gas-runtime-")
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.candidate = self.folder / "candidate"
        self.candidate.mkdir()
        (self.candidate / "a.txt").write_bytes(b"abc")
        (self.candidate / "empty").mkdir()
        self.manifest = self.folder / "manifest.json"
        self.record_path = self.folder / "runtime.json"
        self.script = ROOT / "gas-centralized-development/scripts/gas_runtime.py"

    def cli(self, *arguments, code=0):
        result = subprocess.run([sys.executable, str(self.script), *map(str, arguments)],
                                capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(result.returncode, code, result.stdout + result.stderr)
        self.assertTrue(result.stdout.strip(), "CLI must emit a JSON outcome")
        return json.loads(result.stdout)

    def freeze(self):
        self.cli("manifest", "--candidate", self.candidate, "--output", self.manifest)
        return json.loads(self.manifest.read_text(encoding="utf-8"))

    def assess(self, record, code=0):
        write_json(self.record_path, record)
        return self.cli("assess", "--candidate", self.candidate, "--manifest", self.manifest,
                        "--record", self.record_path, code=code)

    @contextmanager
    def symlink_fixture(self, link, target):
        try:
            try:
                link.symlink_to(target)
                info = link.lstat()
            except (OSError, NotImplementedError) as exc:
                self.skipTest("Host cannot create symlinks: " + str(exc))
            if not (stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400):
                self.skipTest("symlink_to() did not create a symlink/reparse point on this host")
            yield
        finally:
            link.unlink(missing_ok=True)

    def test_manifest_is_deterministic_and_root_independent(self):
        first = self.freeze()
        self.assertEqual(first["files"], [{"path": "a.txt", "size": 3,
                         "sha256": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"}])
        self.assertEqual(first["directories"], ["empty"])
        old = self.manifest.read_bytes()
        self.freeze()
        self.assertEqual(self.manifest.read_bytes(), old)
        other = self.folder / "same-content"
        other.mkdir()
        (other / "empty").mkdir()
        (other / "a.txt").write_bytes(b"abc")
        second = self.folder / "second.json"
        self.cli("manifest", "--candidate", other, "--output", second)
        self.assertEqual(json.loads(second.read_text())["candidate_digest"], first["candidate_digest"])

    def test_manifest_output_inside_candidate_is_rejected(self):
        self.cli("manifest", "--candidate", self.candidate, "--output", self.candidate / "m.json", code=2)
        self.assertFalse((self.candidate / "m.json").exists())

    def test_existing_different_manifest_is_not_overwritten(self):
        self.manifest.write_bytes(b"keep me")
        self.cli("manifest", "--candidate", self.candidate, "--output", self.manifest, code=2)
        self.assertEqual(self.manifest.read_bytes(), b"keep me")

    def test_verify_reports_changed_missing_added_and_empty_directories(self):
        self.freeze()
        self.cli("verify", "--candidate", self.candidate, "--manifest", self.manifest)
        (self.candidate / "a.txt").write_bytes(b"xyz")
        changed = self.cli("verify", "--candidate", self.candidate, "--manifest", self.manifest, code=1)
        self.assertEqual(changed["changed"], ["a.txt"])
        (self.candidate / "a.txt").unlink()
        (self.candidate / "new.txt").write_bytes(b"new")
        (self.candidate / "new-directory").mkdir()
        (self.candidate / "empty").rmdir()
        mismatch = self.cli("verify", "--candidate", self.candidate, "--manifest", self.manifest, code=1)
        self.assertEqual(mismatch["missing"], ["a.txt"])
        self.assertEqual(mismatch["added"], ["new.txt"])
        self.assertEqual(mismatch["directories_added"], ["new-directory"])
        self.assertEqual(mismatch["directories_missing"], ["empty"])

    def test_manifest_tamper_duplicate_escape_and_extra_root_are_rejected(self):
        base = self.freeze()
        variants = []
        item = copy.deepcopy(base); item["files"][0]["sha256"] = "0" * 64; variants.append(item)
        item = copy.deepcopy(base); item["files"].append(item["files"][0]); variants.append(item)
        for path in ("../outside.txt", "/outside.txt", "C:/outside.txt", "x/../a.txt", "x\\a.txt"):
            item = copy.deepcopy(base); item["files"][0]["path"] = path; variants.append(item)
        item = copy.deepcopy(base); item["candidate_root"] = str(self.folder); variants.append(item)
        for item in variants:
            with self.subTest(item=item):
                write_json(self.manifest, item)
                self.cli("verify", "--candidate", self.candidate, "--manifest", self.manifest, code=2)

    def test_self_consistent_manifest_cannot_authorize_unsafe_paths_or_types(self):
        base = self.freeze()
        variants = []
        for path in ("../outside.txt", "A.txt/child", "a.txt.", "a.txt ", "a.txt:stream", "CON", "nul.txt"):
            item = copy.deepcopy(base); item["files"][0]["path"] = path; variants.append(item)
        item = copy.deepcopy(base); item["files"][0]["size"] = True; variants.append(item)
        item = copy.deepcopy(base); item["directories"] = ["empty", "empty"]; variants.append(item)
        item = copy.deepcopy(base); item["directories"] = ["a.txt", "empty"]; variants.append(item)
        item = copy.deepcopy(base); item["files"].append(dict(item["files"][0], path="A.txt"))
        item["files"].sort(key=lambda value: value["path"]); variants.append(item)
        for item in variants:
            payload = {key: value for key, value in item.items() if key != "candidate_digest"}
            item["candidate_digest"] = sha(json.dumps(payload, sort_keys=True, separators=(",", ":"),
                                                      ensure_ascii=False).encode("utf-8"))
            with self.subTest(item=item):
                write_json(self.manifest, item)
                self.cli("verify", "--candidate", self.candidate, "--manifest", self.manifest, code=2)

    def test_windows_junction_is_rejected_without_reading_target(self):
        if os.name != "nt":
            self.skipTest("Windows junction test")
        target = self.folder / "outside-directory"
        target.mkdir(); (target / "private.txt").write_bytes(b"private")
        junction = self.candidate / "junction"
        command = ("New-Item -ItemType Junction -Path '" + str(junction).replace("'", "''") +
                   "' -Target '" + str(target).replace("'", "''") + "' | Out-Null")
        created = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", command],
                                 capture_output=True, text=True)
        try:
            if created.returncode != 0:
                self.skipTest("Host cannot create junction: " + created.stderr)
            try:
                info = junction.lstat()
            except OSError as exc:
                self.skipTest("Host did not create a junction: " + str(exc))
            if not getattr(info, "st_file_attributes", 0) & 0x400:
                self.skipTest("Junction creation did not create a reparse point on this host")
            self.cli("manifest", "--candidate", self.candidate, "--output", self.manifest, code=2)
        finally:
            try:
                info = junction.lstat()
            except FileNotFoundError:
                pass
            else:
                # Non-recursive cleanup removes this link or empty stub, never target contents.
                if stat.S_ISDIR(info.st_mode):
                    os.rmdir(junction)
                else:
                    junction.unlink()
        self.assertEqual((target / "private.txt").read_bytes(), b"private")

    def test_junction_fixture_skips_and_cleans_up_plain_directory_stub(self):
        if os.name != "nt":
            self.skipTest("Windows junction test")
        junction = self.candidate / "junction"
        junction.mkdir()
        created = subprocess.CompletedProcess([], 0, stdout="", stderr="")
        with mock.patch.object(subprocess, "run", return_value=created):
            with self.assertRaises(unittest.SkipTest):
                self.test_windows_junction_is_rejected_without_reading_target()
        self.assertFalse(junction.exists())
        self.assertEqual((self.folder / "outside-directory/private.txt").read_bytes(), b"private")

    def test_duplicate_json_keys_are_rejected(self):
        self.freeze()
        self.manifest.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        self.cli("verify", "--candidate", self.candidate, "--manifest", self.manifest, code=2)

    def test_candidate_and_manifest_symlinks_are_rejected(self):
        outside = self.folder / "outside.txt"
        outside.write_bytes(b"private")
        link = self.candidate / "linked.txt"
        with self.symlink_fixture(link, outside):
            self.cli("manifest", "--candidate", self.candidate, "--output", self.manifest, code=2)
        self.freeze()
        alias = self.folder / "alias.json"
        with self.symlink_fixture(alias, self.manifest):
            self.cli("verify", "--candidate", self.candidate, "--manifest", alias, code=2)

    def test_symlink_fixture_skips_and_cleans_up_plain_file_stub(self):
        def create_plain_file(path, target):
            path.write_bytes(b"")

        with mock.patch.object(Path, "symlink_to", create_plain_file):
            with self.assertRaises(unittest.SkipTest):
                self.test_candidate_and_manifest_symlinks_are_rejected()
        self.assertFalse((self.candidate / "linked.txt").exists())

    def test_stable_invalid_evidence_is_not_reported_as_changed(self):
        digest = self.freeze()["candidate_digest"]
        for content in (b"observed\n", b""):
            with self.subTest(content=content):
                record = valid_record(self.folder, digest)
                record["evidence"][0]["sha256"] = "0" * 64
                (self.folder / "observed.txt").write_bytes(content)
                outcome = self.assess(record, code=1)
                self.assertTrue(any(issue.startswith("invalid evidence:") for issue in outcome["issues"]))
                self.assertFalse(any("changed during assessment" in issue for issue in outcome["issues"]))

    def test_invalid_evidence_readback_still_detects_real_drift(self):
        digest = self.freeze()["candidate_digest"]
        spec = importlib.util.spec_from_file_location("gas_runtime_invalid_drift_test", self.script)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        original = module.read_regular
        for content in (b"observed\n", b""):
            with self.subTest(content=content):
                record = valid_record(self.folder, digest)
                record["evidence"][0]["sha256"] = "0" * 64
                evidence_path = self.folder / "observed.txt"
                evidence_path.write_bytes(content)
                write_json(self.record_path, record)
                injected = []

                def read_then_inject(path):
                    data = original(path)
                    if Path(path) == evidence_path and not injected:
                        injected.append(True)
                        evidence_path.write_bytes(b"changed after first observation")
                    return data

                with mock.patch.object(module, "read_regular", read_then_inject):
                    outcome = module.assess(self.candidate, self.manifest, self.record_path)
                self.assertFalse(outcome["technical_evidence_ready"])
                self.assertIn("evidence changed during assessment: observation", outcome["issues"])

    def test_ready_is_only_technical_and_preserves_other_decisions(self):
        digest = self.freeze()["candidate_digest"]
        record = valid_record(self.folder, digest)
        result = self.assess(record)
        self.assertTrue(result["technical_evidence_ready"])
        for field in ("risk_acceptance", "human_adjudication", "delivery"):
            self.assertEqual(result[field], record[field])
        self.assertNotIn("authorized", result)
        self.assertNotIn("release_ready", result)

    def test_empty_checks_and_no_required_checks_cannot_be_ready(self):
        digest = self.freeze()["candidate_digest"]
        for checks in ([], [{"id": "optional", "required": False, "execution": "NOT_RUN",
                             "result": "UNKNOWN", "input_digest": digest, "evidence_refs": []}]):
            record = valid_record(self.folder, digest); record["checks"] = checks
            self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])

    def test_not_run_pass_and_risk_acceptance_do_not_launder_failure(self):
        digest = self.freeze()["candidate_digest"]
        for execution, outcome in (("NOT_RUN", "PASS"), ("RUNNING", "PASS"), ("COMPLETED", "FAIL"),
                                    ("COMPLETED", "INCONCLUSIVE"), ("NOT_RUN", "UNKNOWN")):
            record = valid_record(self.folder, digest)
            record["checks"][0].update(execution=execution, result=outcome)
            record["risk_acceptance"] = {"status": "ACCEPTED", "record_ref": "human-risk-decision"}
            record["human_adjudication"] = {"status": "ACCEPTED", "record_ref": "decision-1"}
            result = self.assess(record, code=1)
            self.assertFalse(result["technical_evidence_ready"])
            self.assertEqual(result["risk_acceptance"]["status"], "ACCEPTED")
            self.assertEqual(result["checks"][0]["result"], outcome)

    def test_candidate_and_evidence_digest_must_match_and_evidence_must_exist(self):
        digest = self.freeze()["candidate_digest"]
        for change in ("candidate", "check", "evidence", "missing", "changed", "escape", "empty"):
            with self.subTest(change=change):
                record = valid_record(self.folder, digest)
                if change == "candidate": record["binding"]["candidate_digest"] = "0" * 64
                if change == "check": record["checks"][0]["input_digest"] = "0" * 64
                if change == "evidence": record["evidence"][0]["input_digest"] = "0" * 64
                if change == "missing": (self.folder / "observed.txt").unlink()
                if change == "changed": (self.folder / "observed.txt").write_bytes(b"altered")
                if change == "escape": record["evidence"][0]["path"] = "../observed.txt"
                if change == "empty": record["checks"][0]["evidence_refs"] = []
                self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])

    def test_changed_candidate_invalidates_otherwise_passing_assessment(self):
        digest = self.freeze()["candidate_digest"]
        record = valid_record(self.folder, digest)
        (self.candidate / "a.txt").write_bytes(b"updated during review")
        self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])

    def test_critical_preflight_checks_actual_output_against_expected(self):
        digest = self.freeze()["candidate_digest"]
        record = valid_record(self.folder, digest)
        check = copy.deepcopy(record["checks"][0])
        check.update(id="render-preflight", expected_output="observed\n", actual_output_ref="observation")
        record["critical_capability_preflight"] = [check]
        self.assertTrue(self.assess(record)["technical_evidence_ready"])
        check["expected_output"] = "something else\n"
        self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])
        check["expected_output"] = "observed\n"; check["actual_output_ref"] = None
        self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])

    def test_empty_preflight_requires_explicit_not_applicable_basis(self):
        digest = self.freeze()["candidate_digest"]
        record = valid_record(self.folder, digest)
        del record["preflight_applicability"]
        self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])
        record["preflight_applicability"] = {"status": "NOT_APPLICABLE", "reason": None, "contract_ref": None}
        self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])

    def test_dependency_graph_accepts_order_and_rejects_ambiguous_or_cyclic_graphs(self):
        digest = self.freeze()["candidate_digest"]
        record = valid_record(self.folder, digest)
        graph = {"nodes": ["prepare", "review", "adjudicate"],
                 "edges": [{"from": "prepare", "to": "review"}, {"from": "review", "to": "adjudicate"}]}
        record["stage_dependencies"] = graph
        self.assertTrue(self.assess(record)["technical_evidence_ready"])
        for fault in ("cycle", "self", "unknown", "duplicate"):
            broken = copy.deepcopy(record)
            edges = broken["stage_dependencies"]["edges"]
            if fault == "cycle": edges.append({"from": "adjudicate", "to": "prepare"})
            if fault == "self": edges.append({"from": "review", "to": "review"})
            if fault == "unknown": edges.append({"from": "missing", "to": "review"})
            if fault == "duplicate": broken["stage_dependencies"]["nodes"].append("review")
            self.assertFalse(self.assess(broken, code=1)["technical_evidence_ready"])

    def test_delivery_claims_cannot_promote_unexecuted_results(self):
        digest = self.freeze()["candidate_digest"]
        record = valid_record(self.folder, digest)
        record["delivery"].update(execution="NOT_RUN", result="PASS")
        outcome = self.assess(record, code=1)
        self.assertFalse(outcome["technical_evidence_ready"])
        self.assertEqual(outcome["delivery"]["execution"], "NOT_RUN")

    def test_lifecycle_requires_order_host_receipts_and_exact_binding(self):
        digest = self.freeze()["candidate_digest"]
        record = valid_record(self.folder, digest)
        event = {"execution": "COMPLETED", "binding": record["binding"], "host_receipt_ref": "observation"}
        record["lifecycle"] = {stage: copy.deepcopy(event) for stage in ("sent", "received", "started", "completed")}
        self.assertTrue(self.assess(record)["technical_evidence_ready"])
        for change in ("order", "receipt", "binding"):
            changed = copy.deepcopy(record)
            if change == "order": changed["lifecycle"]["received"]["execution"] = "NOT_RUN"
            if change == "receipt": changed["lifecycle"]["started"]["host_receipt_ref"] = None
            if change == "binding": changed["lifecycle"]["completed"]["binding"]["epoch"] = 2
            self.assertFalse(self.assess(changed, code=1)["technical_evidence_ready"])

    def test_unknown_side_effect_cannot_retry_before_reconciliation(self):
        digest = self.freeze()["candidate_digest"]
        record = valid_record(self.folder, digest)
        checkpoint = record["checkpoint"]
        checkpoint.update(side_effect_status="UNKNOWN", retry_requested=True)
        self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])
        checkpoint.update(reconciliation_execution="COMPLETED", reconciliation_evidence_refs=["observation"])
        self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])
        checkpoint.update(side_effect_status="CONFIRMED_NOT_APPLIED")
        self.assertTrue(self.assess(record)["technical_evidence_ready"])
        checkpoint.update(side_effect_status="CONFIRMED_APPLIED")
        self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])

    def test_retry_flag_requires_boolean_and_receipt_binding_preserves_types(self):
        digest = self.freeze()["candidate_digest"]
        for flag in (1, "true", None):
            record = valid_record(self.folder, digest)
            record["checkpoint"].update(side_effect_status="UNKNOWN", retry_requested=flag)
            self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])
        for epoch in (True, 1.0):
            record = valid_record(self.folder, digest)
            event = {"execution": "COMPLETED", "binding": dict(record["binding"]), "host_receipt_ref": "observation"}
            event["binding"]["epoch"] = epoch
            record["lifecycle"] = {"sent": event}
            self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])

    def test_windows_extended_path_alias_cannot_put_manifest_inside_candidate(self):
        if os.name != "nt":
            self.skipTest("Windows extended paths")
        output = self.candidate / "internal.json"
        extended_candidate = "\\\\?\\" + str(self.candidate)
        extended_output = "\\\\?\\" + str(output)
        self.cli("manifest", "--candidate", self.candidate, "--output", extended_output, code=2)
        self.cli("manifest", "--candidate", extended_candidate, "--output", output, code=2)
        self.assertFalse(output.exists())

    def test_source_preflight_reuse_preserves_digest_and_requires_current_applicability(self):
        digest = self.freeze()["candidate_digest"]
        source_digest = "1" * 64
        record = valid_record(self.folder, digest)
        binary = b"\x89PNG\x00\xff\x80probe"
        (self.folder / "probe.bin").write_bytes(binary)
        record["evidence"].append({"id": "historical-probe", "path": "probe.bin", "sha256": sha(binary),
                                   "input_digest": source_digest})
        check = {"id": "binary-preflight", "required": True, "execution": "COMPLETED", "result": "PASS",
                 "input_digest": source_digest, "evidence_refs": ["historical-probe"],
                 "actual_output_ref": "historical-probe", "output_assertion": {"kind": "sha256", "expected": sha(binary)},
                 "applicability": {"source_input_digest": source_digest, "target_candidate_digest": digest,
                                   "environment": "same local fixture", "coverage": "binary probe only",
                                   "reviewer": "fixture-reviewer", "reason": "identical relevant input format",
                                   "evidence_refs": ["observation"]}}
        record["critical_capability_preflight"] = [check]
        self.assertTrue(self.assess(record)["technical_evidence_ready"])
        self.assertEqual(record["evidence"][1]["input_digest"], source_digest)
        for fault in ("no-applicability", "wrong-target", "source-for-review", "wrong-binary"):
            broken = copy.deepcopy(record)
            probe = broken["critical_capability_preflight"][0]
            if fault == "no-applicability": del probe["applicability"]
            if fault == "wrong-target": probe["applicability"]["target_candidate_digest"] = source_digest
            if fault == "source-for-review": probe["applicability"]["evidence_refs"] = ["historical-probe"]
            if fault == "wrong-binary": probe["output_assertion"]["expected"] = "0" * 64
            self.assertFalse(self.assess(broken, code=1)["technical_evidence_ready"])

    def test_execution_readback_detects_candidate_evidence_and_record_drift(self):
        digest = self.freeze()["candidate_digest"]
        spec = importlib.util.spec_from_file_location("gas_runtime_test", self.script)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        for fault in ("candidate", "evidence", "record"):
            (self.candidate / "a.txt").write_bytes(b"abc")
            record = valid_record(self.folder, digest)
            write_json(self.record_path, record)
            original = module.read_regular
            injected = []
            def read_then_inject(path):
                data = original(path)
                if Path(path).name == "observed.txt" and not injected:
                    injected.append(True)
                    if fault == "candidate": (self.candidate / "a.txt").write_bytes(b"def")
                    if fault == "evidence": (self.folder / "observed.txt").write_bytes(b"altered")
                    if fault == "record": self.record_path.write_text('{}', encoding="utf-8")
                return data
            module.read_regular = read_then_inject
            try:
                outcome = module.assess(self.candidate, self.manifest, self.record_path)
                self.assertTrue(injected)
                self.assertFalse(outcome["technical_evidence_ready"], fault)
            finally:
                module.read_regular = original

    def test_snapshot_readback_detects_earlier_file_changed_during_later_read(self):
        (self.candidate / "b.txt").write_bytes(b"second")
        self.freeze()
        spec = importlib.util.spec_from_file_location("gas_runtime_scan_test", self.script)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        original = module.read_regular
        injected = []
        def read_then_inject(path):
            data = original(path)
            if Path(path).name == "b.txt" and not injected:
                injected.append(True)
                (self.candidate / "a.txt").write_bytes(b"def")
            return data
        module.read_regular = read_then_inject
        try:
            try:
                outcome = module.verify_candidate(self.candidate, self.manifest)
            except ValueError:
                outcome = {"ok": False}
            self.assertFalse(outcome["ok"])
        finally:
            module.read_regular = original

    def test_verify_reads_manifest_back_after_candidate_scan(self):
        self.freeze()
        spec = importlib.util.spec_from_file_location("gas_runtime_manifest_drift_test", self.script)
        module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
        original = module.read_regular
        injected = []
        def read_then_inject(path):
            data = original(path)
            if Path(path).name == "a.txt" and not injected:
                injected.append(True)
                self.manifest.write_text('{}', encoding="utf-8")
            return data
        module.read_regular = read_then_inject
        try:
            try:
                outcome = module.verify_candidate(self.candidate, self.manifest)
            except ValueError:
                outcome = {"ok": False}
            self.assertFalse(outcome["ok"])
        finally:
            module.read_regular = original

    def test_shipped_examples_never_claim_execution(self):
        self.freeze()
        for mode in MODES:
            path = ROOT / ("gas-" + mode + "-development/templates/runtime.example.json")
            self.assertTrue(path.is_file(), str(path))
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue(record["example_only"])
            self.assertFalse(self.assess(record, code=1)["technical_evidence_ready"])

    def test_copies_are_byte_identical_and_each_runs_standalone(self):
        digest = self.freeze()["candidate_digest"]
        baseline = self.script.read_bytes()
        for mode in MODES:
            source = ROOT / ("gas-" + mode + "-development/scripts/gas_runtime.py")
            self.assertEqual(source.read_bytes(), baseline)
            isolated = self.folder / (mode + "-runtime.py")
            isolated.write_bytes(source.read_bytes())
            self.script = isolated
            result = self.cli("verify", "--candidate", self.candidate, "--manifest", self.manifest)
            self.assertEqual(result["candidate_digest"], digest)


if __name__ == "__main__":
    unittest.main()
