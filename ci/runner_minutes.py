"""Runner minutes: CI time spent on the same jobs in the parent commit's
pipeline (before) and in this one (after). Input to the SCI estimate.

Only jobs that finished successfully in both are compared, so the two numbers
measure the same work on a bigger and a smaller codebase.

    python -m ci.runner_minutes --base <parent-sha> --out runner_minutes.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ci.gitlab import GitLab

COMPARED_JOBS = ("test", "vulture", "build-image")


def job_minutes(jobs: list[dict]) -> float:
    seconds = sum(job.get("duration") or 0 for job in jobs
                  if job["name"] in COMPARED_JOBS and job["status"] == "success")
    return round(seconds / 60, 2)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True)
    parser.add_argument("--out", default="runner_minutes.json")
    args = parser.parse_args()

    gitlab = GitLab()
    branch = os.environ.get("CI_DEFAULT_BRANCH", "main")
    before_pipelines = gitlab.get("/pipelines", sha=args.base, ref=branch, per_page=1)
    before = (job_minutes(gitlab.get(f"/pipelines/{before_pipelines[0]['id']}/jobs", per_page=100))
              if before_pipelines else None)
    after = job_minutes(gitlab.get(f"/pipelines/{os.environ['CI_PIPELINE_ID']}/jobs", per_page=100))
    result = {"before": before, "after": after, "jobs": list(COMPARED_JOBS)}
    Path(args.out).write_text(json.dumps(result, indent=2))
    print(f"Runner minutes: {result}")


if __name__ == "__main__":
    main()
