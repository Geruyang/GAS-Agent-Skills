#!/usr/bin/env python3
"""Offline evidence bookkeeping, Python 3.9+ standard library only.

This reads files and records; it never runs recorded commands, agents, or delivery.
Technical readiness is not an identity proof, governance decision, or permission.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys

SCHEMA = 1
KIND = "gas-candidate-manifest"
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
EXECUTIONS = {"NOT_RUN", "RUNNING", "COMPLETED"}
RESULTS = {"UNKNOWN", "PASS", "FAIL", "INCONCLUSIVE"}
BINDING = {"run_id", "task_id", "command_or_claim_id", "recipient", "epoch",
           "contract_version", "candidate_digest", "idempotency_key"}
SCOPE = "Local file and record consistency only; no governance or delivery authorization."


def require(condition, message):
    if not condition:
        raise ValueError(message)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest_bytes(data):
    return hashlib.sha256(data).hexdigest()


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        require(key not in result, "duplicate JSON key: " + key)
        result[key] = value
    return result


def reject_constant(value):
    raise ValueError("non-standard JSON constant: " + value)


def checked_path(path, allow_missing_leaf=False):
    """Reject links/junctions on the lexical path before resolving anything."""
    require(not str(path).replace("/", "\\").startswith(("\\\\?\\", "\\\\.\\", "\\??\\")),
            "Windows extended/device paths are not supported")
    path = Path(os.path.abspath(path))
    for part in reversed((path,) + tuple(path.parents)):
        try:
            details = part.lstat()
        except FileNotFoundError:
            if allow_missing_leaf and part == path:
                continue
            raise
        require(not stat.S_ISLNK(details.st_mode) and
                not (getattr(details, "st_file_attributes", 0) & 0x400),
                "symlink or reparse point is not allowed: " + str(part))
    # Resolving existing parents also removes 8.3 aliases before containment checks.
    return path.resolve(strict=not allow_missing_leaf)


def relative_name(value):
    require(isinstance(value, str) and bool(value), "empty/non-string relative path")
    parts = value.split("/")
    for part in parts:
        require(part not in ("", ".", "..") and not part.endswith((".", " ")) and
                not any(ord(c) < 32 or c in '\\:<>"|?*' for c in part),
                "unsafe relative path: " + value)
        require(not re.fullmatch(r"(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", part.split(".")[0]),
                "reserved path: " + value)
    return value


def read_regular(path):
    path = checked_path(path)
    before = path.lstat()
    require(stat.S_ISREG(before.st_mode), "not a regular file: " + str(path))
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        require((before.st_dev, before.st_ino) == (opened.st_dev, opened.st_ino),
                "file changed while opening: " + str(path))
        data = stream.read()
        finished = os.fstat(stream.fileno())
    after = checked_path(path).lstat()
    # Windows versions may expose different ctime meanings through stat/fstat.
    # Compare ctime only within the same API, while identity/size/mtime cross-check both.
    signature = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns)
    require(signature(before) == signature(finished) == signature(after) and
            before.st_ctime_ns == after.st_ctime_ns and opened.st_ctime_ns == finished.st_ctime_ns,
            "file changed while reading: " + str(path))
    return data


def parse_json(data):
    return json.loads(data.decode("utf-8-sig"), object_pairs_hook=unique_object,
                      parse_constant=reject_constant)


def load_json(path):
    return parse_json(read_regular(path))


def validate_entries(files, directories):
    require(isinstance(files, list) and isinstance(directories, list), "manifest arrays required")
    names = []
    for item in files:
        require(isinstance(item, dict) and set(item) == {"path", "size", "sha256"}, "bad file entry")
        names.append(relative_name(item["path"]))
        require(type(item["size"]) is int and item["size"] >= 0, "bad file size")
        require(isinstance(item["sha256"], str) and DIGEST.fullmatch(item["sha256"]), "bad file hash")
    directory_names = [relative_name(value) for value in directories]
    require(names == sorted(names) and directory_names == sorted(directory_names), "entries must be sorted")
    all_names = names + directory_names
    require(len({name.casefold() for name in all_names}) == len(all_names), "duplicate/aliased path")
    directory_set = set(directory_names)
    for name in all_names:
        parts = name.split("/")
        for index in range(1, len(parts)):
            require("/".join(parts[:index]) in directory_set, "missing or conflicting parent directory")


def scan_candidate(candidate):
    root = checked_path(candidate)
    require(root.is_dir(), "candidate must be a directory")
    files, directories = [], []

    def visit(folder):
        before = folder.stat()
        entries = sorted(folder.iterdir(), key=lambda p: p.name)
        for path in entries:
            checked_path(path)
            name = relative_name(path.relative_to(root).as_posix())
            details = path.lstat()
            if stat.S_ISDIR(details.st_mode):
                directories.append(name)
                visit(path)
            else:
                data = read_regular(path)
                files.append({"path": name, "size": len(data), "sha256": digest_bytes(data)})
        after = folder.stat()
        require((before.st_mtime_ns, before.st_ctime_ns) == (after.st_mtime_ns, after.st_ctime_ns),
                "directory changed during scan: " + str(folder))

    visit(root)
    files.sort(key=lambda entry: entry["path"])
    directories.sort()
    validate_entries(files, directories)
    payload = {"schema_version": SCHEMA, "kind": KIND, "files": files, "directories": directories}
    return dict(payload, candidate_digest=digest_bytes(canonical(payload)))


def candidate_snapshot(candidate):
    first = scan_candidate(candidate)
    require(scan_candidate(candidate) == first, "candidate changed during snapshot readback")
    return first


def outside_candidate(candidate, path, allow_missing=False):
    root = checked_path(candidate)
    target = checked_path(path, allow_missing_leaf=allow_missing)
    require(target != root and root not in target.parents, "output/manifest must be outside candidate")
    return target


def make_manifest(candidate, output):
    target = outside_candidate(candidate, output, allow_missing=True)
    manifest = candidate_snapshot(candidate)
    data = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if target.exists():
        require(read_regular(target) == data, "existing different output will not be overwritten")
    else:
        with target.open("xb") as stream:
            stream.write(data)
    return {"ok": True, "candidate_digest": manifest["candidate_digest"], "manifest": str(target),
            "file_count": len(manifest["files"]), "scope": SCOPE}


def read_manifest(candidate, path):
    outside_candidate(candidate, path)
    manifest = load_json(path)
    require(isinstance(manifest, dict) and set(manifest) ==
            {"schema_version", "kind", "files", "directories", "candidate_digest"}, "bad manifest fields")
    require(type(manifest["schema_version"]) is int and manifest["schema_version"] == SCHEMA and
            manifest["kind"] == KIND, "unsupported manifest schema")
    validate_entries(manifest["files"], manifest["directories"])
    payload = {key: value for key, value in manifest.items() if key != "candidate_digest"}
    require(manifest["candidate_digest"] == digest_bytes(canonical(payload)), "manifest digest mismatch")
    return manifest


def verify_candidate(candidate, manifest_path):
    expected = read_manifest(candidate, manifest_path)
    current = candidate_snapshot(candidate)
    require(read_manifest(candidate, manifest_path) == expected, "manifest changed during verification")
    old = {entry["path"]: entry for entry in expected["files"]}
    new = {entry["path"]: entry for entry in current["files"]}
    return {"ok": current == expected, "candidate_digest": expected["candidate_digest"],
            "observed_candidate_digest": current["candidate_digest"],
            "changed": sorted(name for name in old.keys() & new.keys() if old[name] != new[name]),
            "missing": sorted(old.keys() - new.keys()), "added": sorted(new.keys() - old.keys()),
            "directories_added": sorted(set(current["directories"]) - set(expected["directories"])),
            "directories_missing": sorted(set(expected["directories"]) - set(current["directories"])),
            "scope": SCOPE}


def validate_graph(graph):
    require(isinstance(graph, dict), "stage_dependencies must be an object")
    nodes, edges = graph.get("nodes"), graph.get("edges")
    require(isinstance(nodes, list) and all(isinstance(node, str) and node.strip() for node in nodes),
            "dependency nodes must be nonempty strings")
    require(len(nodes) == len(set(nodes)), "duplicate dependency nodes")
    require(isinstance(edges, list), "dependency edges must be an array")
    followers = {node: [] for node in nodes}
    degree = dict.fromkeys(nodes, 0)
    unique = set()
    for edge in edges:
        require(isinstance(edge, dict) and set(edge) == {"from", "to"}, "bad dependency edge")
        source, target = edge["from"], edge["to"]
        require(isinstance(source, str) and isinstance(target, str) and source in degree and target in degree,
                "dependency edge endpoint missing")
        require(source != target and (source, target) not in unique, "self/duplicate dependency edge")
        unique.add((source, target))
        followers[source].append(target)
        degree[target] += 1
    pending = [node for node, count in degree.items() if count == 0]
    visited = 0
    while pending:
        visited += 1
        for target in followers[pending.pop()]:
            degree[target] -= 1
            if degree[target] == 0:
                pending.append(target)
    require(visited == len(nodes), "cyclic stage dependencies")


def assess(candidate, manifest_path, record_path):
    verification = verify_candidate(candidate, manifest_path)
    record_path = checked_path(record_path)
    record_bytes = read_regular(record_path)
    record = parse_json(record_bytes)
    require(isinstance(record, dict), "runtime record must be an object")
    issues = []
    expected_digest = verification["candidate_digest"]

    def need(condition, message):
        if not condition:
            issues.append(message)
        return bool(condition)

    need(verification["ok"], "candidate differs from manifest")
    need(type(record.get("schema_version")) is int and record.get("schema_version") == SCHEMA,
         "unsupported runtime schema")
    need(record.get("example_only") is False, "example or unspecified record is not execution evidence")
    binding = record.get("binding")
    if need(isinstance(binding, dict), "binding must be an object"):
        need(BINDING <= set(binding), "incomplete binding")
        for key in BINDING - {"epoch"}:
            need(isinstance(binding.get(key), str) and bool(binding.get(key, "").strip()), "missing binding: " + key)
        epoch = binding.get("epoch")
        need((type(epoch) is int and epoch >= 0) or (isinstance(epoch, str) and bool(epoch.strip())), "missing epoch")
        need(binding.get("candidate_digest") == expected_digest, "candidate binding mismatch")

    evidence, evidence_digests, evidence_paths = {}, {}, {}
    entries = record.get("evidence", [])
    if need(isinstance(entries, list), "evidence must be an array"):
        for entry in entries:
            try:
                require(isinstance(entry, dict), "evidence must be an object")
                name = entry.get("id")
                require(isinstance(name, str) and bool(name.strip()) and name not in evidence, "bad/duplicate evidence id")
                evidence[name] = None
                source_digest = entry.get("input_digest")
                require(isinstance(source_digest, str) and DIGEST.fullmatch(source_digest), "bad evidence input digest: " + name)
                path = record_path.parent / relative_name(entry.get("path"))
                data = read_regular(path)
                require(bool(data), "empty evidence: " + name)
                require(entry.get("sha256") == digest_bytes(data), "evidence hash mismatch: " + name)
                evidence[name] = data
                evidence_digests[name] = source_digest
                evidence_paths[name] = path
            except (OSError, ValueError, TypeError) as exc:
                issues.append("invalid evidence: " + str(exc))

    def references(refs, label, input_digest=expected_digest):
        return need(isinstance(refs, list) and bool(refs) and
                    all(isinstance(ref, str) and evidence.get(ref) is not None and
                        evidence_digests.get(ref) == input_digest for ref in refs),
                    "missing or invalid evidence refs: " + label)

    def check_list(checks, label, require_mandatory=False, preflight=False):
        if not need(isinstance(checks, list), label + " must be an array"):
            return
        if require_mandatory:
            need(any(isinstance(check, dict) and check.get("required") is True for check in checks),
                 "at least one explicitly required check is needed")
        ids = set()
        for check in checks:
            if not need(isinstance(check, dict), "check must be an object"):
                continue
            name = check.get("id")
            if not need(isinstance(name, str) and bool(name.strip()), "check id required"):
                continue
            need(name not in ids, "duplicate check id: " + name)
            ids.add(name)
            execution, result = check.get("execution"), check.get("result")
            need(isinstance(execution, str) and execution in EXECUTIONS, "bad execution: " + name)
            need(isinstance(result, str) and result in RESULTS, "bad result: " + name)
            need(type(check.get("required")) is bool, "required must be boolean: " + name)
            source_digest = check.get("input_digest")
            source_valid = isinstance(source_digest, str) and bool(DIGEST.fullmatch(source_digest))
            need(source_valid, "invalid check input digest: " + name)
            if not preflight:
                need(source_digest == expected_digest, "check candidate mismatch: " + name)
            elif source_digest != expected_digest:
                applicability = check.get("applicability")
                if need(isinstance(applicability, dict), "source preflight needs current applicability: " + name):
                    need(applicability.get("source_input_digest") == source_digest and
                         applicability.get("target_candidate_digest") == expected_digest,
                         "preflight applicability digest mismatch: " + name)
                    for key in ("environment", "coverage", "reviewer", "reason"):
                        need(isinstance(applicability.get(key), str) and applicability[key].strip(),
                             "missing applicability " + key + ": " + name)
                    references(applicability.get("evidence_refs"), "preflight applicability: " + name)
            need(execution == "COMPLETED" or result == "UNKNOWN", "unexecuted check claims result: " + name)
            if check.get("required") is True:
                need(execution == "COMPLETED" and result == "PASS", "required check not completed PASS: " + name)
            if execution == "COMPLETED":
                references(check.get("evidence_refs"), name, source_digest if preflight else expected_digest)
            if preflight and execution == "COMPLETED" and result == "PASS":
                ref = check.get("actual_output_ref")
                actual = evidence.get(ref) if isinstance(ref, str) else None
                assertion = check.get("output_assertion", {"kind": "utf8_exact", "expected": check.get("expected_output")})
                output_matches = False
                if isinstance(assertion, dict) and isinstance(actual, bytes):
                    wanted = assertion.get("expected")
                    if assertion.get("kind") == "utf8_exact":
                        output_matches = isinstance(wanted, str) and bool(wanted) and actual == wanted.encode("utf-8")
                    elif assertion.get("kind") == "sha256":
                        output_matches = isinstance(wanted, str) and bool(DIGEST.fullmatch(wanted)) and digest_bytes(actual) == wanted
                need(output_matches, "preflight output assertion failed: " + name)
                need(isinstance(check.get("evidence_refs"), list) and ref in check["evidence_refs"],
                     "preflight output must be referenced: " + name)

    check_list(record.get("checks"), "checks", require_mandatory=True)
    preflight = record.get("critical_capability_preflight", [])
    check_list(preflight, "critical_capability_preflight", preflight=True)
    if preflight == []:
        applicability = record.get("preflight_applicability")
        need(isinstance(applicability, dict) and applicability.get("status") == "NOT_APPLICABLE" and
             all(isinstance(applicability.get(key), str) and applicability[key].strip()
                 for key in ("reason", "contract_ref")), "empty preflight needs explicit non-applicability basis")
    if "stage_dependencies" in record:
        try:
            validate_graph(record["stage_dependencies"])
        except ValueError as exc:
            issues.append(str(exc))
    lifecycle = record.get("lifecycle", {})
    if need(isinstance(lifecycle, dict), "lifecycle must be an object"):
        preceding_completed = True
        for stage in ("sent", "received", "started", "completed"):
            event = lifecycle.get(stage, {"execution": "NOT_RUN"})
            if not need(isinstance(event, dict), "bad lifecycle stage: " + stage):
                preceding_completed = False
                continue
            execution = event.get("execution")
            need(execution in ("NOT_RUN", "COMPLETED"), "bad stage execution: " + stage)
            if execution == "COMPLETED":
                need(preceding_completed, "out-of-order lifecycle stage: " + stage)
                need(canonical(event.get("binding")) == canonical(binding), "receipt binding mismatch: " + stage)
                references([event.get("host_receipt_ref")], "host receipt for " + stage)
            else:
                preceding_completed = False

    checkpoint = record.get("checkpoint", {})
    if need(isinstance(checkpoint, dict), "checkpoint must be an object"):
        side_effect = checkpoint.get("side_effect_status", "UNKNOWN")
        need(side_effect in ("NONE", "UNKNOWN", "CONFIRMED_NOT_APPLIED", "CONFIRMED_APPLIED"), "bad side effect status")
        need(type(checkpoint.get("retry_requested")) is bool, "retry_requested must be boolean")
        if checkpoint.get("retry_requested") is True:
            need(side_effect in ("NONE", "CONFIRMED_NOT_APPLIED"), "retry blocked pending side-effect reconciliation")
            if side_effect != "NONE":
                need(checkpoint.get("reconciliation_execution") == "COMPLETED", "reconciliation has not completed")
                references(checkpoint.get("reconciliation_evidence_refs"), "side-effect reconciliation")
    delivery = record.get("delivery")
    if need(isinstance(delivery, dict), "delivery must be a separate object"):
        execution, result = delivery.get("execution"), delivery.get("result")
        need(isinstance(execution, str) and execution in EXECUTIONS, "bad delivery execution")
        need(isinstance(result, str) and result in RESULTS, "bad delivery result")
        need(execution == "COMPLETED" or result == "UNKNOWN", "unexecuted delivery claims a result")
        if execution == "COMPLETED":
            references(delivery.get("evidence_refs"), "delivery")
    # Read back the inputs used in the decision. This catches ordinary in-run
    # drift; it is not a filesystem lock or protection against hostile writers.
    try:
        for name, path in evidence_paths.items():
            need(read_regular(path) == evidence[name], "evidence changed during assessment: " + name)
        need(read_regular(record_path) == record_bytes, "runtime record changed during assessment")
        final_verification = verify_candidate(candidate, manifest_path)
        need(final_verification["ok"] and final_verification["candidate_digest"] == expected_digest,
             "candidate or manifest changed during assessment")
        if not final_verification["ok"]:
            verification = final_verification
    except (OSError, ValueError, TypeError) as exc:
        issues.append("assessment readback failed: " + str(exc))
    return {"technical_evidence_ready": not issues, "issues": issues, "verification": verification,
            "checks": record.get("checks"), "risk_acceptance": record.get("risk_acceptance"),
            "human_adjudication": record.get("human_adjudication"), "delivery": record.get("delivery"), "scope": SCOPE}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for command in ("manifest", "verify", "assess"):
        sub = commands.add_parser(command)
        sub.add_argument("--candidate", type=Path, required=True)
        if command == "manifest":
            sub.add_argument("--output", type=Path, required=True)
        else:
            sub.add_argument("--manifest", type=Path, required=True)
        if command == "assess":
            sub.add_argument("--record", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "manifest":
            outcome = make_manifest(args.candidate, args.output)
        elif args.command == "verify":
            outcome = verify_candidate(args.candidate, args.manifest)
        else:
            outcome = assess(args.candidate, args.manifest, args.record)
        code = 0 if outcome.get("ok", outcome.get("technical_evidence_ready", False)) else 1
    except (OSError, ValueError, TypeError, UnicodeError) as exc:
        outcome = {"ok": False, "error": str(exc), "scope": SCOPE}
        code = 2
    print(json.dumps(outcome, ensure_ascii=True, indent=2, allow_nan=False))
    return code


if __name__ == "__main__":
    sys.exit(main())
