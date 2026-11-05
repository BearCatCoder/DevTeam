#!/usr/bin/env python3
"""Generate/check per-role reliability blocks; no runtime policy dependency."""
import argparse
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "policy" / "reliability-v1.md"
START = "<!-- devteam-policy:v1:start -->"
END = "<!-- devteam-policy:v1:end -->"
AUDIENCES = ("all", "specialists", "writers", "coordinator")
WRITERS = {
    "devteam-back-end-dev-engineer", "devteam-front-end-dev-engineer",
    "devteam-database-engineer", "devteam-qa-engineer", "devteam-documentation-writer",
}


def sections(policy):
    """Return [(audience, text)] in source order; reject unmarked or unknown text."""
    parts = re.split(r"^<!-- (\w+) -->\n", policy, flags=re.M)
    if parts[0].strip():
        raise ValueError("policy text before first audience marker")
    result = []
    for audience, text in zip(parts[1::2], parts[2::2]):
        if audience not in AUDIENCES:
            raise ValueError("unknown policy audience: " + audience)
        result.append((audience, text.strip()))
    return result


def audiences(name):
    if name == "DevTeam":
        return {"all", "coordinator"}
    return {"all", "specialists", "writers"} if name in WRITERS else {"all", "specialists"}


def block_for(name, policy):
    wanted = audiences(name)
    body = "\n\n".join(text for audience, text in sections(policy) if audience in wanted)
    return "## Reliability contract v1\n\n" + body


def render(text, block):
    block = START + "\n" + block.rstrip() + "\n" + END
    if START in text:
        before, rest = text.split(START, 1)
        _, after = rest.split(END, 1)
        return before + block + after
    return text.rstrip() + "\n\n" + block + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Regenerate only marked blocks")
    args = parser.parse_args()
    policy = SOURCE.read_text()
    stale = []
    for p in sorted((ROOT / ".opencode" / "agents").glob("*.md")):
        old = p.read_text()
        new = render(old, block_for(p.stem, policy))
        if old != new:
            stale.append(p.name)
            if args.write:
                p.write_text(new)
    print(("Updated: " if args.write else "Drift: ") + ", ".join(stale) if stale else "PASS: all ten embedded policy blocks match v1")
    return int(bool(stale) and not args.write)


if __name__ == "__main__":
    raise SystemExit(main())
