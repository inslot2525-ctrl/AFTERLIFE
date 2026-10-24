"""Gate merge: the only thing in AFTERLIFE that merges.

The Duo flow token can't merge, so this job does it with a project access
token, pinned to the commit this pipeline tested. Earlier jobs (verdict-check,
review-check) must have passed for it to run at all; on top of that it needs
a silent vigil, no protected path in the diff, and a CODEOWNERS approval when
policy lists the feature under requires_approval.

    python -m ci.gate_merge --feature books_v1 --vigil vigil.json \
        --policy target-policy.yaml --changed-files changed.txt
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from ci.gitlab import GitLab
from ci.policy import DEFAULT_POLICY, is_allowed_collateral, is_protected, load_policy


def decide(feature: str, vigil: dict | None, changed_files: list[str], policy: dict,
           codeowner_approved: bool) -> list[str]:
    """Reasons to refuse; an empty list means merge."""
    problems = []
    if vigil is None:
        problems.append("no vigil.json")
    elif vigil.get("feature") != feature:
        problems.append(f"vigil was for {vigil.get('feature')!r}, not {feature!r}")
    elif vigil.get("decision") != "pass":
        problems.append(f"vigil decision is {vigil.get('decision')!r}")
    for path in changed_files:
        if is_protected(path, policy) and not is_allowed_collateral(path, policy):
            problems.append(f"{path}: protected path in the diff")
    if feature in policy.get("requires_approval", []) and not codeowner_approved:
        problems.append(f"{feature} requires a CODEOWNERS approval")
    return problems


def merge_message(feature: str, iid) -> str:
    # The main pipeline's retirement jobs key off this exact prefix.
    return f"AFTERLIFE: retire {feature} via !{iid}"


def codeowner_approved(gitlab: GitLab, iid) -> bool:
    state = gitlab.get(f"/merge_requests/{iid}/approval_state")
    rules = [r for r in state.get("rules", []) if r.get("rule_type") == "code_owner"]
    return bool(rules) and all(r.get("approved") for r in rules)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", required=True)
    parser.add_argument("--vigil", default="vigil.json")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--changed-files", required=True)
    args = parser.parse_args()

    gitlab = GitLab()
    iid = os.environ["CI_MERGE_REQUEST_IID"]
    vigil_path = Path(args.vigil)
    vigil = json.loads(vigil_path.read_text()) if vigil_path.exists() else None
    changed = [line.strip() for line in Path(args.changed_files).read_text().splitlines() if line.strip()]
    policy = load_policy(args.policy)
    approved = codeowner_approved(gitlab, iid) if args.feature in policy.get("requires_approval", []) else False

    problems = decide(args.feature, vigil, changed, policy, approved)
    if problems:
        gitlab.comment_mr(iid, ":no_entry: **gate-merge refused**\n\n" + "\n".join(f"- {p}" for p in problems))
        print("Gate merge REFUSED:")
        for problem in problems:
            print(f"  - {problem}")
        sys.exit(1)

    # Merged-results pipelines test a merge commit; pin to the source head instead.
    sha = os.environ.get("CI_MERGE_REQUEST_SOURCE_BRANCH_SHA") or os.environ["CI_COMMIT_SHA"]
    body = {"sha": sha, "should_remove_source_branch": True, "merge_commit_message": merge_message(args.feature, iid)}
    # "auto" merges once this pipeline finishes green, which "Pipelines must
    # succeed" requires while this job is still running.
    if os.environ.get("GATE_MERGE_MODE", "auto") == "auto":
        body.update({"auto_merge": True, "merge_when_pipeline_succeeds": True})
    result = gitlab.put(f"/merge_requests/{iid}/merge", body)
    print(f"Gate merge: !{iid} at {sha[:8]} -> {result.get('state')}")


if __name__ == "__main__":
    main()
