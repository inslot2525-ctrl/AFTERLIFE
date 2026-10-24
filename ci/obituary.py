"""Obituary: the audit record for a retirement, posted on the census issue.

Written by CI from savings.json (measured numbers), never by an agent. The
census issue comes from the Sunset MR's `Census-Issue: #<iid>` line.

    python -m ci.obituary --savings savings.json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

from ci.gitlab import GitLab

CENSUS_ISSUE = re.compile(r"^Census-Issue:\s*#(\d+)\s*$", re.MULTILINE)


def census_issue(description: str) -> int | None:
    match = CENSUS_ISSUE.search(description or "")
    return int(match.group(1)) if match else None


def render(s: dict, release_url: str | None = None) -> str:
    def value(v, unit: str = "") -> str:
        return "not measured" if v is None else f"{v}{unit}"

    cves = f"{s['cves_before']} → {s['cves_after']}"
    if s["cves_removed"]:
        cves += f" (removed {', '.join(s['cves_removed'])})"
    lines = [
        f"## :headstone: Obituary: `{s['feature']}`",
        "",
        f"Retired in !{s['mr_iid']} at `{s['sha'][:8]}`. Every number below was measured by "
        f"[this job]({s['measured_by']}).",
        "",
        "| Measure | Value |",
        "| --- | --- |",
        f"| Lines removed | {s['lines_removed']} (added {s['lines_added']}) |",
        f"| Dependencies removed | {', '.join(s['deps_removed']) or 'none'} |",
        f"| CVEs before → after | {cves} |",
        f"| Image size | {value(s['image_mb_before'], ' MB')} → {value(s['image_mb_after'], ' MB')} |",
        f"| Runner minutes per pipeline | {value(s['runner_minutes_before'])} → {value(s['runner_minutes_after'])} |",
    ]
    sci = s.get("sci")
    if sci:
        lines.append(f"| SCI per pipeline run | {sci['before']['sci_gco2e']} → {sci['after']['sci_gco2e']} gCO2e "
                     f"(−{sci['delta_gco2e']}) |")
    else:
        lines.append(f"| SCI | not computed: {s.get('sci_missing', 'unknown')} |")
    if release_url:
        lines += ["", f"Release: {release_url}"]
    return "\n".join(lines)


def obituary_url(project_url: str | None, issue: int, note: dict | None) -> str | None:
    if not project_url:
        return None
    url = f"{project_url}/-/issues/{issue}"
    return f"{url}#note_{note['id']}" if note and note.get("id") else url


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--savings", default="savings.json")
    args = parser.parse_args()

    savings = json.loads(Path(args.savings).read_text())
    gitlab = GitLab()
    issue = census_issue(gitlab.mr(savings["mr_iid"]).get("description", ""))
    if issue is None:
        print(f"MR !{savings['mr_iid']} has no 'Census-Issue: #N' line; can't post the obituary.")
        sys.exit(1)
    note = gitlab.comment_issue(issue, render(savings, os.environ.get("RELEASE_URL")))
    print(f"Obituary posted on #{issue}.")
    # publish_savings runs next in this job; the graveyard links to the obituary.
    savings["obituary_url"] = obituary_url(os.environ.get("CI_PROJECT_URL"), issue, note)
    Path(args.savings).write_text(json.dumps(savings, indent=2))


if __name__ == "__main__":
    main()
