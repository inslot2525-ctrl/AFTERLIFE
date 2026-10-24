"""Release notes for a retirement: the Sunset MR's '### Deprecation note'
section (written by the Undertaker) plus the death certificate's evidence.
Writes release_notes.md and release.env (RELEASE_TAG, RETIRED_FEATURE, MR_IID).

    python -m ci.release_notes
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

from ci.gitlab import GitLab, feature_from_branch
from ci.verdict_check import parse_verdicts

DEPRECATION_NOTE = re.compile(r"^###\s*Deprecation note\s*\n(.*?)(?=^#{1,3}\s|\Z)", re.MULTILINE | re.DOTALL)


def deprecation_note(description: str) -> str | None:
    match = DEPRECATION_NOTE.search(description or "")
    return match.group(1).strip() if match else None


def render(feature: str, mr_iid: int, description: str) -> str:
    lines = [f"## Retired: `{feature}`", "", deprecation_note(description) or f"`{feature}` has been removed.", ""]
    verdicts = [v for v in parse_verdicts(description or "") if v.get("feature") == feature]
    if verdicts and verdicts[0].get("evidence"):
        lines += ["**Evidence (from the death certificate):**", ""]
        lines += [f"- {e}" for e in verdicts[0]["evidence"]]
        lines.append("")
    lines.append(f"Retired by AFTERLIFE in !{mr_iid}. If you still need it, open an issue; "
                 "it can be restored from git history.")
    return "\n".join(lines)


def main() -> None:
    sha = os.environ["CI_COMMIT_SHA"]
    mr = GitLab().merge_request_for_commit(sha)
    if mr is None:
        print(f"{sha[:8]} did not come from a Sunset MR.")
        sys.exit(1)
    feature = feature_from_branch(mr["source_branch"])
    Path("release_notes.md").write_text(render(feature, mr["iid"], mr.get("description", "")))
    Path("release.env").write_text(
        f"RELEASE_TAG=retire-{feature}-{sha[:8]}\nRETIRED_FEATURE={feature}\nMR_IID={mr['iid']}\n")
    print(f"Release notes written for {feature} (!{mr['iid']}).")


if __name__ == "__main__":
    main()
