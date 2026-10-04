#!/usr/bin/env python3
"""Run reproducible local file faults, not a comparison of agent governance teams."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
MODES = ("centralized", "decentralized", "combined")
CASES = (
    ("normal", 0), ("changed_during_review", 1), ("missing_file", 1), ("added_file", 1),
    ("empty_checks", 1), ("not_run_claims_pass", 1), ("risk_accepts_failed_check", 1),
    ("unknown_side_effect_retry", 1), ("confirmed_absent_retry", 0), ("already_applied_retry", 1),
    ("preflight_wrong_output", 1), ("preflight_missing_output", 1), ("receipt_wrong_epoch", 1),
    ("receipt_missing_started", 1), ("dependency_order", 0), ("dependency_cycle", 1),
    ("historical_binary_preflight", 0), ("historical_preflight_wrong_target", 1),
)


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def hash_bytes(value):
    return hashlib.sha256(value).hexdigest()


def call(script, arguments, destination):
    started = time.perf_counter()
    command = [sys.executable, str(script), *map(str, arguments)]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    duration = time.perf_counter() - started
    destination.with_suffix(".stdout.json").write_text(result.stdout, encoding="utf-8")
    destination.with_suffix(".stderr.txt").write_text(result.stderr, encoding="utf-8")
    try:
        body = json.loads(result.stdout)
    except ValueError:
        body = None
    observation = {"command": command, "returncode": result.returncode, "elapsed_seconds": duration,
                   "output": body, "tokens": None, "cost": None}
    write_json(destination.with_suffix(".invocation.json"), observation)
    return observation


def case_record(folder, digest, observation):
    binding = {"run_id": "local-mechanical-experiment", "task_id": "sum-input",
               "command_or_claim_id": "local-fixture-operation", "recipient": "local-python-harness",
               "epoch": 1, "contract_version": "local-fixture-v1", "candidate_digest": digest,
               "idempotency_key": "local-mechanical-experiment/sum-input/1"}
    (folder / "actual.txt").write_bytes((str(observation["actual_sum"]) + "\n").encode("utf-8"))
    write_json(folder / "local-check.json", observation)
    evidence = []
    for evidence_id, filename in (("local-check", "local-check.json"), ("actual-output", "actual.txt"),
                                  ("local-process-receipt", "manifest.stdout.json")):
        evidence.append({"id": evidence_id, "path": filename,
                         "sha256": hash_bytes((folder / filename).read_bytes()), "input_digest": digest})
    record = {"schema_version": 1, "example_only": False, "record_type": "runtime_evidence",
              "binding": binding,
              "checks": [{"id": "sum-check", "required": True, "execution": "COMPLETED",
                          "result": "PASS" if observation["matched"] else "FAIL", "input_digest": digest,
                          "evidence_refs": ["local-check"]}],
              "critical_capability_preflight": [],
              "preflight_applicability": {"status": "NOT_APPLICABLE", "reason": "Local file bookkeeping only; no business capability or agents are started.",
                                          "contract_ref": "local-fixture-v1"},
              "evidence": evidence, "lifecycle": {},
              "checkpoint": {"side_effect_status": "NONE", "retry_requested": False,
                             "reconciliation_execution": "NOT_RUN", "reconciliation_evidence_refs": []},
              "risk_acceptance": {"status": "NOT_DECIDED", "record_ref": None},
              "human_adjudication": {"status": "NOT_DECIDED", "record_ref": None},
              "delivery": {"execution": "NOT_RUN", "result": "UNKNOWN", "evidence_refs": []},
              "metrics": {"tokens": None, "cost": None, "human_interventions": None},
              "limitations": ["Fault-injection fixture only. Receipt is from the local manifest CLI, not an agent host.",
                              "No real risk acceptance, governance adjudication, dispatch, external side effect, or delivery occurs."]}
    return record


def run_case(script, mode_directory, name, expected_code):
    started = time.perf_counter()
    folder = mode_directory / name
    folder.mkdir()
    candidate = folder / "candidate"
    candidate.mkdir()
    (candidate / "empty").mkdir()
    (candidate / "input.json").write_bytes(b'{"values":[2,3],"expected_sum":5}\n')
    manifest = folder / "manifest.json"
    frozen = call(script, ["manifest", "--candidate", candidate, "--output", manifest], folder / "manifest")
    if frozen["returncode"] != 0:
        return {"case": name, "passed": False, "manifest_error": frozen,
                "elapsed_seconds": time.perf_counter() - started}
    digest = frozen["output"]["candidate_digest"]
    check_started = time.perf_counter()
    raw = json.loads((candidate / "input.json").read_text(encoding="utf-8"))
    actual = sum(raw["values"])
    expected = 999 if name == "risk_accepts_failed_check" else raw["expected_sum"]
    observation = {"execution": "COMPLETED", "method": "Python integer sum of real candidate JSON",
                   "expected_sum": expected, "actual_sum": actual, "matched": actual == expected,
                   "elapsed_seconds": time.perf_counter() - check_started}
    record = case_record(folder, digest, observation)
    if name == "changed_during_review":
        (candidate / "input.json").write_bytes(b'{"values":[2,4],"expected_sum":6}\n')
    elif name == "missing_file":
        (candidate / "input.json").unlink()
    elif name == "added_file":
        (candidate / "extra.txt").write_bytes(b"unreviewed content\n")
    elif name == "empty_checks":
        record["checks"] = []
    elif name == "not_run_claims_pass":
        record["checks"][0]["execution"] = "NOT_RUN"
    elif name == "risk_accepts_failed_check":
        record["risk_acceptance"] = {"status": "ACCEPTED", "record_ref": "injected-risk-fixture-not-a-human-approval"}
    elif name in ("unknown_side_effect_retry", "confirmed_absent_retry", "already_applied_retry"):
        status = {"unknown_side_effect_retry": "UNKNOWN", "confirmed_absent_retry": "CONFIRMED_NOT_APPLIED",
                  "already_applied_retry": "CONFIRMED_APPLIED"}[name]
        record["checkpoint"].update(side_effect_status=status, retry_requested=True)
        if status != "UNKNOWN":
            ledger = folder / "local-side-effect-ledger.json"
            write_json(ledger, {"effects": ["fixture-effect"] if status == "CONFIRMED_APPLIED" else []})
            observed_ledger = json.loads(ledger.read_text(encoding="utf-8"))
            write_json(folder / "ledger-observation.json", {"method": "read local fixture ledger",
                                                            "observed": observed_ledger})
            evidence_path = folder / "ledger-observation.json"
            record["evidence"].append({"id": "reconciled", "path": evidence_path.name,
                                       "sha256": hash_bytes(evidence_path.read_bytes()), "input_digest": digest})
            record["checkpoint"].update(reconciliation_execution="COMPLETED", reconciliation_evidence_refs=["reconciled"])
    elif name.startswith("preflight_"):
        # The local probe really produced actual.txt. We then inject wrong expectation or missing output.
        record["critical_capability_preflight"] = [{"id": "local-output-probe", "required": True,
            "execution": "COMPLETED", "result": "PASS", "input_digest": digest,
            "evidence_refs": ["actual-output"], "actual_output_ref": "actual-output", "expected_output": "5\n"}]
        if name == "preflight_wrong_output":
            record["critical_capability_preflight"][0]["expected_output"] = "6\n"
        else:
            (folder / "actual.txt").unlink()
    elif name.startswith("receipt_"):
        record["lifecycle"] = {stage: {"execution": "COMPLETED", "binding": dict(record["binding"]),
                                      "host_receipt_ref": "local-process-receipt"}
                               for stage in ("sent", "received", "started", "completed")}
        if name == "receipt_wrong_epoch":
            record["lifecycle"]["completed"]["binding"]["epoch"] = 2
        else:
            record["lifecycle"]["started"]["execution"] = "NOT_RUN"
    elif name.startswith("dependency_"):
        record["stage_dependencies"] = {"nodes": ["prepare", "review", "adjudicate"],
            "edges": [{"from": "prepare", "to": "review"}, {"from": "review", "to": "adjudicate"}]}
        if name == "dependency_cycle":
            record["stage_dependencies"]["edges"].append({"from": "adjudicate", "to": "prepare"})
    elif name.startswith("historical_"):
        # Preserve a real separate probe candidate and its manifest, rather than
        # relabeling a pre-production sample as the final candidate.
        source_candidate = folder / "probe-candidate"
        source_candidate.mkdir()
        source_bytes = b"\x89PNG\x00\xff\x80local-binary-probe"
        (source_candidate / "probe.bin").write_bytes(source_bytes)
        source_frozen = call(script, ["manifest", "--candidate", source_candidate,
                                      "--output", folder / "probe-manifest.json"], folder / "probe-freeze")
        if source_frozen["returncode"] != 0:
            return {"case": name, "passed": False, "manifest_error": source_frozen,
                    "elapsed_seconds": time.perf_counter() - started}
        source_digest = source_frozen["output"]["candidate_digest"]
        # Actual local byte observation is a mechanical sample only, not a PNG renderer test.
        (folder / "binary-output.bin").write_bytes((source_candidate / "probe.bin").read_bytes())
        record["evidence"].append({"id": "binary-output", "path": "binary-output.bin",
                                   "sha256": hash_bytes(source_bytes), "input_digest": source_digest})
        applicability = {"source_input_digest": source_digest, "target_candidate_digest": digest,
                         "environment": sys.version, "coverage": "local binary byte preservation only",
                         "reviewer": "local deterministic harness", "reason": "same filesystem read/write path",
                         "evidence_refs": ["local-check"]}
        if name == "historical_preflight_wrong_target":
            applicability["target_candidate_digest"] = source_digest
        record["critical_capability_preflight"] = [{"id": "prior-binary-sample", "required": True,
            "execution": "COMPLETED", "result": "PASS", "input_digest": source_digest,
            "evidence_refs": ["binary-output"], "actual_output_ref": "binary-output",
            "output_assertion": {"kind": "sha256", "expected": hash_bytes(source_bytes)},
            "applicability": applicability}]
    write_json(folder / "runtime.json", record)
    outcome = call(script, ["assess", "--candidate", candidate, "--manifest", manifest,
                           "--record", folder / "runtime.json"], folder / "assessment")
    ready = outcome["output"].get("technical_evidence_ready") if isinstance(outcome["output"], dict) else None
    passed = outcome["returncode"] == expected_code and ready is (expected_code == 0)
    result = {"case": name, "execution": "COMPLETED", "passed": passed,
              "expected_exit_code": expected_code, "actual_exit_code": outcome["returncode"],
              "expected_technical_evidence_ready": expected_code == 0, "technical_evidence_ready": ready,
              "candidate_digest_before_fault": digest, "false_acceptance": expected_code != 0 and ready is True,
              "issues": outcome["output"].get("issues") if outcome["output"] else None,
              "elapsed_seconds": time.perf_counter() - started,
              "cli_elapsed_seconds": frozen["elapsed_seconds"] + outcome["elapsed_seconds"],
              "local_cli_invocations": 3 if name.startswith("historical_") else 2,
              "tokens": None, "cost": None, "human_interventions": None}
    if name.startswith("historical_"):
        result["cli_elapsed_seconds"] += source_frozen["elapsed_seconds"]
    write_json(folder / "result.json", result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new directory; existing paths are never overwritten")
    args = parser.parse_args()
    destination = args.output.absolute()
    try:
        destination.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        parser.error("output path already exists; choose a new directory: " + str(destination))
    started = time.perf_counter()
    results = []
    for mode in MODES:
        script = ROOT / ("gas-" + mode + "-development/scripts/gas_runtime.py")
        directory = destination / mode
        directory.mkdir()
        mode_started = time.perf_counter()
        cases = [run_case(script, directory, name, expected) for name, expected in CASES]
        result = {"mode": mode, "execution": "COMPLETED", "script_sha256": hash_bytes(script.read_bytes()),
                  "passed": all(case["passed"] for case in cases), "case_count": len(cases), "cases": cases,
                  "elapsed_seconds": time.perf_counter() - mode_started, "tokens": None, "cost": None,
                  "scope": "Real local file/CLI fault tests only; no agent-team or governance performance comparison."}
        write_json(directory / "results.json", result)
        results.append(result)
    summary = {"created_at": datetime.now(timezone.utc).isoformat(), "execution": "COMPLETED",
               "passed": all(result["passed"] for result in results), "mode_count": len(MODES),
               "case_count": sum(result["case_count"] for result in results),
               "false_acceptances": sum(case.get("false_acceptance", False) for result in results for case in result["cases"]),
               "elapsed_seconds": time.perf_counter() - started, "tokens": None, "cost": None,
               "human_interventions": None, "python": sys.version,
               "scope": "Identical code and input fixtures across modes. Measures this bookkeeping utility, not agent skill effectiveness or governance superiority.",
               "modes": [{key: value for key, value in result.items() if key != "cases"} for result in results]}
    write_json(destination / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
