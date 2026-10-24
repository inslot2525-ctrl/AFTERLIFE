"""The Coroner's latest verdicts, read from the census issue, for the graveyard.

The ledger (afterlife/graveyard.yaml) only changes through Sunset MRs, so a
feature the Coroner decided to keep (HIBERNATING) never reaches it. This reads
the afterlife-verdict blocks the Coroner posted on the newest "AFTERLIFE
census" issue and adds those decisions to what the pages show, linked to the
issue they came from.

GitLab hides issue notes from anonymous API calls, so this needs
AFTERLIFE_GITLAB_READ_TOKEN (read_api). Without it the pages show the ledger
alone.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.error

from app.timeline import Fetch, gitlab_fetch

CENSUS_TITLE = "AFTERLIFE census"
VERDICT_BLOCK = re.compile(r"```afterlife-verdict\s*\n(.*?)```", re.DOTALL)
CACHE_SECONDS = 60


def parse_verdicts(text: str) -> list[dict]:
    verdicts = []
    for block in VERDICT_BLOCK.findall(text or ""):
        try:
            verdicts.append(json.loads(block))
        except ValueError:
            continue  # a malformed block is the Coroner's problem, not the page's
    return verdicts


def latest_verdicts(fetch: Fetch = gitlab_fetch) -> tuple[list[dict], dict | None]:
    """Verdicts from the newest census issue that has any, and that issue."""
    issues = fetch("/issues?search=AFTERLIFE%20census&in=title&order_by=created_at&sort=desc&per_page=10")
    for issue in issues:
        if not issue.get("title", "").startswith(CENSUS_TITLE):
            continue
        notes = fetch(f"/issues/{issue['iid']}/notes?sort=desc&order_by=created_at&per_page=50")
        for note in notes:
            verdicts = parse_verdicts(note.get("body", ""))
            if verdicts:
                return verdicts, issue
    return [], None


def with_verdicts(ledger: dict, verdicts: list[dict], issue: dict | None) -> dict:
    """The ledger plus features the Coroner chose to keep, without duplicates."""
    if not verdicts:
        return ledger
    known = {entry.get("feature") for key in ledger for entry in ledger[key]}
    source = f"Coroner, census #{issue['iid']}" if issue else "Coroner"
    hibernating = list(ledger["hibernating"])
    for verdict in verdicts:
        if verdict.get("verdict") != "HIBERNATING" or verdict.get("feature") in known:
            continue
        evidence = verdict.get("evidence") or []
        hibernating.append({
            "feature": verdict["feature"],
            "reason": "; ".join(str(e) for e in evidence[:2]) or "usage looks periodic",
            "recheck": verdict.get("recheck") or "",
            "source": source,
        })
    return {**ledger, "hibernating": hibernating}


_cache: dict = {"at": 0.0, "value": ([], None), "loaded": False}


def cached_verdicts(fetch: Fetch = gitlab_fetch) -> tuple[list[dict], dict | None]:
    """Shared by every viewer for CACHE_SECONDS; empty if GitLab can't be read."""
    if os.environ.get("AFTERLIFE_TIMELINE") == "off" or not os.environ.get("AFTERLIFE_GITLAB_READ_TOKEN"):
        return [], None
    # A fresh Cloud Run container's monotonic clock starts near 0, so "at" alone
    # would hide the verdicts for the first minute after every cold start.
    if not _cache["loaded"] or time.monotonic() - _cache["at"] >= CACHE_SECONDS:
        try:
            _cache["value"] = latest_verdicts(fetch)
            _cache["loaded"] = True
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, TypeError):
            pass  # keep the last known verdicts
        _cache["at"] = time.monotonic()
    return _cache["value"]
