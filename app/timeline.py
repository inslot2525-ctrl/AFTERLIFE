"""Live retirement timeline for /graveyard, read from GitLab itself.

Each Sunset MR (branch afterlife/<feature>) is one retirement. Its stages come
from the jobs GitLab already ran: the MR pipeline (gates, coma, vigil, merge
or resurrect) and the main pipeline of the merge commit (canary, promote or
rollback, obituary). Nothing extra is recorded, so the timeline can't drift
from what actually happened, and every stage links to its job.

The project is public, so no token is needed; AFTERLIFE_GITLAB_READ_TOKEN
(read_api) raises the rate limit if set.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from html import escape
from pathlib import Path
from typing import Callable

import yaml

GITLAB_API = os.environ.get("AFTERLIFE_GITLAB_API", "https://gitlab.com/api/v4")
PROJECT = os.environ.get("AFTERLIFE_GITLAB_PROJECT", "afterlife-transcend/AFTERLIFE")
BRANCH_PREFIX = "afterlife/"
NOT_RETIREMENTS = ("afterlife/census", "afterlife/resurrect-")
CACHE_SECONDS = 15
REFRESH_MS = 15_000

Fetch = Callable[[str], object]
# feature, vigil start -> knocks heard since then (the app's usage store).
Knocks = Callable[[str, dt.datetime], int]
POLICY = Path(__file__).resolve().parent.parent / "afterlife" / "policy.yaml"


def vigil_minutes() -> float:
    """The vigil length CI uses: policy, unless overridden like CI's VIGIL_MINUTES."""
    override = os.environ.get("AFTERLIFE_VIGIL_MINUTES")
    if override:
        return float(override)
    try:
        return float(yaml.safe_load(POLICY.read_text())["vigil_minutes"])
    except (OSError, KeyError, TypeError, ValueError):
        return 10.0


def _vigil_clock(stage: dict, job: dict | None, feature: str, knocks: Knocks | None, minutes: float) -> dict:
    """A running vigil gets its deadline and knock count, for the countdown."""
    if not job or job["status"] != "running" or not job.get("started_at"):
        return stage
    started = dt.datetime.fromisoformat(job["started_at"].replace("Z", "+00:00"))
    clock = {"deadline": (started + dt.timedelta(minutes=minutes)).isoformat()}
    if knocks:
        try:
            clock["knocks"] = knocks(feature, started)
        except Exception:  # noqa: BLE001 - the countdown must not take the page down
            pass
    return {**stage, **clock}

# GitLab job status -> stage state.
JOB_STATE = {
    "success": "done", "running": "active", "pending": "waiting", "created": "waiting",
    "waiting_for_resource": "waiting", "preparing": "waiting", "scheduled": "waiting",
    "failed": "failed", "canceled": "skipped", "skipped": "skipped", "manual": "skipped",
}


def gitlab_fetch(path: str) -> object:
    url = f"{GITLAB_API}/projects/{urllib.parse.quote(PROJECT, safe='')}{path}"
    headers = {}
    token = os.environ.get("AFTERLIFE_GITLAB_READ_TOKEN")
    if token:
        headers["PRIVATE-TOKEN"] = token
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=5) as resp:
        return json.loads(resp.read())


def latest_jobs(fetch: Fetch, pipeline_id: int) -> dict[str, dict]:
    """Job name -> its newest run (a retried job appears more than once)."""
    jobs: dict[str, dict] = {}
    for job in fetch(f"/pipelines/{pipeline_id}/jobs?per_page=100&include_retried=false"):
        if job["name"] not in jobs or job["id"] > jobs[job["name"]]["id"]:
            jobs[job["name"]] = job
    return jobs


def _stage(label: str, state: str, url: str | None = None, note: str = "") -> dict:
    return {"label": label, "state": state, "url": url, "note": note}


def _from_job(label: str, job: dict | None, note: str = "") -> dict:
    if job is None:
        return _stage(label, "todo")
    return _stage(label, JOB_STATE.get(job["status"], "waiting"), job.get("web_url"), note)


