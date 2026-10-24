"""Publish a retirement's measured savings so /graveyard can show them.

CI never commits to main, so savings.json from the measure job goes to the
app's store (Firestore in production) under the feature's name.

    AFTERLIFE_STORE=firestore python -m ci.publish_savings --savings savings.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from app.store import store_from_env


def with_links(savings: dict) -> dict:
    """Add links back to the jobs that produced the numbers."""
    project_url = os.environ.get("CI_PROJECT_URL")
    if not project_url:
        return savings
    linked = dict(savings)
    linked["mr_url"] = f"{project_url}/-/merge_requests/{savings['mr_iid']}"
    if os.environ.get("CI_JOB_URL"):
        linked["measured_job_url"] = os.environ["CI_JOB_URL"]
    if os.environ.get("RELEASE_TAG"):
        linked["release_url"] = f"{project_url}/-/releases/{os.environ['RELEASE_TAG']}"
    return linked


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--savings", default="savings.json")
    args = parser.parse_args()

    savings = with_links(json.loads(Path(args.savings).read_text()))
    store_from_env().record_savings(savings["feature"], savings)
    print(f"Published savings for {savings['feature']}.")


if __name__ == "__main__":
    main()
