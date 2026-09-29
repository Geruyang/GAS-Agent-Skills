#!/usr/bin/env python3
"""Offline, standard-library checks for the GAS skill package.

These checks validate files and declarations, NOT agent behavior, security
isolation, or Windows installer execution. No network or project changes.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path
from typing import Any

MODES = {
    "gas-decentralized-development": "decentralized",
    "gas-centralized-development": "centralized",
}
REQUIRED = (
    "SKILL.md", "references/protocol.md", "templates/run.example.json",
    "templates/task.example.json", "templates/review.example.json",
    "evals/scenarios.json",
)
HEADINGS = (
    "## 启动与适用边界", "## 权责边界", "## 执行流程",
    "## 停止与升级", "## 交付格式",
)
COMMON_RULES = {"AUTH-01", "AUTH-02", "EVID-01", "EVID-02", "SAFE-01", "BUDGET-01", "FALLBACK-01", "CHANGE-01"}


def validate(root: Path, selected: list[str], package: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: str = "") -> None:
        checks.append({"check": name, "passed": bool(passed), "detail": detail})

    def read_json(path: Path, label: str) -> Any:
        try:
            obj = json.loads(path.read_text(encoding="utf-8-sig"))
            if not isinstance(obj, dict):
                raise ValueError("Expected a JSON object")
            add(label, True)
            return obj
        except (OSError, ValueError) as exc:
            add(label, False, str(exc))
            return None

    def object_field(parent: dict, key: str, label: str) -> dict:
        value = parent.get(key)
        add(f"{label}:{key}-object", isinstance(value, dict))
        return value if isinstance(value, dict) else {}

    for name in selected:
        base = root / name
        for relative in REQUIRED:
            add(f"{name}:file:{relative}", (base / relative).is_file())
        main = base / "SKILL.md"
        if not main.is_file():
            continue
        try:
            text = main.read_text(encoding="utf-8")
            protocol = (base / "references/protocol.md").read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            add(f"{name}:utf8", False, str(exc))
            continue
        add(f"{name}:utf8", True)
        fm = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
        add(f"{name}:frontmatter", fm is not None)
        if fm:
            metadata = dict(re.findall(r"^(name|description): (.+)$", fm.group(1), re.M))
            add(f"{name}:name", metadata.get("name") == name and bool(re.fullmatch(r"[a-z0-9-]+", name)))
            description = metadata.get("description", "")
            add(f"{name}:description", description.startswith("Use when ") and len(description) < 500)
            add(f"{name}:frontmatter-size", len(fm.group(1)) <= 1024)
        add(f"{name}:main-size", len(text.splitlines()) <= 200)
        for heading in HEADINGS:
            add(f"{name}:heading:{heading}", heading in text)
        for doc in (main, base / "references/protocol.md"):
            content = doc.read_text(encoding="utf-8")
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
                if target.startswith(("http:", "https:", "#")):
                    continue
                clean = target.split("#", 1)[0]
                resolved = (doc.parent / clean).resolve()
                within = resolved.is_relative_to(base.resolve())
                add(f"{name}:link:{doc.name}:{target}", within and resolved.is_file())
        rules = set(re.findall(r"\b[A-Z]+-\d{2}\b", text + "\n" + protocol))
        add(f"{name}:common-rules", COMMON_RULES.issubset(rules))
        add(f"{name}:enforcement-limits", all(term in text + protocol for term in ("权限隔离", "worktree", "独立", "未执行", "不自动")))

        run = read_json(base / "templates/run.example.json", f"{name}:run-json")
        if isinstance(run, dict):
            add(f"{name}:run-mode", run.get("mode") == MODES[name])
            approval = object_field(run, "approval", name)
            add(f"{name}:unapproved-example", run.get("example_only") is True and approval.get("approved") is False and approval.get("record") is None)
            budget = object_field(run, "budget", name)
            add(f"{name}:bounded-defaults", all(isinstance(budget.get(k), int) and not isinstance(budget.get(k), bool) and budget[k] > 0 for k in ("max_active_workers", "max_tool_calls_total", "max_task_attempts", "max_review_rounds", "max_conflict_rounds")))
            controls = object_field(run, "controls", name)
            add(f"{name}:safe-defaults", controls.get("production_release_enabled") is False and controls.get("independent_review_required") is True and controls.get("require_exact_commit_checks") is True)
            add(f"{name}:protected-paths", bool(controls.get("protected_paths")))
            runtime = object_field(run, "runtime", name)
            add(f"{name}:unknown-capabilities", runtime.get("subagents_verified") is False and runtime.get("permission_isolation_verified") is False and runtime.get("reviewer_identity") is None)
            expected_dispatch = "single-executor-self-claim" if MODES[name] == "decentralized" else "coordinator-assignment"
            add(f"{name}:dispatch-distinction", object_field(run, "dispatch", name).get("method") == expected_dispatch)
            if MODES[name] == "decentralized":
                prefix = f"{name}:separation:"
                governance = object_field(run, "governance", prefix)
                roles = object_field(governance, "roles", prefix)
                add(prefix + "three-roles", set(roles) == {"legislator", "executor", "arbiter"}
                    and governance.get("agent_count") == 3)
                add(prefix + "separate-powers", governance.get("role_combination_allowed") is False
                    and governance.get("majority_override_allowed") is False
                    and governance.get("main_session_role") in roles)
                add(prefix + "single-executor", budget.get("max_active_workers") == 1
                    and budget.get("max_active_agents") == 3)
                add(prefix + "identities-not-invented", all(isinstance(role, dict)
                    and role.get("identity") is None and role.get("epoch") is None
                    and role.get("available") is False for role in roles.values())
                    and runtime.get("three_distinct_identities_verified") is False)
                contract = object_field(run, "contract", prefix)
                add(prefix + "contract-not-effective", contract.get("status") == "DRAFT"
                    and contract.get("authored_by_role") == "legislator"
                    and contract.get("effective_record") is None
                    and contract.get("executor_feasibility") == "NOT_REVIEWED"
                    and contract.get("arbiter_authority_check") == "NOT_REVIEWED")
                intent = object_field(run, "human_intent", prefix)
                intent_review = object_field(contract, "intent_review", prefix)
                add(prefix + "intent-source-not-invented", intent.get("version") is None
                    and intent.get("source_records") == [] and intent.get("unconfirmed_interpretations") == [])
                add(prefix + "intent-review-not-run", intent_review.get("verdict") == "NOT_RUN"
                    and intent_review.get("reviewer_role") == "arbiter"
                    and intent_review.get("reviewer_identity") is None and intent_review.get("reviewer_epoch") is None
                    and intent_review.get("record") is None
                    and intent_review.get("contract_version") == run.get("contract_version")
                    and intent_review.get("intent_version") == intent.get("version"))

        task = read_json(base / "templates/task.example.json", f"{name}:task-json")
        if isinstance(task, dict):
            needed = {"id", "mode", "goal", "allowed_paths", "protected_paths", "dependencies", "acceptance_criteria", "base_commit", "head_commit", "contract_version", "owner", "state", "budget", "evidence", "dispatch"}
            add(f"{name}:task-contract", needed.issubset(task) and task.get("mode") == MODES[name])
            add(f"{name}:draft-no-fake-evidence", task.get("example_only") is True and task.get("state") == "DRAFT" and task.get("owner") is None and task.get("evidence") == [] and task.get("head_commit") is None)
            dispatch = object_field(task, "dispatch", name)
            if MODES[name] == "decentralized":
                add(f"{name}:claim-fields", {"lease_id", "lease_expires_at", "fencing_token", "expected_state_version"}.issubset(dispatch))
            else:
                add(f"{name}:assignment-fields", {"assigned_by", "assignment_id", "plan_version", "acknowledged"}.issubset(dispatch))

        review = read_json(base / "templates/review.example.json", f"{name}:review-json")
        if isinstance(review, dict):
            add(f"{name}:review-not-executed", review.get("verdict") == "NOT_RUN" and review.get("checks") == [] and review.get("reviewer_identity") is None)
            findings_field = "findings" if name == "gas-centralized-development" and review.get("schema_version") in (2, 3) else "blocking_findings"
            add(f"{name}:review-scope", {"base_commit", "head_commit", "integration_commit", "contract_version", "independence_verified", findings_field, "unverified_items"}.issubset(review))
            add(f"{name}:no-fake-independence", review.get("independence_verified") is False)

        if MODES[name] == "decentralized":
            prefix = f"{name}:separation:"
            add(prefix + "independent-arbiter", isinstance(review, dict)
                and review.get("reviewer_role") == "arbiter" and review.get("reviewer_epoch") is None)
            add(prefix + "task-executor", isinstance(task, dict) and task.get("owner_role") == "executor"
                and task.get("owner_epoch") is None and task.get("contract_record") is None)
            dispute = read_json(base / "templates/dispute.example.json", prefix + "dispute-json")
            if isinstance(dispute, dict):
                resolution = object_field(dispute, "resolution", prefix)
                add(prefix + "dispute-not-decided", dispute.get("example_only") is True
                    and dispute.get("status") == "DRAFT" and dispute.get("evidence") == []
                    and resolution.get("verdict") == "NOT_DECIDED" and resolution.get("record") is None)
                add(prefix + "dispute-scope", {"challenged_role", "raised_by_identity", "disputed_action",
                    "rule_references", "affected_scope", "requested_resolution", "recusal"}.issubset(dispute))
                add(prefix + "dispute-epochs", "raised_by_epoch" in dispute
                    and dispute["raised_by_epoch"] is None
                    and "decided_by_epoch" in resolution and resolution["decided_by_epoch"] is None)
                reconsideration = object_field(dispute, "rule_reconsideration", prefix)
                add(prefix + "rule-reconsideration-not-decided", reconsideration.get("handler_role") == "legislator"
                    and reconsideration.get("decision") == "NOT_REQUESTED"
                    and reconsideration.get("record") is None)
                intent_change = object_field(dispute, "intent_change", prefix)
                add(prefix + "intent-change-not-approved", intent_change.get("proposed_by_role") == "legislator"
                    and intent_change.get("human_decision") == "NOT_REQUESTED"
                    and intent_change.get("human_response_record") is None
                    and intent_change.get("approved_scope") == []
                    and intent_change.get("new_intent_version") is None)
            release = read_json(base / "templates/release.example.json", prefix + "release-json")
            if isinstance(release, dict):
                add(prefix + "release-not-run", release.get("example_only") is True
                    and release.get("status") == "NOT_RUN" and release.get("actions") == []
                    and release.get("receipt") is None and release.get("actor_identity") is None)
                gates = object_field(release, "gates", prefix)
                needed_gates = {"contract_effective", "independent_review_passed", "exact_artifact_verified",
                    "action_authorized", "all_roles_available", "current_epochs_verified",
                    "no_blocking_disputes", "budget_available"}
                add(prefix + "release-gates", set(gates) == needed_gates
                    and all(value is False for value in gates.values())
                    and release.get("actor_role") == "executor")
                add(prefix + "release-evidence", {"effective_contract_record", "review_record",
                    "authorization_record", "integration_commit", "artifact_digest"}.issubset(release)
                    and all(release.get(key) is None for key in ("effective_contract_record", "review_record",
                        "authorization_record", "integration_commit", "artifact_digest")))
            for label, record in (("task", task), ("review", review), ("dispute", dispute), ("release", release)):
                add(prefix + label + "-binding", isinstance(record, dict) and isinstance(run, dict)
                    and record.get("schema_version") == run.get("schema_version") == 2
                    and record.get("run_id") == run.get("run_id")
                    and record.get("contract_version") == run.get("contract_version"))

        scenarios = read_json(base / "evals/scenarios.json", f"{name}:eval-json")
        if isinstance(scenarios, dict):
            cases = scenarios.get("cases", [])
            valid_cases = isinstance(cases, list) and all(
                isinstance(c, dict) and isinstance(c.get("id"), str)
                and isinstance(c.get("rules"), list)
                and all(isinstance(rule, str) for rule in c["rules"])
                and isinstance(c.get("pressures", []), list)
                for c in cases
            )
            add(f"{name}:eval-structure", valid_cases)
            if not valid_cases:
                cases = []
            add(f"{name}:eval-count", len(cases) >= 12)
            ids = [c.get("id") for c in cases]
            add(f"{name}:eval-unique", len(set(ids)) == len(ids))
            add(f"{name}:eval-not-run", scenarios.get("execution_status") == "NOT_RUN" and all(c.get("status") == "NOT_RUN" for c in cases))
            add(f"{name}:eval-assertions", all(c.get("prompt") and c.get("expected_actions") and c.get("failure_actions") for c in cases))
            referenced = {r for c in cases for r in c.get("rules", [])}
            add(f"{name}:eval-rule-coverage", COMMON_RULES.issubset(referenced) and referenced.issubset(rules))
            add(f"{name}:eval-pressure", any(len(c.get("pressures", [])) >= 3 for c in cases))

        # Keep common checks, and enforce the new hub records through its own validator.
        if name == "gas-centralized-development":
            validator_path = base / "scripts/validate_skill.py"
            try:
                spec = importlib.util.spec_from_file_location("gas_commander_v3_validator", validator_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                result = module.validate(base)
                add(f"{name}:v3:validator", True)
                for check in result["checks"]:
                    add(f"{name}:v3:{check['name']}", check["ok"], check["detail"])
            except (OSError, ValueError, TypeError, AttributeError, KeyError, SyntaxError) as exc:
                add(f"{name}:v3:validator", False, str(exc))

    if package:
        for item in ("README.zh-CN.md", "Install-GAS-Skills.ps1", "VALIDATION.md", "manifest.sha256.json"):
            add(f"package:file:{item}", (root / item).is_file())
        installer = root / "Install-GAS-Skills.ps1"
        if installer.is_file():
            script = installer.read_text(encoding="utf-8-sig")
            add("package:installer-target", "E:\\AIProject\\GAS" in script)
            add("package:installer-preflight", all(term in script for term in ("ShouldProcess", "Refusing to overwrite", "Get-FileHash", "Directory]::Move")))
            add("package:installer-no-network-or-policy-change", not re.search(r"(?i)Invoke-WebRequest|Invoke-RestMethod|Set-ExecutionPolicy|Start-Process.*RunAs", script))
        manifest = read_json(root / "manifest.sha256.json", "package:manifest-json")
        if isinstance(manifest, dict):
            files = manifest.get("files", {})
            actual = {p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file() and p.name != "manifest.sha256.json" and "__pycache__" not in p.parts}
            add("package:manifest-complete", set(files) == actual)
            for rel, expected in files.items():
                p = (root / rel).resolve()
                safe = p.is_relative_to(root.resolve())
                digest = hashlib.sha256(p.read_bytes()).hexdigest() if safe and p.is_file() else None
                add(f"package:sha256:{rel}", digest == expected)
    failed = [c for c in checks if not c["passed"]]
    return {
        "scope": "static package checks only; not model behavior or Windows execution",
        "passed": not failed,
        "check_count": len(checks), "failure_count": len(failed), "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--skill", choices=list(MODES))
    parser.add_argument("--report", type=Path, help="Optional JSON report; keep it outside the package to preserve the manifest.")
    args = parser.parse_args()
    report = validate(args.root, [args.skill] if args.skill else list(MODES), package=args.skill is None)
    for check in report["checks"]:
        if not check["passed"]:
            print("FAIL:", check["check"], check["detail"])
    print(f"Static checks: {report['check_count'] - report['failure_count']}/{report['check_count']} passed")
    print(report["scope"])
    if args.report:
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