def retirement(fetch: Fetch, mr: dict, knocks: Knocks | None = None, minutes: float | None = None) -> dict:
    feature = mr["source_branch"].removeprefix(BRANCH_PREFIX)
    stages = [
        _stage("Death certificate", "done", mr["web_url"], "Coroner"),
        _stage("Sunset MR", "done", mr["web_url"], f"!{mr['iid']}"),
    ]
    pipelines = fetch(f"/merge_requests/{mr['iid']}/pipelines?per_page=1")
    mr_jobs = latest_jobs(fetch, pipelines[0]["id"]) if pipelines else {}
    stages += [
        _from_job("Reviewed", mr_jobs.get("review-check"), "Reviewer agent"),
        _from_job("Gates", mr_jobs.get("verdict-check"), "policy from main"),
        _from_job("Coma", mr_jobs.get("coma"), "flag off"),
        _vigil_clock(_from_job("Vigil", mr_jobs.get("vigil"), "listening for knocks"), mr_jobs.get("vigil"),
                     feature, knocks, minutes if minutes is not None else vigil_minutes()),
    ]

    resurrect = mr_jobs.get("resurrect")
    if resurrect and resurrect["status"] in ("success", "running"):
        # vigil.py exits 1 on a knock by design; here that is the story, not an error.
        vigil = stages[-1]
        stages[-1] = {**vigil, "state": "knocked", "note": "knock heard"}
        stages.append(_from_job("Resurrected", resurrect, "flag back on"))
        return {"feature": feature, "outcome": "resurrected", "mr_url": mr["web_url"], "stages": stages}

    merged = mr.get("state") == "merged" and mr.get("merge_commit_sha")
    stages.append(_stage("Merged", "done", mr["web_url"], "gate-merge")
                  if merged else _from_job("Merged", mr_jobs.get("gate-merge"), "gate-merge"))
    if not merged:
        outcome = "failed" if any(s["state"] == "failed" for s in stages) else "in progress"
        return {"feature": feature, "outcome": outcome, "mr_url": mr["web_url"], "stages": stages}

    main = fetch(f"/pipelines?sha={mr['merge_commit_sha']}&ref=main&per_page=1")
    main_jobs = latest_jobs(fetch, main[0]["id"]) if main else {}
    rollback = main_jobs.get("rollback")
    # rollback exits 1 only when it actually rolled back; it passes when the canary was healthy.
    if rollback and rollback["status"] == "failed":
        stages += [_from_job("Canary", main_jobs.get("canary-watch"), "10% of traffic"),
                   _stage("Rolled back", "failed", rollback.get("web_url"), "traffic to old revision")]
        return {"feature": feature, "outcome": "rolled back", "mr_url": mr["web_url"], "stages": stages}

    promote = main_jobs.get("promote")
    live_ok = promote and rollback and promote["status"] == "success" and rollback["status"] == "success"
    stages += [
        _from_job("Canary", main_jobs.get("canary-watch"), "10% of traffic"),
        _stage("Live", "done", promote.get("web_url"), "100% of traffic") if live_ok
        else _from_job("Live", promote, "100% of traffic"),
        _from_job("Obituary", main_jobs.get("obituary"), "savings measured"),
    ]
    outcome = "retired" if all(s["state"] == "done" for s in stages) else "in progress"
    return {"feature": feature, "outcome": outcome, "mr_url": mr["web_url"], "stages": stages}


def is_retirement(mr: dict) -> bool:
    """A Sunset MR: open or merged, or closed because the feature was resurrected."""
    branch = mr["source_branch"]
    if not branch.startswith(BRANCH_PREFIX) or branch.startswith(NOT_RETIREMENTS):
        return False
    return mr.get("state") != "closed" or "afterlife::resurrected" in mr.get("labels", [])


def build_timeline(fetch: Fetch = gitlab_fetch, limit: int = 8, knocks: Knocks | None = None) -> list[dict]:
    mrs = fetch("/merge_requests?state=all&order_by=created_at&sort=desc&per_page=50")
    return [retirement(fetch, mr, knocks) for mr in [mr for mr in mrs if is_retirement(mr)][:limit]]


_cache: dict = {"at": 0.0, "value": None, "error": None}


