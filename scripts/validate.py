#!/usr/bin/env python3
"""Validate resolved DevTeam agents using OpenCode itself; no model calls."""

from concurrent.futures import ThreadPoolExecutor
from fnmatch import fnmatchcase
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
ROLES = (
    "architect", "back-end-dev-engineer", "database-engineer", "dev-admin",
    "documentation-writer", "front-end-dev-engineer", "product-owner",
    "qa-engineer", "security-reviewer",
)
NAMES = ["DevTeam"] + [f"devteam-{role}" for role in ROLES]
WRITERS = {
    "devteam-back-end-dev-engineer", "devteam-front-end-dev-engineer",
    "devteam-database-engineer", "devteam-documentation-writer", "devteam-qa-engineer",
}
RUNNERS = WRITERS - {"devteam-documentation-writer"}


def permission(agent, tool, target="*"):
    action = None
    for rule in agent["permission"]:
        if fnmatchcase(tool, rule["permission"]) and fnmatchcase(target, rule["pattern"]):
            action = rule["action"]
    return action


def check(name):
    result = subprocess.run(
        ["opencode", "debug", "agent", name], cwd=ROOT,
        capture_output=True, text=True, timeout=120, check=True,
    )
    agent = json.loads(result.stdout)
    assert agent["name"] == name, f"{name}: not loaded"
    assert agent["mode"] == ("all" if name == "DevTeam" else "subagent")
    assert bool(agent.get("hidden")) == (name != "DevTeam")
    assert agent.get("description") and agent.get("prompt")
    assert not agent.get("model"), f"{name}: unexpected model override"
    assert not agent.get("options"), f"{name}: unexpected provider options"
    assert permission(agent, "edit") == ("allow" if name in WRITERS else "deny")
    assert permission(agent, "bash") == ("ask" if name in RUNNERS else "deny")
    assert permission(agent, "bash", "gh issue list") == "ask"
    assert permission(agent, "bash", "gh pr comment 42 --body review") == "ask"
    for command in ("git push", "python3 script.py", "gh-unrelated command"):
        assert permission(agent, "bash", command) == (
            "ask" if name in RUNNERS else "deny"
        ), f"{name}: unexpected shell permission for {command}"
    for tool in ("github_get_issue", "github_create_pull_request",
                 "jira_get_issue", "jira_update_issue", "atlassian_transition_issue"):
        assert permission(agent, tool) == "ask", f"{name}: {tool} unavailable"
    assert permission(agent, "unrelated_update_issue") == "deny"
    assert permission(agent, "read") == "allow"
    assert permission(agent, "unconfigured_mcp_tool") == "deny"
    assert permission(agent, "task", "general") == "deny"
    assert permission(agent, "task", "DevTeam") == "deny"
    for child in NAMES[1:]:
        expected = "allow" if name == "DevTeam" else "deny"
        assert permission(agent, "task", child) == expected, f"{name} -> {child}"
    # Ensure the installed/loaded prompt is actually the repository definition.
    source = (ROOT / ".opencode" / "agents" / f"{name}.md").read_text()
    assert source.split("---", 2)[2].strip() == agent["prompt"].strip()
    return name


def main():
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            for name in pool.map(check, NAMES):
                print(f"PASS {name}: loaded, mode, permissions, GitHub/Jira access, delegation, prompt, model neutrality")
    except (OSError, ValueError, KeyError, AssertionError, subprocess.SubprocessError) as error:
        print(f"FAIL: {error}", file=sys.stderr)
        return 1
    print("All 10 agents validated. This checks configuration, not model behavior.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
