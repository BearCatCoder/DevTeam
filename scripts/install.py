#!/usr/bin/env python3
"""Install the ten self-contained agent definitions without changing config."""

import argparse
import os
from pathlib import Path
import shutil


SOURCE = Path(__file__).resolve().parents[1] / ".opencode" / "agents"


def install(destination, replace=False):
    destination = Path(destination)
    sources = sorted(SOURCE.glob("*.md"))
    if len(sources) != 10 or not (SOURCE / "DevTeam.md").is_file():
        raise ValueError("Expected DevTeam and nine specialist definitions.")

    # Preflight the entire set before copying anything. Never follow an existing
    # agent symlink when replacing a definition.
    conflicts = []
    pending = []
    for source in sources:
        target = destination / source.name
        if target.is_symlink() or (target.exists() and not target.is_file()):
            conflicts.append(str(target))
        elif target.is_file() and target.read_bytes() == source.read_bytes():
            continue
        elif target.exists() and not replace:
            conflicts.append(str(target))
        else:
            pending.append((source, target))
    if conflicts:
        raise ValueError(
            "Conflicting agent paths (no files copied):\n"
            + "\n".join(conflicts)
            + "\nReview differences; --replace permits replacing regular files only."
        )
    destination.mkdir(parents=True, exist_ok=True)
    for source, target in pending:
        shutil.copy2(source, target)
    return len(pending)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--global", dest="global_scope", action="store_true",
                       help="Install in the user's OpenCode config directory")
    scope.add_argument("--project", type=Path, metavar="ROOT",
                       help="Install in an existing project's .opencode/agents")
    parser.add_argument("--replace", action="store_true",
                        help="Replace differing regular files with the same names")
    args = parser.parse_args()
    if args.global_scope:
        config_home = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
        destination = config_home / "opencode" / "agents"
    else:
        root = args.project.expanduser().resolve()
        if not root.is_dir():
            parser.error("--project must name an existing project directory")
        destination = root / ".opencode" / "agents"
    try:
        count = install(destination, args.replace)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(f"Installed/updated {count} agent files in {destination}")
    print("Quit and restart OpenCode, then invoke @DevTeam in your project.")


if __name__ == "__main__":
    main()