def cached_timeline(fetch: Fetch = gitlab_fetch, knocks: Knocks | None = None) -> tuple[list[dict], str | None]:
    """Shared by every viewer for CACHE_SECONDS, to stay far below GitLab's rate limit."""
    if os.environ.get("AFTERLIFE_TIMELINE") == "off":
        return [], None
    if time.monotonic() - _cache["at"] >= CACHE_SECONDS or _cache["value"] is None:
        try:
            _cache.update(value=build_timeline(fetch, knocks=knocks), error=None)
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as error:
            _cache.update(error=f"GitLab unavailable ({type(error).__name__}); showing the last known state.")
            _cache["value"] = _cache["value"] or []
        _cache["at"] = time.monotonic()
    return _cache["value"], _cache["error"]


STYLE = r"""
/* --- active cases: glass panels, one per retirement ------------------------- */
.timeline { display: grid; grid-template-columns: minmax(0, 1fr); gap: 16px; }
.retirement { position: relative; overflow: hidden; padding: 24px 26px 22px;
  background: linear-gradient(180deg, var(--glass-hi), var(--glass)); border: 1px solid var(--edge); border-radius: var(--radius);
  backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur); box-shadow: inset 0 1px 0 var(--sheen); }
.retirement:has(.outcome.resurrected) { box-shadow: inset 0 1px 0 var(--sheen), 0 0 80px -30px rgba(201, 168, 255, 0.45); }
.retirement:has(.step.active) { box-shadow: inset 0 1px 0 var(--sheen), 0 0 80px -30px rgba(166, 220, 255, 0.5); }
.retirement:has(.step.active)::after { content: ""; position: absolute; top: 0; left: 0; width: 30%; height: 1px;
  background: linear-gradient(90deg, transparent, var(--ice), transparent); animation: scanline 3s linear infinite; }
.retirement header { display: flex; justify-content: space-between; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 26px; }
.retirement h3 { margin: 0; font: 400 15px/1.2 var(--display); letter-spacing: 0.08em; text-transform: uppercase; }
.retirement h3::before { content: "SUBJECT  "; font: 400 10px/1 var(--mono); letter-spacing: 0.16em; color: var(--faint); }
.retirement h3 a { color: var(--ink); }
.retirement h3 a::after { content: "  \2197"; font: 400 12px/1 var(--mono); color: var(--faint); }
.retirement h3 a:hover { color: var(--ice); }
.outcome { display: inline-flex; align-items: center; gap: 8px; padding: 7px 13px; border-radius: 999px;
  font: 500 10.5px/1 var(--mono); letter-spacing: 0.14em; text-transform: uppercase; }
.outcome::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; box-shadow: 0 0 10px currentColor; }
.outcome.retired { color: var(--mint); background: var(--mint-soft); }
.outcome.resurrected { color: var(--aura); background: var(--aura-soft); }
.outcome.failed, .outcome.rolled-back { color: var(--coral); background: var(--coral-soft); }
.outcome.in-progress { color: var(--ice); background: var(--ice-soft); }
.outcome.in-progress::before { animation: breathe 1.4s ease-in-out infinite; }
.steps { display: flex; overflow-x: auto; padding: 0 0 4px; scrollbar-width: none; }
.steps::-webkit-scrollbar { display: none; }
.step { flex: 1 1 0; min-width: 80px; position: relative; padding: 28px 4px 0; text-align: center;
  font: 400 10.5px/1.5 var(--mono); color: var(--faint); text-wrap: balance; }
.step b { display: block; margin-bottom: 4px; font: 400 9.5px/1.3 var(--display); letter-spacing: 0.12em; text-transform: uppercase; color: var(--quiet); }
.step::before { content: ""; position: absolute; top: 6px; left: 50%; width: 10px; height: 10px; margin-left: -5px; z-index: 1;
  border-radius: 50%; background: var(--bg); border: 1px solid var(--edge-hi); transition: transform .25s; }
.step::after { content: ""; position: absolute; top: 11px; left: -50%; width: 100%; height: 1px; background: var(--edge); }
.step:first-child::after { display: none; }
a.step:hover::before { transform: scale(1.5); }
a.step:hover b { color: var(--ink); }
.step.done b { color: var(--ink); }
.step.done::before { background: var(--mint); border-color: var(--mint); box-shadow: 0 0 12px rgba(147, 240, 200, 0.6); }
.step.done::after { background: linear-gradient(90deg, rgba(147, 240, 200, 0.35), rgba(147, 240, 200, 0.7)); }
.step.active b { color: var(--ice); }
.step.active::before { background: var(--ice); border-color: var(--ice); box-shadow: 0 0 0 6px var(--ice-soft), 0 0 22px var(--ice);
  animation: breathe 1.6s ease-in-out infinite; }
.step.failed b { color: var(--coral); }
.step.failed::before { background: var(--coral); border-color: var(--coral); }
.step.knocked b { color: var(--aura); }
.step.knocked::before { background: var(--aura); border-color: var(--aura); box-shadow: 0 0 0 6px var(--aura-soft), 0 0 22px var(--aura); }
.step.knocked::after { background: rgba(147, 240, 200, 0.7); }
.step.skipped { opacity: 0.35; }
@keyframes pulse { 50% { opacity: 0.35; } }
.timeline-error { color: var(--ice); font: 400 12px/1.4 var(--mono); }
.countdown { display: inline-block; margin-top: 4px; padding: 4px 9px; border-radius: 999px; font: 500 12.5px/1 var(--mono);
  font-variant-numeric: tabular-nums; color: var(--ice); background: var(--ice-soft); box-shadow: 0 0 18px rgba(166, 220, 255, 0.3); }
"""

