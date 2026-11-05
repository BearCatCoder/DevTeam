#!/usr/bin/env python3
"""Print an optional exact-path edit restriction overlay; verify resolved permissions.

This restricts OpenCode edit tools, not OS/filesystem access. Shell and remote
tools are denied in this mode. Never writes project or global configuration.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

from validate import NAMES, WRITERS, permission
from workflow import scope_valid


def overlay(root, scope):
    scope_valid(scope)
    root = Path(root).resolve()
    agents = {}
    for name in NAMES:
        edits = {"*": "deny"}
        for relative in scope["allowed"]:
            path = root / relative
            if path.resolve() != path or any(c in str(path) for c in "*?[]"):
                raise ValueError("symlink or pattern path cannot be isolated: " + relative)
            if name in WRITERS and scope["owners"][relative] == name:
                edits[str(path)] = "allow"
        agents[name] = {"permission": {"edit": edits, "bash": "deny", "github_*": "deny", "jira_*": "deny", "atlassian_*": "deny"}}
    return {"$schema": "https://opencode.ai/config.json", "agent": agents}


def verify(root, scope, config):
    env = {**os.environ, "OPENCODE_CONFIG_CONTENT": json.dumps(config)}
    for name in NAMES:
        run = subprocess.run(["opencode", "debug", "agent", name], cwd=root, env=env,
                             capture_output=True, text=True, check=True, timeout=120)
        agent = json.loads(run.stdout)
        for path in scope["allowed"]:
            expected = "allow" if name in WRITERS and scope["owners"][path] == name else "deny"
            if permission(agent, "edit", str(Path(root).resolve() / path)) != expected:
                raise ValueError("unresolved edit restriction: " + name + " " + path)
        for tool, target in (("edit", "/outside-devteam-scope"), ("bash", "gh issue list"),
                             ("bash", "python3 script.py"), ("github_update_issue", "*"),
                             ("jira_update_issue", "*"), ("atlassian_update_issue", "*")):
            if permission(agent, tool, target) != "deny":
                raise ValueError("isolation overlay not effective: " + name + " " + tool)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", type=Path, required=True)
    p.add_argument("--scope", type=Path, required=True)
    p.add_argument("--verify", action="store_true", help="Verify against installed resolved agents; no model calls")
    a = p.parse_args()
    try:
        scope = json.loads(a.scope.read_text())
        config = overlay(a.root, scope)
        if a.verify:
            verify(a.root, scope, config)
        print(json.dumps(config, indent=2))
    except (ValueError, OSError, subprocess.SubprocessError) as e:
        p.exit(1, "BLOCKED: " + str(e) + "\n")


if __name__ == "__main__":
    main()
