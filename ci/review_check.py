"""Review check: the Reviewer agent must have said PASS on the Sunset MR.

The Reviewer posts a note with a line `AFTERLIFE-REVIEW: PASS` or
`AFTERLIFE-REVIEW: BLOCK`. The latest one from the agent's account wins. The
note may arrive after the pipeline starts, so this waits for it.

    python -m ci.review_check --wait-minutes 15
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time

from ci.gitlab import GitLab

REVIEW_LINE = re.compile(r"^\s*AFTERLIFE-REVIEW:\s*(PASS|BLOCK)\b", re.MULTILINE)


def latest_review(notes: list[dict], agent_username: str | None) -> str | None:
    result = None
    for note in notes:  # oldest first
        if agent_username and note.get("author", {}).get("username") != agent_username:
            continue
        match = REVIEW_LINE.search(note.get("body", ""))
        if match:
            result = match.group(1)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wait-minutes", type=float, default=15)
    parser.add_argument("--poll-seconds", type=float, default=30)
    args = parser.parse_args()

    gitlab = GitLab()
    iid = os.environ["CI_MERGE_REQUEST_IID"]
    agent = os.environ.get("AFTERLIFE_AGENT_USERNAME")
    deadline = time.monotonic() + args.wait_minutes * 60
    review = latest_review(gitlab.mr_notes(iid), agent)
    while review is None and time.monotonic() < deadline:
        print("Waiting for the Reviewer's AFTERLIFE-REVIEW note...", flush=True)
        time.sleep(args.poll_seconds)
        review = latest_review(gitlab.mr_notes(iid), agent)

    if review != "PASS":
        print(f"Review check FAILED: Reviewer says {review or 'nothing'}; AFTERLIFE-REVIEW: PASS is required.")
        sys.exit(1)
    print("Review check passed: Reviewer said PASS.")


if __name__ == "__main__":
    main()