STATE_WORDS = {"done": "done", "active": "now", "waiting": "queued", "failed": "failed",
               "skipped": "skipped", "todo": "", "knocked": ""}


def clock_text(deadline: str, now: dt.datetime | None = None) -> str:
    """'6:12 left', or 'deciding' once the vigil's time is up (the job still has to report)."""
    now = now or dt.datetime.now(dt.timezone.utc)
    seconds = int((dt.datetime.fromisoformat(deadline) - now).total_seconds())
    return "deciding" if seconds <= 0 else f"{seconds // 60}:{seconds % 60:02d} left"


def _vigil_detail(stage: dict) -> str:
    knocks = stage.get("knocks")
    heard = "" if knocks is None else f" &middot; {knocks} knock{'' if knocks == 1 else 's'}"
    return (f"<span class='countdown' data-deadline='{escape(stage['deadline'])}'>"
            f"{escape(clock_text(stage['deadline']))}</span>{heard}")


def _step(stage: dict) -> str:
    tag = "a" if stage["url"] else "span"
    href = f" href='{escape(stage['url'])}'" if stage["url"] else ""
    if stage.get("deadline"):
        detail = _vigil_detail(stage)
    else:
        word = STATE_WORDS[stage["state"]]
        detail = " &middot; ".join(escape(p) for p in (stage["note"], word) if p)
    return f"<{tag} class='step {stage['state']}'{href}><b>{escape(stage['label'])}</b>{detail}</{tag}>"


def render_timeline(timeline: list[dict], error: str | None = None) -> str:
    notice = f"<p class='timeline-error'>{escape(error)}</p>" if error else ""
    if not timeline:
        return notice + ("<p class='empty'>No retirement in progress. Open an issue titled "
                         "<code>AFTERLIFE census</code> to start one.</p>")
    cards = "".join(
        "<article class='retirement'><header>"
        f"<h3><a href='{escape(r['mr_url'])}'>{escape(r['feature'])}</a></h3>"
        f"<span class='outcome {escape(r['outcome'].replace(' ', '-'))}'>{escape(r['outcome'])}</span>"
        f"</header><div class='steps'>{''.join(_step(s) for s in r['stages'])}</div></article>"
        for r in timeline
    )
    return notice + f"<div class='timeline'>{cards}</div>"


# Re-fetches only the timeline section; the rest of the page is static.
REFRESH_SCRIPT = f"""<script>
(function () {{
  var box = document.getElementById('timeline');
  if (!box || !window.fetch) return;
  // Vigil countdowns tick every second between the 15-second refreshes.
  setInterval(function () {{
    box.querySelectorAll('.countdown[data-deadline]').forEach(function (el) {{
      var s = Math.floor((Date.parse(el.dataset.deadline) - Date.now()) / 1000);
      el.textContent = s <= 0 ? 'deciding' : Math.floor(s / 60) + ':' + String(s % 60).padStart(2, '0') + ' left';
    }});
  }}, 1000);
  setInterval(function () {{
    fetch('/graveyard/timeline', {{cache: 'no-store'}})
      .then(function (r) {{ return r.ok ? r.text() : null; }})
      .then(function (html) {{ if (html !== null) box.innerHTML = html; }})
      .catch(function () {{}});
  }}, {REFRESH_MS});
}})();
</script>"""
