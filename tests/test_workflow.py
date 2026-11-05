"""Offline deterministic audit, evidence and reconciliation regression tests."""
import copy
import importlib.util
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CURRENT = "head:abc1234;dirty:unknown"
sys.path.insert(0, str(ROOT / "scripts"))
import workflow as w
import policy
import isolation


def handoff(role="devteam-back-end-dev-engineer", kind="self_check"):
    h = json.loads((ROOT / "examples" / "handoff.json").read_text())
    h.update(task_id=role, role=role, status="done", state_id=CURRENT, mode="test" if kind == "independent_qa" else "implement")
    h["checks"][0].update(kind=kind, state_id=CURRENT, outcome="passed", exit_code=0, evidence=["checks.log:1"])
    h["criteria"][0]["outcome"] = "passed"
    h["limitations"] = []
    return h


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "backend.py").write_text("user changes\n")
        (self.root / "note").write_text("untracked user content\n")
        self.scope = {"allowed": ["backend.py"], "prohibited": ["note"], "section_review": [],
                      "owners": {"backend.py": "devteam-back-end-dev-engineer"}}
        self.before = w.snapshot(self.root)

    def test_baseline_does_not_flag_existing_user_edits(self):
        self.assertEqual(w.audit(self.before, w.snapshot(self.root), self.scope)["changed"], [])
        (self.root / "backend.py").write_text("user changes\nfix\n")
        self.assertEqual(w.audit(self.before, w.snapshot(self.root), self.scope)["status"], "passed")

    def test_untracked_deletion_and_mode_changes_are_audited_without_revert(self):
        (self.root / "new").write_text("unexpected")
        (self.root / "note").unlink()
        (self.root / "backend.py").chmod(0o755)
        result = w.audit(self.before, w.snapshot(self.root), self.scope)
        self.assertEqual(result["violations"], ["new", "note"])
        self.assertIn("backend.py", result["changed"])
        self.assertEqual((self.root / "new").read_text(), "unexpected")
        self.assertFalse((self.root / "note").exists())

    def test_symlinks_not_followed(self):
        (self.root / "link").symlink_to("/nonexistent")
        self.assertEqual(w.snapshot(self.root)["files"]["link"]["kind"], "symlink")
        self.assertEqual(w.audit(self.before, w.snapshot(self.root), self.scope)["violations"], ["link"])

    def test_section_review_fails_closed(self):
        self.scope["section_review"] = ["backend.py"]
        (self.root / "backend.py").write_text("changed")
        self.assertEqual(w.audit(self.before, w.snapshot(self.root), self.scope)["status"], "blocked")

    def test_git_metadata_and_repository_identity(self):
        after = copy.deepcopy(self.before)
        after["index"] = "changed-index"
        self.assertTrue(w.audit(self.before, after, self.scope)["git_metadata_changed"])
        after["root"] = "/different"
        with self.assertRaises(ValueError):
            w.audit(self.before, after, self.scope)

    def test_scope_requires_owner_and_canonical_paths(self):
        for path in (".", "../escape", "/absolute", "./noncanonical", ".git/config"):
            bad = copy.deepcopy(self.scope)
            bad["allowed"] = [path]
            with self.assertRaises(ValueError):
                w.scope_valid(bad)
        self.scope["owners"] = {}
        with self.assertRaises(ValueError):
            w.scope_valid(self.scope)

    def test_resume_is_idempotent_and_invalidates_evidence_on_any_drift(self):
        c = {"version": 1, "task_id": "T1", "scope": self.scope, "baseline": self.before,
             "current": self.before, "status": "active", "dependencies": [], "criteria": ["AC-1"],
             "handoffs": [], "pending_reviews": ["QA"], "blockers": [], "completed_mutations": ["fix-1"]}
        self.assertEqual(w.reconcile(c, self.before)["status"], "ready")
        (self.root / "note").write_text("new user edit")
        now = w.snapshot(self.root)
        result = w.reconcile(c, now)
        self.assertEqual(result, w.reconcile(c, now))
        self.assertTrue(result["stale_evidence"])
        self.assertEqual(result["completed_mutations"], ["fix-1"])
        self.assertEqual((self.root / "note").read_text(), "new user edit")

    def test_atomic_checkpoint_refuses_symlink_and_roundtrips(self):
        out = self.root / "checkpoint.json"
        w.atomic_json(out, {"version": 1})
        self.assertEqual(json.loads(out.read_text()), {"version": 1})
        out.unlink()
        out.symlink_to(self.root / "note")
        with self.assertRaises(ValueError):
            w.atomic_json(out, {})
        self.assertEqual((self.root / "note").read_text(), "untracked user content\n")

    def test_handoff_rejects_fabricated_pass_and_engineer_qa(self):
        w.validate_handoff(handoff())
        for changes in ({"exit_code": 7}, {"evidence": []}, {"outcome": "not_run"}, {"state_id": "head:def5678;dirty:unknown"}, {"kind": "independent_qa"}):
            h = handoff()
            h["checks"][0].update(changes)
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                w.validate_handoff(h)

    def test_handoff_rejects_wrong_owner_and_missing_criterion_evidence(self):
        h = handoff()
        h["changed"] = ["frontend.html"]
        with self.assertRaises(ValueError):
            w.validate_handoff(h)

    def test_read_only_analyze_handoff_with_packet_state_id_is_done(self):
        h = json.loads((ROOT / "examples" / "handoff.json").read_text())
        h.update(role="devteam-architect", mode="analyze", status="done", changed=[],
                 state_id="head:abc1234;dirty:unknown", checks=[], criteria=[], limitations=[],
                 summary="Design complete; no files changed.")
        h["scope"] = {"allowed": [], "prohibited": [], "section_review": [], "owners": {}}
        w.validate_handoff(h)
        for bad in ("unavailable", "head:XYZ;dirty:unknown", "head:abc1234;dirty:maybe"):
            h["state_id"] = bad
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                w.validate_handoff(h)

    def test_approved_assignment_cannot_be_expanded_by_handoff(self):
        h = handoff()
        approval = copy.deepcopy(h)
        h["scope"]["allowed"].append("frontend.html")
        h["scope"]["owners"]["frontend.html"] = h["role"]
        with self.assertRaises(ValueError):
            w.validate_handoff(h, approval)
        h = handoff()
        h["criteria"][0]["checks"] = []
        with self.assertRaises(ValueError):
            w.validate_handoff(h)

    def test_gates_require_independent_current_qa_and_risk_decisions(self):
        packet = {"version": 1, "handoffs": [handoff()], "criteria": ["AC-1"], "state_id": CURRENT,
                  "assignments": {h["task_id"]: h for h in [handoff(), handoff("devteam-qa-engineer", "independent_qa")]},
                  "security": {"required": False, "reason": "arithmetic-only"},
                  "documentation": {"required": False, "reason": "no documented contract change"},
                  "audit": {"status": "passed", "state_id": CURRENT}, "blockers": []}
        with self.assertRaisesRegex(ValueError, "missing assignment handoff"):
            w.gates(packet)
        packet["handoffs"].append(handoff("devteam-qa-engineer", "independent_qa"))
        self.assertFalse(w.gates(packet)["accepted"])
        (self.root / "checks.log").write_text("independent test passed\n")
        packet["evidence"] = {"checks.log:1": {"path": "checks.log", "sha256": hashlib.sha256((self.root / "checks.log").read_bytes()).hexdigest()}}
        self.assertTrue(w.gates(packet, self.root)["accepted"])
        (self.root / "checks.log").write_text("tampered evidence")
        self.assertFalse(w.gates(packet, self.root)["accepted"])
        packet["state_id"] = "head:def5678;dirty:unknown"
        self.assertFalse(w.gates(packet)["accepted"])
        packet["security"]["reason"] = ""
        with self.assertRaises(ValueError):
            w.gates(packet)

    def test_policy_generation_is_idempotent_and_self_contained(self):
        canonical = (ROOT / "policy" / "reliability-v1.md").read_text()
        agents = list((ROOT / ".opencode" / "agents").glob("*.md"))
        self.assertEqual(len(agents), 10)
        for p in agents:
            text = p.read_text()
            self.assertEqual(policy.render(text, policy.block_for(p.stem, canonical)), text, p.name)
            body = text.split("---", 2)[2].split(policy.START, 1)[0]
            # Generated block is the only collaboration copy; files open with role.
            self.assertNotIn("collaboration is permitted", body, p.name)
            self.assertEqual(text.count("GitHub/Jira:"), 1, p.name)
            heading, _, rest = body.strip().partition("\n\n")
            self.assertTrue(heading.startswith("# ") and "\n" not in heading, p.name)
            self.assertFalse(rest.startswith(("#", "<!--")), p.name)

    def test_policy_blocks_are_rendered_per_role(self):
        canonical = (ROOT / "policy" / "reliability-v1.md").read_text()
        block = {name: policy.block_for(name, canonical) for name in
                 ("DevTeam", "devteam-product-owner", "devteam-back-end-dev-engineer", "devteam-documentation-writer")}
        self.assertRegex(block["DevTeam"], r"\bgates\b")
        self.assertIn("Checkpoints", block["DevTeam"])
        self.assertNotIn("Edit only the packet", block["DevTeam"])
        for name in ("devteam-product-owner", "devteam-back-end-dev-engineer", "devteam-documentation-writer"):
            self.assertNotRegex(block[name], r"(?i)\bgates\b", name)
            self.assertNotIn("Checkpoints", block[name], name)
            self.assertIn("untrusted task", block[name], name)
            self.assertIn("state_id", block[name], name)
        self.assertNotIn("Edit only the packet", block["devteam-product-owner"])
        self.assertIn("Edit only the packet", block["devteam-back-end-dev-engineer"])
        self.assertIn("Edit only the packet", block["devteam-documentation-writer"])

    def test_specialists_return_needs_owner_instead_of_asking(self):
        rule = "return `status: needs-owner` with the exact question in `limitations`"
        for p in (ROOT / ".opencode" / "agents").glob("*.md"):
            text = " ".join(p.read_text().split())
            if p.stem == "DevTeam":
                self.assertNotIn(rule, text)
            else:
                self.assertIn(rule, text, p.name)
                self.assertNotRegex(text, r"(?i)\bask (when|for|the user)\b", p.name)

    def test_prompt_word_budgets_and_tiers(self):
        for p in (ROOT / ".opencode" / "agents").glob("*.md"):
            limit = 1400 if p.stem == "DevTeam" else 650
            self.assertLessEqual(len(p.read_text().split()), limit, p.name)
        coordinator = (ROOT / ".opencode" / "agents" / "DevTeam.md").read_text()
        for tier in ("**Direct answer:**", "**Small:**", "**Medium:**", "**Large:**", "State the tier chosen"):
            self.assertIn(tier, coordinator)

    def test_policy_section_word_limits(self):
        limits = {"all": [70, 90, 60], "writers": [90]}
        seen = {"all": 0, "writers": 0}
        for audience, text in policy.sections((ROOT / "policy" / "reliability-v1.md").read_text()):
            if audience in limits:
                self.assertLessEqual(len(text.split()), limits[audience][seen[audience]], text[:40])
                seen[audience] += 1

    def test_isolation_overlay_denies_shell_and_other_owners(self):
        overlay = isolation.overlay(self.root, self.scope)
        backend = overlay["agent"]["devteam-back-end-dev-engineer"]["permission"]
        self.assertEqual(backend["edit"][str(self.root / "backend.py")], "allow")
        self.assertEqual(backend["bash"], "deny")
        self.assertEqual(overlay["agent"]["devteam-qa-engineer"]["permission"]["edit"], {"*": "deny"})


class EvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("eval_runner", ROOT / "evals" / "run.py")
        cls.runner = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.runner)
        spec = importlib.util.spec_from_file_location("eval_review", ROOT / "evals" / "review.py")
        cls.review = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.review)

    def test_fixed_scenarios_have_assertions_and_unique_ids(self):
        scenarios = json.loads((ROOT / "evals" / "scenarios.json").read_text())
        self.assertEqual(len(scenarios), 18)
        self.assertEqual(len({s["id"] for s in scenarios}), 18)
        for s in scenarios:
            self.assertTrue(s["criteria"])
            self.assertTrue(s["roles"])
            self.assertIn("allowed", s)

    def test_offline_is_not_a_behavioral_pass(self):
        from argparse import Namespace
        s = json.loads((ROOT / "evals" / "scenarios.json").read_text())[0]
        result = self.runner.execute(s, None, Namespace(live=False))
        self.assertEqual(result["status"], "not_run")
        self.assertIsNone(result["metrics"])

    def test_trace_metrics_do_not_invent_absent_cost(self):
        result = self.runner.observations([{"part": {"type": "tool", "tool": "task", "state": {"input": {"subagent_type": "devteam-qa-engineer"}}}}])
        self.assertEqual(result["delegations"], 1)
        self.assertIsNone(result["cost"])
        self.assertIsNone(result["tokens"])

    def test_prompt_has_no_coaching_beyond_notice(self):
        import inspect
        source = inspect.getsource(self.runner.execute)
        self.assertIn('prompt = s["request"] + NOTICE', source)
        for coaching in ("Assign role-specific ownership", "Return explicit handoffs", "actual check evidence"):
            self.assertNotIn(coaching, inspect.getsource(self.runner))

    def test_missing_child_exports_fail_routing_assertions(self):
        self.assertTrue(self.runner.exports_complete(3, [], 2))
        self.assertFalse(self.runner.exports_complete(2, [], 2))
        self.assertFalse(self.runner.exports_complete(3, ["ses_x"], 2))
        assertions = {"expected_delegations_observed": True, "selective_routing": True, "write_scope": True}
        limitations = []
        self.runner.require_export_coverage(assertions, False, ["ses_x"], limitations)
        self.assertEqual(assertions, {"expected_delegations_observed": False, "selective_routing": False, "write_scope": True})
        self.assertIn("ses_x", limitations[0])

    def test_budget_stops_and_fails_closed_on_unknown_cost(self):
        stop = self.runner.budget_stop
        self.assertIsNone(stop([], None))
        self.assertIsNone(stop([{"metrics": {"cost": 0.4}}], 1.0))
        self.assertIn("exceeded", stop([{"metrics": {"cost": 0.6}}, {"metrics": {"cost": 0.6}}], 1.0))
        self.assertIn("no cost", stop([{"metrics": {"cost": None}}], 1.0))
        self.assertIn("no cost", stop([{"metrics": None, "cost_unknown": True}], 1.0))

    def test_fixtures_are_deterministic_and_include_dirty_user_state(self):
        scenario = next(s for s in json.loads((ROOT / "evals" / "scenarios.json").read_text()) if s["id"] == "resume")
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            self.runner.fixture(Path(first), scenario, ROOT / ".opencode" / "agents")
            self.runner.fixture(Path(second), scenario, ROOT / ".opencode" / "agents")
            self.assertEqual(w.snapshot(first)["files"], w.snapshot(second)["files"])
            self.assertIn("a + b", (Path(first) / "backend.py").read_text())
            self.assertIn("USER COMMENT", (Path(first) / "backend.py").read_text())

    def test_review_cannot_promote_unrun_or_failed_invariants(self):
        reviews = {"version": 1, "scenarios": {"x": {"reviewer": "QA", "trace_references": ["trace:1"],
                   "criteria": [{"outcome": "passed", "evidence": ["trace:1"]}]}}}
        report = {"results": [{"id": "x", "status": "not_run", "criteria": ["criterion"], "assertions": {}}]}
        with self.assertRaises(ValueError):
            self.review.reviewed(report, reviews)
        report["results"][0].update(status="failed", assertions={"write_scope": False})
        self.assertEqual(self.review.reviewed(report, reviews)["results"][0]["status"], "failed")
        report["results"][0].update(status="inconclusive", assertions={"write_scope": True})
        self.assertEqual(self.review.reviewed(report, reviews)["summary"]["completion_rate"], 1)
        self.assertEqual(report["results"][0]["status"], "inconclusive")


if __name__ == "__main__":
    unittest.main()
