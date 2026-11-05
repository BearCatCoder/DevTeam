#!/usr/bin/env python3
"""Generate/check the self-contained reliability block; no runtime policy dependency."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- devteam-policy:v1:start -->"
END = "<!-- devteam-policy:v1:end -->"


def render(text, policy):
    block = START + "\n" + policy.rstrip() + "\n" + END
    if START in text:
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
        return before + block + after
    return text.rstrip() + "\n\n" + block + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate only marked blocks")
    args = parser.parse_args()
    policy = (ROOT / "policy" / "reliability-v1.md").read_text()
    stale = []
    for p in sorted((ROOT / ".opencode" / "agents").glob("*.md")):
        old = p.read_text()
        new = render(old, policy)
        if old != new:
            stale.append(p.name)
            if args.write:
                p.write_text(new)
    print(("Updated: " if args.write else "Drift: ") + ", ".join(stale) if stale else "PASS: all ten embedded policy blocks match v1")
    return int(bool(stale) and not args.write)


if __name__ == "__main__":
    raise SystemExit(main())
