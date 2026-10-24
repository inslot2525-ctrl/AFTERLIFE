"""Verdict check: the deterministic gate between the agents and a deletion.

Parses the ```afterlife-verdict JSON blocks from a Sunset MR description and
checks them against the census, the policy (from the target branch) and the
files the MR actually changes. Any problem fails the job.

    python -m ci.verdict_check --description mr.md --census census/latest.json \
        --policy target-policy.yaml --changed-files changed.txt
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from ci.policy import DEFAULT_POLICY, is_allowed_collateral, is_protected, load_policy

VERDICTS = {"DEAD", "HIBERNATING", "ALIVE", "PROTECTED", "INSUFFICIENT_EVIDENCE"}
REQUIRED_KEYS = {"feature", "verdict", "confidence", "evidence", "files"}
VERDICT_BLOCK = re.compile(r"```afterlife-verdict\s*\n(.*?)```", re.DOTALL)


def parse_verdicts(text: str) -> list[dict]:
    return [json.loads(block) for block in VERDICT_BLOCK.findall(text)]


def check_dead(verdict: dict, signals: dict, policy: dict) -> list[str]:
    name = verdict["feature"]
    problems = []
    if signals["calls_in_window"] != 0:
        problems.append(f"{name}: {signals['calls_in_window']} calls in the census window")
    if signals["days_silent"] is not None and signals["days_silent"] < policy["min_silence_days"]:
        problems.append(f"{name}: silent {signals['days_silent']} days, policy needs {policy['min_silence_days']}")
    if signals["protected"]:
        problems.append(f"{name}: module is in protected_paths")
    if signals["seasonal_suspect"]:
        problems.append(f"{name}: usage looks seasonal; HIBERNATING expected")
    if verdict["confidence"] < policy["min_confidence"]:
        problems.append(f"{name}: confidence {verdict['confidence']} below {policy['min_confidence']}")
    if not verdict["evidence"]:
        problems.append(f"{name}: DEAD without evidence")
    return problems


def check(verdicts: list[dict], census: dict, policy: dict, changed_files: list[str]) -> list[str]:
    problems = []
    signals_by_name = {f["feature"]: f for f in census["features"]}
    dead_files: set[str] = set()

    for verdict in verdicts:
        missing = REQUIRED_KEYS - verdict.keys()
        if missing:
            problems.append(f"verdict missing keys: {', '.join(sorted(missing))}")
            continue
        name = verdict["feature"]
        if verdict["verdict"] not in VERDICTS:
            problems.append(f"{name}: unknown verdict {verdict['verdict']!r}")
            continue
        if name not in signals_by_name:
            problems.append(f"{name}: not in the census")
            continue
        if verdict["verdict"] == "DEAD":
            problems += check_dead(verdict, signals_by_name[name], policy)
            dead_files.update(f.replace("\\", "/") for f in verdict["files"])

    if changed_files and not dead_files:
        problems.append("MR changes files but carries no DEAD verdict")

    for path in changed_files:
        path = path.replace("\\", "/")
        if is_allowed_collateral(path, policy):
            continue
        if is_protected(path, policy):
            problems.append(f"{path}: protected path touched")
        elif path not in dead_files:
            problems.append(f"{path}: changed but not listed in any DEAD verdict's files")

    return problems


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--description", required=True, help="MR description saved to a file")
    parser.add_argument("--census", default="census/latest.json")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--changed-files", required=True, help="output of git diff --name-only")
    args = parser.parse_args()

    verdicts = parse_verdicts(Path(args.description).read_text())
    census = json.loads(Path(args.census).read_text())
    changed = [line.strip() for line in Path(args.changed_files).read_text().splitlines() if line.strip()]
    problems = check(verdicts, census, load_policy(args.policy), changed)

    if problems:
        print("Verdict check FAILED:")
        for problem in problems:
            print(f"  - {problem}")
        sys.exit(1)
    print(f"Verdict check passed: {len(verdicts)} verdict(s), {len(changed)} changed file(s).")


if __name__ == "__main__":
    main()
