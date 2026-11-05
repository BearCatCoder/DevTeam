#!/usr/bin/env python3
"""Portable DevTeam v1 evidence, scope audit and checkpoint helpers (stdlib only)."""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import tempfile

VERSION = 1
ROLES = {"devteam-" + r for r in (
    "architect", "back-end-dev-engineer", "front-end-dev-engineer",
    "database-engineer", "dev-admin", "documentation-writer", "product-owner",
    "qa-engineer", "security-reviewer")}
OUTCOMES = {"passed", "failed", "blocked", "not_run", "inconclusive"}
STATE_ID = re.compile(r"^(head:[0-9a-f]{7,40};dirty:(unknown|true|false)|none|[0-9a-f]{64})$")


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def path_name(value):
    require(isinstance(value, str) and value and "\\" not in value,
            "paths must be nonempty POSIX relative paths")
    p = PurePosixPath(value)
    require(bool(p.parts) and not p.is_absolute() and ".." not in p.parts and str(p) == value
            and p.parts[0] != ".git", "unsafe or noncanonical path: " + value)
    return value


def scope_valid(scope):
    require(isinstance(scope, dict), "scope must be an object")
    for key in ("allowed", "prohibited", "section_review"):
        require(isinstance(scope.get(key), list), "scope missing " + key)
        for p in scope[key]:
            path_name(p)
    require(isinstance(scope.get("owners"), dict), "scope needs owners")
    for p in scope["allowed"]:
        require(scope["owners"].get(p) in ROLES, "one specialist owner required: " + p)
    require(not set(scope["allowed"]) & set(scope["prohibited"]), "conflicting scope")


