"""Rollback notice: the canary failed and traffic went back to the previous
revision (the gcloud command is in the job). Reopen the census issue with the
canary's numbers so the retirement gets judged again.

    python -m ci.rollback --canary canary.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ci.gitlab import GitLab
from ci.obituary import census_issue


def rollback_note(canary: dict, previous_revision: str) -> str:
    reasons = ", ".join(canary.get("problems", [])) or "see the job log"
    return (f":rewind: **Rolled back.** Canary `{canary.get('revision', '?')}` failed: {reasons}. "
            f"Traffic is back on `{previous_revision}`. This census issue is reopened for re-judgement.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--canary", default="canary.json")
    args = parser.parse_args()

    canary = json.loads(Path(args.canary).read_text()) if Path(args.canary).exists() else {}
    note = rollback_note(canary, os.environ.get("PREV_REVISION", "the previous revision"))
    print(note)
    gitlab = GitLab()
    mr = gitlab.merge_request_for_commit(os.environ["CI_COMMIT_SHA"])
    issue = census_issue(mr.get("description", "")) if mr else None
    if issue:
        gitlab.put(f"/issues/{issue}", {"state_event": "reopen"})
        gitlab.comment_issue(issue, note)


if __name__ == "__main__":
    main()
