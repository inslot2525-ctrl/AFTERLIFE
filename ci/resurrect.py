"""Resurrect: someone knocked during the vigil, so bring the feature back.

Runs with `when: on_failure` after the vigil. Reads vigil.json; if the vigil
decided "resurrect", turns the flag back on, labels and closes the Sunset MR,
posts the knock log, and starts the Medium (when the Flows API is enabled).

    python -m ci.resurrect --vigil vigil.json
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from ci.gitlab import GitLab


def knock_table(knocks: list[dict]) -> str:
    rows = ["| When (UTC) | Caller |", "| --- | --- |"]
    rows += [f"| {k.get('at', '')[:19]} | {k.get('caller', 'unknown')} |" for k in knocks[:20]]
    return "\n".join(rows)


def resurrection_note(feature: str, knocks: list[dict], medium_started: bool) -> str:
    return "\n\n".join([
        f":candle: **Resurrected.** `{feature}` got {len(knocks)} knock(s) during the vigil. "
        "The flag is back on and nothing was deleted.",
        knock_table(knocks),
        "The Medium has been asked to explain who still depends on it." if medium_started
        else "Mention the Medium's service account on this MR for the resurrection report.",
    ])


def start_medium(gitlab: GitLab, iid: str, feature: str, knocks: list[dict]) -> bool:
    """Start the afterlife-resurrect flow through the Flows API.

    UNVERIFIED: the endpoint and body are a guess until the Flows API spike
    confirms them, so this is off unless MEDIUM_VIA_API=1. The fallback is a
    human mention on the MR.
    """
    if os.environ.get("MEDIUM_VIA_API") != "1":
        return False
    gitlab.request("POST", os.environ.get("MEDIUM_FLOWS_ENDPOINT", "/ai/duo_workflows/workflows"), {
        "project_id": os.environ["CI_PROJECT_ID"],
        "workflow_definition": os.environ.get("MEDIUM_FLOW_DEFINITION", "afterlife-resurrect"),
        "goal": f"Explain who still depends on {feature}. Sunset MR !{iid}. Knocks: {json.dumps(knocks[:20])}",
    }, project_scoped=False)
    return True


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vigil", default="vigil.json")
    args = parser.parse_args()

    path = Path(args.vigil)
    if not path.exists():
        print("No vigil.json: the pipeline failed before the vigil, so there is nothing to resurrect.")
        return
    vigil = json.loads(path.read_text())
    if vigil["decision"] != "resurrect":
        print(f"Vigil decision was {vigil['decision']!r}; nothing to resurrect.")
        return

    feature, knocks, iid = vigil["feature"], vigil["knocks"], os.environ["CI_MERGE_REQUEST_IID"]
    gitlab = GitLab()
    gitlab.set_flag(feature, active=True)
    gitlab.put(f"/merge_requests/{iid}", {
        "add_labels": "afterlife::resurrected",
        "remove_labels": "afterlife::sunset",
        "state_event": "close",
    })
    medium = start_medium(gitlab, iid, feature, knocks)
    gitlab.comment_mr(iid, resurrection_note(feature, knocks, medium))
    print(f"{feature} resurrected; MR !{iid} closed.")


if __name__ == "__main__":
    main()