def snapshot(root):
    """Hash all working files, including ignored/untracked, without following links."""
    root = Path(root).resolve()
    files = {}
    def visit(directory):
        for p in sorted(directory.iterdir()):
            if p == root / ".git":
                continue
            s = p.lstat()
            name = p.relative_to(root).as_posix()
            if stat.S_ISLNK(s.st_mode):
                files[name] = {"kind": "symlink", "value": os.readlink(p)}
            elif stat.S_ISDIR(s.st_mode):
                visit(p)
            elif stat.S_ISREG(s.st_mode):
                files[name] = {"kind": "file", "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                               "mode": stat.S_IMODE(s.st_mode)}
            else:
                raise ValueError("unsupported special file: " + name)
    visit(root)
    def git(*args):
        r = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
        return r.stdout.hex() if r.returncode == 0 else None
    state = {"version": VERSION, "root": str(root), "files": files,
             "head": git("rev-parse", "HEAD"), "index": git("ls-files", "--stage", "-z"),
             "user_status": git("status", "--porcelain=v1", "-z", "--untracked-files=all")}
    state["state_id"] = digest({k: state[k] for k in ("files", "head", "index")})
    return state


def audit(before, after, scope):
    scope_valid(scope)
    require(before["version"] == after["version"] == VERSION, "unsupported snapshot version")
    require(before["root"] == after["root"], "repository identity mismatch")
    changed = sorted(p for p in before["files"].keys() | after["files"].keys()
                     if before["files"].get(p) != after["files"].get(p))
    violations = sorted(set(changed) - set(scope["allowed"]) | (set(changed) & set(scope["prohibited"])))
    sections = sorted(set(changed) & set(scope["section_review"]))
    metadata = before["head"] != after["head"] or before["index"] != after["index"]
    return {"status": "blocked" if violations or sections or metadata else "passed",
            "changed": changed, "violations": violations, "section_review_required": sections,
            "git_metadata_changed": metadata, "state_id": after["state_id"]}


def validate_handoff(h, assignment=None):
    require(isinstance(h, dict) and h.get("version") == VERSION, "unsupported handoff version")
    for key in ("task_id", "summary", "state_id"):
        require(isinstance(h.get(key), str) and h[key], "missing " + key)
    require(STATE_ID.fullmatch(h["state_id"]), "invalid state_id format")
    require(h.get("role") in ROLES, "unknown role")
    require(h.get("mode") in {"analyze", "implement", "test", "document"}, "invalid mode")
    require(h.get("status") in {"done", "blocked", "needs-owner"}, "invalid status")
    scope_valid(h.get("scope"))
    if assignment is not None:
        for key in ("task_id", "role", "mode", "scope", "dependencies", "contracts"):
            require(h.get(key) == assignment.get(key), "handoff differs from approved assignment: " + key)
    for key in ("reviewed", "changed", "dependencies", "contracts", "findings", "risks", "limitations", "criteria", "checks"):
        require(isinstance(h.get(key), list), "missing list: " + key)
    require("next_owner" in h and (h["next_owner"] is None or h["next_owner"] in ROLES), "invalid/missing next_owner")
    for p in h["reviewed"] + h["changed"]:
        path_name(p)
    require(set(h["changed"]) <= set(h["scope"]["allowed"]), "changed paths exceed scope")
    require(all(h["scope"]["owners"][p] == h["role"] for p in h["changed"]), "changed another owner's file")
    readonly = ROLES - {"devteam-back-end-dev-engineer", "devteam-front-end-dev-engineer",
                       "devteam-database-engineer", "devteam-qa-engineer", "devteam-documentation-writer"}
    require(not h["changed"] or h["role"] not in readonly, "read-only role changed files")
    ids = set()
    for c in h["checks"]:
        require(isinstance(c, dict) and isinstance(c.get("id"), str) and c["id"] not in ids, "invalid/duplicate check id")
        ids.add(c["id"])
        require(c.get("outcome") in OUTCOMES, "invalid check outcome")
        require(c.get("kind") in {"self_check", "independent_qa", "review"}, "invalid evidence kind")
        require(c["kind"] != "independent_qa" or h["role"] == "devteam-qa-engineer", "QA evidence requires QA role")
        require(isinstance(c.get("command"), str) and isinstance(c.get("evidence"), list), "check needs command and evidence list")
        require(c.get("state_id") == h["state_id"], "stale check state")
        code = c.get("exit_code")
        require(code is None or type(code) is int, "invalid exit code")
        if c["outcome"] == "passed":
            require(bool(c["evidence"]) and all(isinstance(e, str) and e.strip() for e in c["evidence"]), "passed check lacks evidence")
            require(code == 0 if c["command"] else c["kind"] == "review" and code is None,
                    "passed command requires exit 0; manual evidence must be review")
        if c["outcome"] in {"not_run", "blocked"}:
            require(code is None, "unrun check cannot have exit code")
    criterion_ids = set()
    for c in h["criteria"]:
        require(isinstance(c, dict) and isinstance(c.get("id"), str) and c["id"] not in criterion_ids, "invalid/duplicate criterion")
        criterion_ids.add(c["id"])
        require(c.get("outcome") in OUTCOMES and isinstance(c.get("checks"), list), "invalid criterion")
        require(set(c["checks"]) <= ids, "unknown check reference")
        if c["outcome"] == "passed":
            require(bool(c["checks"]) and all(x["outcome"] == "passed" for x in h["checks"] if x["id"] in c["checks"]), "unsupported criterion pass")
    for f in h["findings"]:
        require(isinstance(f, dict) and f.get("severity") in {"info", "low", "medium", "high", "critical"}
                and f.get("evidence") and f.get("summary"), "finding needs severity, summary, evidence")
    return h


def gates(packet, evidence_root=None):
    """Fail closed; supplied evidence remains subject to independent authenticity review."""
    require(packet.get("version") == VERSION, "unsupported gate version")
    assignments = packet["assignments"]
    require(isinstance(assignments, dict), "approved assignments required")
    handoffs = []
    for h in packet["handoffs"]:
        require(h["task_id"] in assignments, "handoff has no approved assignment")
        handoffs.append(validate_handoff(h, assignments[h["task_id"]]))
    require(len({h["task_id"] for h in handoffs}) == len(handoffs), "duplicate final handoffs")
    require({h["task_id"] for h in handoffs} == set(assignments), "missing assignment handoff")
    require(packet["criteria"] and len(set(packet["criteria"])) == len(packet["criteria"]), "criteria required")
    current = packet["state_id"]
    usable = [h for h in handoffs if h["state_id"] == current and h["status"] == "done"]
    engineers = {"devteam-back-end-dev-engineer", "devteam-front-end-dev-engineer", "devteam-database-engineer"}
    implemented = any(h["mode"] == "implement" and h["role"] in engineers for h in usable)
    qa = {c["id"] for h in usable if h["role"] == "devteam-qa-engineer" for c in h["criteria"]
          if c["outcome"] == "passed" and all(next(x for x in h["checks"] if x["id"] == i)["kind"] == "independent_qa" for i in c["checks"])}
    def review(key, role):
        decision = packet[key]
        require(type(decision.get("required")) is bool and bool(decision.get("reason")), key + " requires applicability reason")
        return not decision["required"] or any(h["role"] == role and h["checks"] and
            all(c["outcome"] == "passed" for c in h["checks"]) for h in usable)
    result = {"implemented": implemented, "qa_verified": set(packet["criteria"]) <= qa,
              "security_reviewed_when_applicable": review("security", "devteam-security-reviewer"),
              "documented_when_applicable": review("documentation", "devteam-documentation-writer")}
    evidence_ok = evidence_root is not None
    for h in usable:
        for check in h["checks"]:
            if check["outcome"] != "passed":
                continue
            for reference in check["evidence"]:
                entry = packet.get("evidence", {}).get(reference)
                if not entry or evidence_root is None:
                    evidence_ok = False
                    continue
                base = Path(evidence_root).resolve()
                artifact = base / path_name(entry["path"])
                require(base in artifact.resolve().parents, "evidence escapes evidence root")
                evidence_ok = evidence_ok and artifact.is_file() and hashlib.sha256(artifact.read_bytes()).hexdigest() == entry["sha256"]
    result["evidence_artifacts_verified"] = evidence_ok
    result["accepted"] = all(result.values()) and packet["audit"]["status"] == "passed" and packet["audit"]["state_id"] == current and not packet["blockers"] and not any(h["findings"] or h["status"] != "done" for h in handoffs)
    return result


def atomic_json(path, data):
    path = Path(path)
    require(not path.is_symlink(), "refusing symlink output")
    fd, temp = tempfile.mkstemp(prefix=".devteam-", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(data, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def checkpoint_valid(c):
    require(c.get("version") == VERSION and c.get("task_id"), "invalid checkpoint identity/version")
    scope_valid(c["scope"])
    for key in ("dependencies", "criteria", "handoffs", "pending_reviews", "blockers", "completed_mutations"):
        require(isinstance(c.get(key), list), "checkpoint missing " + key)
    require(c.get("status") in {"active", "blocked", "done"}, "invalid checkpoint status")
    require(c["baseline"]["version"] == VERSION and c["current"]["version"] == VERSION, "invalid checkpoint snapshots")
    require(c["baseline"]["root"] == c["current"]["root"], "checkpoint repository identity mismatch")
    for h in c["handoffs"]:
        validate_handoff(h)
    return c


def reconcile(c, now):
    checkpoint_valid(c)
    delta = audit(c["current"], now, c["scope"])
    stale = c["current"]["state_id"] != now["state_id"]
    return {"version": VERSION, "task_id": c["task_id"], "status": "blocked" if stale else "ready",
            "delta": delta, "stale_evidence": stale, "rerun_required": stale,
            "completed_mutations": c["completed_mutations"],
            "instruction": "Reconcile all drift with owners; preserve user changes. Never replay completed mutations. Confirm remote state before any authorized retry."}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("operation", choices=["snapshot", "audit", "handoff", "gates", "checkpoint", "resume"])
    p.add_argument("--root", type=Path, default=Path.cwd())
    p.add_argument("--input", type=Path)
    p.add_argument("--scope", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--evidence-root", type=Path, help="Trusted local evidence artifacts for acceptance gates")
    a = p.parse_args()
    def load(path):
        require(path is not None, "input file required")
        return json.loads(path.read_text())
    try:
        if a.operation == "snapshot":
            result = snapshot(a.root)
        elif a.operation == "audit":
            result = audit(load(a.input), snapshot(a.root), load(a.scope))
        elif a.operation == "handoff":
            validate_handoff(load(a.input), load(a.scope) if a.scope else None)
            result = {"status": "passed"}
        elif a.operation == "gates":
            result = gates(load(a.input), a.evidence_root)
        elif a.operation == "checkpoint":
            result = checkpoint_valid(load(a.input))
        else:
            result = reconcile(load(a.input), snapshot(a.root))
        if a.output:
            require(a.root.resolve() not in a.output.resolve().parents, "store workflow outputs outside audited root")
            atomic_json(a.output, result)
        print(json.dumps(result, indent=2))
        return 1 if result.get("status") == "blocked" or result.get("accepted") is False else 0
    except (ValueError, KeyError, TypeError, AttributeError, IndexError, OSError) as e:
        print(json.dumps({"status": "blocked", "error": str(e)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
