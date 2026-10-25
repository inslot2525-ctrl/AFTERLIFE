"""Cloud Run traffic helpers for the deploy jobs, safe when pipelines overlap.

Two main pipelines can be in flight at once (one runner, several pushes). So
each canary gets its own tag, promote skips when a newer pipeline will
promote anyway, and rollback picks its target from the traffic as it is now,
not from a snapshot taken before other pipelines moved it.

    gcloud run services describe shelf --format=json | python3 -m ci.cloudrun stable --exclude shelf-00009-rob
    gcloud run services describe shelf --format=json | python3 -m ci.cloudrun tag-url --tag c-42
    python3 -m ci.cloudrun superseded   # exit 0 if a newer main pipeline exists
"""

from __future__ import annotations

import argparse
import json
import os
import sys

from ci.gitlab import GitLab


def stable_revision(traffic: list[dict], exclude: str) -> str | None:
    """The revision serving the most traffic, other than the canary under test."""
    serving = [t for t in traffic if t.get("percent") and t.get("revisionName") != exclude]
    return max(serving, key=lambda t: t["percent"])["revisionName"] if serving else None


def tag_url(traffic: list[dict], tag: str) -> str | None:
    return next((t["url"] for t in traffic if t.get("tag") == tag), None)


# A newer pipeline in one of these states can still promote, or already has.
STILL_PROMOTING = {"created", "waiting_for_resource", "preparing", "pending", "running", "scheduled", "success"}


def is_superseded(pipelines: list[dict], pipeline_id: int) -> bool:
    """A newer push pipeline on the branch that is still on its way to production.

    A newer pipeline that failed, was cancelled or was skipped never promotes, so
    stepping aside for it would leave production on an old revision.
    """
    return any(p["id"] > pipeline_id and p.get("source") == "push"
               and p.get("status") in STILL_PROMOTING for p in pipelines)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    stable = sub.add_parser("stable")
    stable.add_argument("--exclude", required=True)
    url = sub.add_parser("tag-url")
    url.add_argument("--tag", required=True)
    sub.add_parser("superseded")
    args = parser.parse_args()

    if args.command == "superseded":
        pipelines = GitLab().get("/pipelines", ref=os.environ.get("CI_DEFAULT_BRANCH", "main"), per_page=20)
        sys.exit(0 if is_superseded(pipelines, int(os.environ["CI_PIPELINE_ID"])) else 1)

    traffic = json.load(sys.stdin)["status"]["traffic"]
    value = stable_revision(traffic, args.exclude) if args.command == "stable" else tag_url(traffic, args.tag)
    if value is None:
        sys.exit(f"no {args.command} found in the service's traffic")
    print(value)


if __name__ == "__main__":
    main()
