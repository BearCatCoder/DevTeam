#!/usr/bin/env python3
"""Apply explicit human trace judgments without overwriting the raw evaluation report."""
import argparse
import copy
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from workflow import atomic_json, require


def reviewed(report, reviews):
    result = copy.deepcopy(report)
    require(reviews.get("version") == 1, "unsupported review version")
    for run in result["results"]:
        review = reviews.get("scenarios", {}).get(run["id"])
        if review is None:
            continue
        require(run["status"] in {"inconclusive", "failed"}, "cannot review an unrun/blocked scenario as executed")
        require(review.get("reviewer") and review.get("trace_references"), "review needs reviewer and trace references")
        judgments = review.get("criteria", [])
        require(len(judgments) == len(run["criteria"]), "review every listed criterion in order")
        require(all(c.get("outcome") in {"passed", "failed", "inconclusive"} and c.get("evidence") for c in judgments), "each judgment needs outcome and evidence")
        passed = all(c["outcome"] == "passed" for c in judgments)
        invariants = bool(run["assertions"]) and all(run["assertions"].values())
        run["status"] = "passed" if passed and invariants else "failed" if not invariants or any(c["outcome"] == "failed" for c in judgments) else "inconclusive"
        run["quality"] = review
    attempted = [r for r in result["results"] if r["status"] != "not_run"]
    result["summary"] = {"attempted": len(attempted), "reviewed_passes": sum(r["status"] == "passed" for r in attempted),
                         "completion_rate": sum(r["status"] == "passed" for r in attempted) / len(attempted) if attempted else None}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--reviews", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    require(not a.output.exists(), "use a new output file; preserve raw evidence")
    atomic_json(a.output, reviewed(json.loads(a.report.read_text()), json.loads(a.reviews.read_text())))


if __name__ == "__main__":
    main()
