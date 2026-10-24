"""Measure: write savings.json for one retirement, from measured numbers only.

Runs on the default branch after a Sunset MR merges, comparing the merge
commit with its first parent: lines removed, dependencies removed, CVEs
before vs after (pip-audit JSON), image size before vs after, and CI runner
minutes. SCI is computed only when every coefficient in
afterlife/sci_coefficients.yaml has a cited value; otherwise it stays null and
the reason is recorded. No number here is estimated without saying so.

    python -m ci.measure --feature books_v1 --mr-iid 12 --base <parent-sha> \
        --audit-before audit_before.json --audit-after audit_after.json \
        --image-before 212400000 --image-after 198100000 --minutes runner_minutes.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

import yaml

REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9_.\-]+)")
SCI_COEFFICIENTS = Path("afterlife/sci_coefficients.yaml")


def line_totals(numstat: str) -> dict:
    added = removed = 0
    for line in numstat.splitlines():
        parts = line.split("\t")
        if len(parts) == 3 and parts[0] != "-":  # "-" marks a binary file
            added += int(parts[0])
            removed += int(parts[1])
    return {"lines_added": added, "lines_removed": removed}


def requirement_names(text: str) -> set[str]:
    names = set()
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if line and not line.startswith("-"):
            match = REQUIREMENT_NAME.match(line)
            if match:
                names.add(match.group(1).lower().replace("_", "-"))
    return names


def deps_removed(before: str, after: str) -> list[str]:
    return sorted(requirement_names(before) - requirement_names(after))


def cve_ids(pip_audit: dict) -> set[str]:
    return {vuln["id"] for dep in pip_audit.get("dependencies", []) for vuln in dep.get("vulns", [])}


def sci(runner_minutes: float, coefficients: dict) -> dict | None:
    """SCI = ((E * I) + M) / R, with R = one pipeline run.

    Returns None when a coefficient is missing: never a made-up default.
    """
    grid = coefficients.get("grid", {})
    embodied = coefficients.get("embodied", {})
    compute = coefficients.get("compute", {})
    needed = [grid.get("gco2e_per_kwh"), embodied.get("gco2e_per_vcpu_hour"),
              compute.get("min_watts_per_vcpu"), compute.get("max_watts_per_vcpu")]
    if any(value is None for value in needed):
        return None
    hours = runner_minutes / 60
    vcpus, memory_gb = coefficients["runner"]["vcpus"], coefficients["runner"]["memory_gb"]
    watts = compute["min_watts_per_vcpu"] + compute["assumed_utilisation"] * (
        compute["max_watts_per_vcpu"] - compute["min_watts_per_vcpu"])
    energy_kwh = (watts * vcpus * hours / 1000 + memory_gb * hours * coefficients["memory_kwh_per_gb_hour"]) \
        * coefficients["pue"]
    embodied_g = embodied["gco2e_per_vcpu_hour"] * vcpus * hours
    return {
        "E_kwh": round(energy_kwh, 6),
        "I_gco2e_per_kwh": grid["gco2e_per_kwh"],
        "M_gco2e": round(embodied_g, 4),
        "R": "1 pipeline run",
        "sci_gco2e": round(energy_kwh * grid["gco2e_per_kwh"] + embodied_g, 4),
    }


def megabytes(n: int | None) -> float | None:
    return round(n / 1_000_000, 1) if n is not None else None


def build_savings(*, feature: str, mr_iid: int, sha: str, numstat: str, requirements_before: str,
                  requirements_after: str, audit_before: dict, audit_after: dict,
                  image_before: int | None, image_after: int | None,
                  minutes_before: float | None, minutes_after: float | None,
                  coefficients: dict, measured_by: str) -> dict:
    cves_before, cves_after = cve_ids(audit_before), cve_ids(audit_after)
    savings = {
        "feature": feature,
        "mr_iid": mr_iid,
        "sha": sha,
        "measured_by": measured_by,
        **line_totals(numstat),
        "deps_removed": deps_removed(requirements_before, requirements_after),
        "cves_before": len(cves_before),
        "cves_after": len(cves_after),
        "cves_removed": sorted(cves_before - cves_after),
        "image_mb_before": megabytes(image_before),
        "image_mb_after": megabytes(image_after),
        "image_mb_saved": megabytes(image_before - image_after)
        if image_before is not None and image_after is not None else None,
        "runner_minutes_before": minutes_before,
        "runner_minutes_after": minutes_after,
        "sci": None,
    }
    if minutes_before is None or minutes_after is None:
        savings["sci_missing"] = "runner minutes not available"
        return savings
    before, after = sci(minutes_before, coefficients), sci(minutes_after, coefficients)
    if before is None or after is None:
        savings["sci_missing"] = f"coefficients incomplete in {SCI_COEFFICIENTS}"
        return savings
    savings["sci"] = {"before": before, "after": after,
                      "delta_gco2e": round(before["sci_gco2e"] - after["sci_gco2e"], 4)}
    return savings


def git(*args: str) -> str:
    return subprocess.run(["git", *args], check=True, capture_output=True, text=True).stdout


def git_show(rev: str, path: str) -> str:
    result = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else ""


def read_json(path: str | None) -> dict:
    return json.loads(Path(path).read_text()) if path and Path(path).exists() else {}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", required=True)
    parser.add_argument("--mr-iid", type=int, required=True)
    parser.add_argument("--base", required=True, help="the merge commit's first parent")
    parser.add_argument("--sha", default=os.environ.get("CI_COMMIT_SHA", "HEAD"))
    parser.add_argument("--audit-before")
    parser.add_argument("--audit-after")
    parser.add_argument("--image-before", type=int)
    parser.add_argument("--image-after", type=int)
    parser.add_argument("--minutes", help="runner_minutes.json")
    parser.add_argument("--out", default="savings.json")
    args = parser.parse_args()

    minutes = read_json(args.minutes)
    savings = build_savings(
        feature=args.feature, mr_iid=args.mr_iid, sha=git("rev-parse", args.sha).strip(),
        numstat=git("diff", "--numstat", args.base, args.sha),
        requirements_before=git_show(args.base, "requirements.txt"),
        requirements_after=git_show(args.sha, "requirements.txt"),
        audit_before=read_json(args.audit_before), audit_after=read_json(args.audit_after),
        image_before=args.image_before, image_after=args.image_after,
        minutes_before=minutes.get("before"), minutes_after=minutes.get("after"),
        coefficients=yaml.safe_load(SCI_COEFFICIENTS.read_text()),
        measured_by=os.environ.get("CI_JOB_URL", "local run"),
    )
    Path(args.out).write_text(json.dumps(savings, indent=2))
    print(json.dumps(savings, indent=2))


if __name__ == "__main__":
    main()
