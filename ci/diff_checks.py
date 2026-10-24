"""Before-vs-after checks on a Sunset MR (target branch vs MR head).

    python -m ci.diff_checks vulture vulture_target.txt vulture_mr.txt
        Fails if any file has more unused-code findings than on the target:
        a deletion must not leave orphans behind.
    python -m ci.diff_checks pip-audit audit_target.json audit_mr.json
        Fails on any CVE the MR introduces. Writes cves.json with before/after.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ci.census import parse_vulture
from ci.measure import cve_ids


def new_unused(target_output: str, mr_output: str) -> dict[str, int]:
    before = {path: len(items) for path, items in parse_vulture(target_output).items()}
    after = {path: len(items) for path, items in parse_vulture(mr_output).items()}
    return {path: n - before.get(path, 0) for path, n in sorted(after.items()) if n > before.get(path, 0)}


def cve_diff(target: dict, mr: dict) -> dict:
    before, after = cve_ids(target), cve_ids(mr)
    return {"cves_before": len(before), "cves_after": len(after),
            "cves_removed": sorted(before - after), "cves_added": sorted(after - before)}


def read_json(path: Path) -> dict:
    text = path.read_text() if path.exists() else ""
    return json.loads(text) if text.strip() else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("check", choices=["vulture", "pip-audit"])
    parser.add_argument("target", type=Path)
    parser.add_argument("mr", type=Path)
    args = parser.parse_args()

    if args.check == "vulture":
        grown = new_unused(args.target.read_text(), args.mr.read_text())
        if grown:
            print(f"Vulture recheck FAILED: the deletion left new unused code behind: {grown}")
            sys.exit(1)
        print("Vulture recheck passed: no new unused code.")
        return

    diff = cve_diff(read_json(args.target), read_json(args.mr))
    Path("cves.json").write_text(json.dumps(diff, indent=2))
    print(f"CVEs {diff['cves_before']} -> {diff['cves_after']}; removed: {', '.join(diff['cves_removed']) or 'none'}")
    if diff["cves_added"]:
        print(f"pip-audit diff FAILED: the MR introduces {', '.join(diff['cves_added'])}")
        sys.exit(1)


if __name__ == "__main__":
    main()
