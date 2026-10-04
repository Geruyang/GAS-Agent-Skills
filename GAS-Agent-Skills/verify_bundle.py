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
COMBINED = "gas-combined-development"
ROLE_HOSTING = {
    "gas-centralized-development": (4, {"coordinator", "executor", "reviewer", "supervisor"}),
    "gas-decentralized-development": (3, {"legislator", "executor", "arbiter"}),
    COMBINED: (6, {"outer.legislator", "outer.executor", "outer.arbiter", "inner.coordinator",
                   "inner.executor", "inner.reviewer", "inner.supervisor"}),
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
EVAL_VERSIONS = {"gas-decentralized-development": 1, "gas-centralized-development": 3, COMBINED: 1}


def validate(root: Path, selected: list[str], package: bool = False) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    if package:
        selected = list(dict.fromkeys([*selected, COMBINED]))

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

    def defaults_match(value: Any, expected: dict[str, Any]) -> bool:
        return isinstance(value, dict) and all(
            key in value and type(value[key]) is type(default) and value[key] == default
            for key, default in expected.items())

    def nonempty_text(value: Any) -> bool:
        return isinstance(value, str) and bool(value.strip())

    def text_list(value: Any) -> bool:
        return isinstance(value, list) and bool(value) and all(nonempty_text(item) for item in value)

    def common_skill_checks(base: Path, name: str) -> set[str]:
        main = base / "SKILL.md"
        try:
            text = main.read_text(encoding="utf-8")
            protocol = (base / "references/protocol.md").read_text(encoding="utf-8")
        except (OSError, UnicodeError) as exc:
            add(f"{name}:utf8", False, str(exc))
            return set()
        add(f"{name}:utf8", True)
        fm = re.match(r"\A---\n(.*?)\n---\n", text, re.S)
        add(f"{name}:frontmatter", fm is not None)
        if fm:
            metadata = dict(re.findall(r"^(name|description): (.+)$", fm.group(1), re.M))
            add(f"{name}:name", metadata.get("name") == name and bool(re.fullmatch(r"[a-z0-9-]+", name)))
            description = metadata.get("description", "")
            add(f"{name}:description", description.startswith("Use when ") and bool(description[9:].strip()))
            add(f"{name}:description-size", len(description) <= 1024)
        add(f"{name}:main-size", len(text.splitlines()) <= 200)
        for heading in HEADINGS:
            add(f"{name}:heading:{heading}", heading in text)
        # Combined intentionally references its two sibling skills. This does not
        # allow their text to substitute for this skill's own safety declarations.
        link_root = root if name == COMBINED else base
        docs = [main, base / "references/protocol.md"]
        if name == COMBINED:
            docs = [main, *sorted((base / "references").glob("*.md"))]
        for doc in docs:
            try:
                content = doc.read_text(encoding="utf-8")
                add(f"{name}:utf8:{doc.name}", True)
            except (OSError, UnicodeError) as exc:
                add(f"{name}:utf8:{doc.name}", False, str(exc))
                continue
            for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
                if target.startswith(("http:", "https:", "#")):
                    continue
                resolved = (doc.parent / target.split("#", 1)[0]).resolve()
                add(f"{name}:link:{doc.name}:{target}",
                    resolved.is_relative_to(link_root.resolve()) and resolved.is_file())
        own_text = text + "\n" + protocol
        rules = set(re.findall(r"\b[A-Z]+-\d{2}\b", own_text))
        add(f"{name}:common-rules", COMMON_RULES.issubset(rules))
        add(f"{name}:enforcement-limits", all(term in own_text for term in
            ("权限隔离", "worktree", "独立", "未执行", "不自动")))
        return rules

    def eval_checks(base: Path, name: str, rules: set[str]) -> None:
        scenarios = read_json(base / "evals/scenarios.json", f"{name}:eval-json")
        if not isinstance(scenarios, dict):
            return
        # Evals are independently versioned; run-contract versions are not their schema.
        add(f"{name}:eval-metadata", type(scenarios.get("schema_version")) is int
            and scenarios.get("schema_version") == EVAL_VERSIONS[name]
            and scenarios.get("skill") == name
            and all(nonempty_text(scenarios.get(key)) for key in ("purpose", "procedure")))
        cases = scenarios.get("cases")
        valid_cases = isinstance(cases, list) and all(
            isinstance(case, dict) and nonempty_text(case.get("id"))
            and text_list(case.get("rules"))
            and all(re.fullmatch(r"[A-Z]+-\d{2}", rule) for rule in case["rules"])
            and isinstance(case.get("pressures", []), list)
            and all(nonempty_text(value) for value in case.get("pressures", []))
            for case in cases)
        add(f"{name}:eval-structure", valid_cases)
        if not valid_cases:
            cases = []
        # Preserve pure-mode regression baselines; combined has a distinct set.
        add(f"{name}:eval-count", bool(cases) if name == COMBINED else len(cases) >= 12)
        ids = [case["id"] for case in cases]
        add(f"{name}:eval-unique", len(set(ids)) == len(ids))
        add(f"{name}:eval-not-run", scenarios.get("execution_status") == "NOT_RUN"
            and all(case.get("status") == "NOT_RUN" for case in cases))
        add(f"{name}:eval-assertions", bool(cases) and all(nonempty_text(case.get("prompt"))
            and text_list(case.get("expected_actions")) and text_list(case.get("failure_actions"))
            for case in cases))
        referenced = {rule for case in cases for rule in case["rules"]}
        required = {f"COM-{index:02}" for index in range(1, 9)} if name == COMBINED else COMMON_RULES
        add(f"{name}:eval-rule-coverage", required.issubset(referenced) and referenced.issubset(rules))
        if name != COMBINED:
            add(f"{name}:eval-pressure", any(len(case.get("pressures", [])) >= 3 for case in cases))

    def execution_team_defaults(run: dict, name: str) -> None:
        # Configurable plans remain unapproved examples; this does not authenticate a roster.
        team = object_field(run, "execution_team", name)
        count = team.get("executor_count")
        valid_count = type(count) is int and count > 0
        add(f"{name}:execution-team:count", valid_count)
        source = team.get("count_source")
        add(f"{name}:execution-team:count-source", source in ("default", "user", "proposed")
            and (source != "default" or count == 1 and type(count) is int))
        offset = {"gas-centralized-development": 3, "gas-decentralized-development": 2, COMBINED: 5}[name]
        planned = team.get("planned_distinct_subagents")
        add(f"{name}:execution-team:headcount", valid_count and type(planned) is int
            and planned == count + offset)
        if "planned_total_sessions" in team:
            add(f"{name}:execution-team:total-sessions", valid_count
                and type(team["planned_total_sessions"]) is int
                and team["planned_total_sessions"] == count + offset + 1)
        add(f"{name}:execution-team:unassigned-example", defaults_match(team, {
            "executor_roster": [], "assignments": []}))

    def role_hosting_defaults(run: dict, name: str) -> None:
        execution_team_defaults(run, name)
        # These are conservative example declarations, not live host attestations.
        main_session = object_field(run, "main_session", name)
        add(f"{name}:main-session:display-only", defaults_match(main_session, {
            "purpose": "progress_display", "identity": None, "governance_role": None,
            "counts_as_role": False, "business_execution_allowed": False}))
        hosting = object_field(run, "role_hosting", name)
        minimum, expected_roles = ROLE_HOSTING[name]
        add(f"{name}:role-hosting:subagents-only", defaults_match(hosting, {
            "all_roles_must_be_subagents": True}))
        add(f"{name}:role-hosting:minimum-subagents", defaults_match(hosting, {
            "required_distinct_subagents_minimum": minimum}))
        roles = hosting.get("required_roles")
        add(f"{name}:role-hosting:required-roles", isinstance(roles, list)
            and all(isinstance(role, str) for role in roles)
            and len(roles) == len(expected_roles) and set(roles) == expected_roles)
        add(f"{name}:role-hosting:unverified-example", defaults_match(hosting, {"verified": False}))
        add(f"{name}:role-hosting:empty-roster", defaults_match(hosting, {"roster": []}))
        legacy_parent = {"gas-decentralized-development": "governance", COMBINED: "runtime"}.get(name)
        if legacy_parent is not None:
            add(f"{name}:main-session:no-legacy-role", defaults_match(run.get(legacy_parent), {
                "main_session_role": None}))

    def runtime_examples(base: Path, name: str) -> None:
        prefix = f"{name}:runtime-example"
        record = read_json(base / "templates/runtime.example.json", prefix + ":json")
        if isinstance(record, dict):
            add(prefix + ":schema", defaults_match(record, {
                "schema_version": 1, "example_only": True, "record_type": "runtime_evidence",
                "mode": MODES.get(name, "combined")}))
            add(prefix + ":unbound", defaults_match(record.get("binding"), dict.fromkeys((
                "run_id", "task_id", "command_or_claim_id", "recipient", "epoch",
                "contract_version", "candidate_digest", "idempotency_key"))))
            add(prefix + ":no-evidence", defaults_match(record, {
                "governance_record_refs": [], "evidence": []}))
            for field in ("checks", "critical_capability_preflight"):
                entries = record.get(field)
                add(prefix + ":" + field + "-not-run", isinstance(entries, list) and bool(entries)
                    and all(defaults_match(entry, {"execution": "NOT_RUN", "result": "UNKNOWN",
                                                  "input_digest": None, "evidence_refs": []})
                            for entry in entries))
                if field == "critical_capability_preflight" and isinstance(entries, list):
                    add(prefix + ":preflight-no-observations", all(
                        defaults_match(entry, {"team_ready_evidence_ref": None, "actual_output_ref": None})
                        and defaults_match(entry.get("applicability"), {
                            "source_input_digest": None, "target_candidate_digest": None,
                            "environment": None, "coverage": None, "reviewer": None,
                            "reason": None, "evidence_refs": []}) for entry in entries))
            add(prefix + ":preflight-unassessed", defaults_match(record.get("preflight_applicability"), {
                "status": "NOT_ASSESSED", "reason": None, "contract_ref": None}))
            lifecycle = record.get("lifecycle")
            add(prefix + ":lifecycle-not-run", isinstance(lifecycle, dict) and all(
                defaults_match(lifecycle.get(stage), {
                    "execution": "NOT_RUN", "host_receipt_ref": None, "binding": None})
                for stage in ("sent", "received", "started", "completed")))
            add(prefix + ":checkpoint-not-run", defaults_match(record.get("checkpoint"), {
                "checkpoint_id": None, "resume_from": None, "last_completed_stage": None,
                "side_effect_status": "UNKNOWN", "retry_requested": False,
                "reconciliation_execution": "NOT_RUN", "reconciliation_evidence_refs": [],
                "prior_attempt_ref": None, "remaining_budget_ref": None}))
            add(prefix + ":progress-not-run", defaults_match(record.get("progress"), {
                "execution": "NOT_RUN", "observed_progress_refs": [], "blocking_facts": [],
                "next_verifiable_step": None, "stagnation_count": None, "replan_count": None,
                "max_replans": None, "stop_condition": None, "remaining_budget_ref": None}))
            add(prefix + ":review-not-run", defaults_match(record.get("review_method"), {
                "execution": "NOT_RUN", "reviewer_identity": None, "author_method": None,
                "independent_method": None, "independence_basis_refs": [],
                "deterministic_calculation_refs": [], "full_scope_required_by_contract": None,
                "coverage_refs": [], "unverified_items": []}))
            add(f"{name}:verification-ownership:unobserved", defaults_match(record.get("verification_ownership"), {
                "executor_identity": None, "task_ref": None, "test_code_paths": [],
                "execution_evidence_refs": [], "analysis_owner_identity": None,
                "supplement_request_refs": []}))
            add(prefix + ":risk-not-decided", defaults_match(record.get("risk_acceptance"), {
                "status": "NOT_DECIDED", "authority": None, "record_ref": None}))
            add(prefix + ":human-not-decided", defaults_match(record.get("human_adjudication"), {
                "status": "NOT_DECIDED", "identity": None, "record_ref": None}))
            add(prefix + ":delivery-not-run", defaults_match(record.get("delivery"), {
                "execution": "NOT_RUN", "result": "UNKNOWN", "target": None,
                "authorization_ref": None, "evidence_refs": []}))
            metrics = record.get("metrics")
            add(prefix + ":metrics-unmeasured", defaults_match(metrics, dict.fromkeys((
                "elapsed_seconds", "model_calls", "tool_calls", "tokens", "cost", "currency",
                "human_interventions", "false_acceptances")))
                and all(value is None for value in metrics.values()))
        scenarios = read_json(base / "evals/runtime-scenarios.json", f"{name}:runtime-eval-json")
        if isinstance(scenarios, dict):
            cases = scenarios.get("cases")
            add(f"{name}:runtime-eval-not-run", defaults_match(scenarios, {
                "schema_version": 1, "example_only": True, "mode": MODES.get(name, "combined"),
                "execution_status": "NOT_RUN"})
                and isinstance(cases, list) and bool(cases) and all(defaults_match(case, {
                    "status": "NOT_RUN", "observed_result": None, "elapsed_seconds": None,
                    "tokens": None, "cost": None}) for case in cases))

    for name in selected:
        base = root / name
        if base.is_dir():
            runtime_examples(base, name)
            rules = common_skill_checks(base, name)
            eval_checks(base, name, rules)
        if name == COMBINED:
            for relative in ("SKILL.md", "references/protocol.md", "references/architecture-guide.md",
                             "references/runtime-evidence.md", "references/research-basis.md",
                             "scripts/gas_runtime.py", "templates/run.example.json",
                             "templates/runtime.example.json", "templates/review-reuse.example.json",
                             "evals/scenarios.json", "evals/runtime-scenarios.json"):
                add(f"{name}:file:{relative}", (base / relative).is_file())
            run = read_json(base / "templates/run.example.json", f"{name}:run-json")
            if isinstance(run, dict):
                role_hosting_defaults(run, name)
                add(f"{name}:schema", type(run.get("schema_version")) is int
                    and run.get("schema_version") == 1 and run.get("mode") == "combined")
                approval = object_field(run, "approval", name)
                add(f"{name}:unapproved-example", run.get("example_only") is True
                    and run.get("status") == "DRAFT" and approval.get("approved") is False
                    and approval.get("record") is None)
                outer = object_field(run, "outer", name)
                inner = object_field(run, "inner", name)
                outer_roles = object_field(outer, "roles", f"{name}:outer")
                inner_roles = object_field(inner, "roles", f"{name}:inner")
                add(f"{name}:roles", set(outer_roles) == {"legislator", "executor", "arbiter"}
                    and set(inner_roles) == {"coordinator", "executor", "reviewer", "supervisor"})
                add(f"{name}:unknown-identities", all(isinstance(role, dict)
                    and role.get("identity") is None and role.get("epoch") is None
                    and role.get("available") is False
                    for role in [*outer_roles.values(), *inner_roles.values()]))
                bridge = object_field(run, "bridge", name)
                add(f"{name}:bridge-boundary", bridge.get("outer_executor_is_inner_coordinator") is True
                    and bridge.get("outer_peers_outside_inner_command") is True
                    and bridge.get("identity_equality_verified") is False
                    and bridge.get("epoch_equality_verified") is False)
                runtime = object_field(run, "runtime", name)
                add(f"{name}:six-identities", type(runtime.get("required_distinct_identities_minimum")) is int
                    and runtime.get("required_distinct_identities_minimum") == 6
                    and runtime.get("roles_verified") is False)
                controls = object_field(run, "controls", name)
                add(f"{name}:independent-gates", all(controls.get(key) is True for key in (
                    "independent_inner_review_required", "inner_supervision_required",
                    "independent_outer_adjudication_required", "exact_candidate_binding_required"))
                    and controls.get("production_release_enabled") is False)
                add(f"{name}:review-code-boundary", defaults_match(controls, {
                    "reviewers_write_test_code": False, "supplemental_verification_assigned_by_bridge": True}))
                delivery = object_field(run, "delivery", name)
                add(f"{name}:delivery-not-run", delivery.get("status") == "NOT_RUN"
                    and delivery.get("gates_verified") is False and delivery.get("receipt_ref") is None
                    and delivery.get("action_id") is None)
            reuse = read_json(base / "templates/review-reuse.example.json", f"{name}:reuse-json")
            if isinstance(reuse, dict):
                opinions = reuse.get("opinions")
                add(f"{name}:reuse-not-run", reuse.get("example_only") is True
                    and isinstance(opinions, list) and bool(opinions)
                    and all(isinstance(item, dict) and item.get("status") == "NOT_RUN"
                            and item.get("issuer_identity") is None for item in opinions))
                entries = reuse.get("evidence_reuse")
                add(f"{name}:evidence-reuse-not-run", isinstance(entries, list) and bool(entries)
                    and all(defaults_match(item, {"status": "NOT_RUN", "checker_identity": None,
                                                 "check_result_ref": None, "independent_judgment_ref": None,
                                                 "full_independent_check_ref": None})
                            and defaults_match(item.get("environment_applicability"), {
                                "status": "NOT_VERIFIED", "basis_ref": None}) for item in entries))
                add(f"{name}:dependency-check-not-run", defaults_match(reuse.get("dependency_details"), {
                    "check_execution": "NOT_RUN", "checked_by_identity": None,
                    "check_method": None, "check_evidence_ref": None}))
            continue
        for relative in REQUIRED:
            add(f"{name}:file:{relative}", (base / relative).is_file())
        main = base / "SKILL.md"
        if not main.is_file():
            continue

        run = read_json(base / "templates/run.example.json", f"{name}:run-json")
        if isinstance(run, dict):
            role_hosting_defaults(run, name)
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
            team = run.get("execution_team") if isinstance(run.get("execution_team"), dict) else {}
            expected_dispatch = (("single-executor-self-claim" if team.get("executor_count") == 1
                                  else "peer-executor-self-claim")
                                 if MODES[name] == "decentralized" else "coordinator-assignment")
            add(f"{name}:dispatch-distinction", object_field(run, "dispatch", name).get("method") == expected_dispatch)
            if MODES[name] == "decentralized":
                prefix = f"{name}:separation:"
                governance = object_field(run, "governance", prefix)
                roles = object_field(governance, "roles", prefix)
                add(prefix + "three-roles", set(roles) == {"legislator", "executor", "arbiter"}
                    and type(governance.get("agent_count")) is int
                    and governance.get("agent_count") == (run.get("execution_team", {}).get("planned_distinct_subagents")
                         if isinstance(run.get("execution_team"), dict) else None))
                add(prefix + "separate-powers", governance.get("role_combination_allowed") is False
                    and governance.get("majority_override_allowed") is False
                    and "main_session_role" in governance and governance["main_session_role"] is None)
                team = run.get("execution_team") if isinstance(run.get("execution_team"), dict) else {}
                count = team.get("executor_count")
                add(prefix + "executor-capacity", type(count) is int and count > 0
                    and type(budget.get("max_active_workers")) is int
                    and 1 <= budget["max_active_workers"] <= count
                    and type(budget.get("max_active_agents")) is int
                    and budget["max_active_agents"] >= count + 2)
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
            if name == "gas-centralized-development":
                add(f"{name}:review-code-boundary", review.get("reviewer_may_write_verification_code") is False)
            else:
                add(f"{name}:review-code-boundary", defaults_match(review.get("review_boundary"), {
                    "test_code_write_allowed": False, "analysis_only": True, "existing_command_rerun_allowed": True}))

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

        # Keep common checks, and enforce the new hub records through its own validator.
        if name == "gas-centralized-development":
            validator_path = base / "scripts/validate_skill.py"
            try:
                spec = importlib.util.spec_from_file_location("gas_commander_v3_validator", validator_path)
                if spec is None or spec.loader is None:
                    raise ImportError("validator module has no usable loader")
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                result = module.validate(base)
                add(f"{name}:v3:validator", True)
                for check in result["checks"]:
                    add(f"{name}:v3:{check['name']}", check["ok"], check["detail"])
            except Exception as exc:  # Isolate validator defects, not control-flow BaseExceptions.
                add(f"{name}:v3:validator", False, f"{type(exc).__name__}: {exc}")

    if package:
        for item in ("README.zh-CN.md", "Install-GAS-Skills.ps1", "VALIDATION.md", "manifest.sha256.json"):
            add(f"package:file:{item}", (root / item).is_file())
        installer = root / "Install-GAS-Skills.ps1"
        if installer.is_file():
            script = installer.read_text(encoding="utf-8-sig")
            add("package:installer-default", "GetFolderPath('UserProfile')" in script
                and "'.agents\\skills'" in script and "Join-Path" in script)
            add("package:installer-absolute-destination", "IsPathRooted($Destination)" in script)
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
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent,
                        help="Package root containing skill folders and manifest.sha256.json (default: this script's folder). All checks, including hashes, use this root.")
    parser.add_argument("--skill", choices=[*MODES, COMBINED])
    parser.add_argument("--report", type=Path, help="Optional JSON report; keep it outside the package to preserve the manifest.")
    args = parser.parse_args()
    if not (args.root / "manifest.sha256.json").is_file() and (args.root / "GAS-Agent-Skills").is_dir():
        print("Invalid --root: this appears to be the repository root. Use --root", args.root / "GAS-Agent-Skills")
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
