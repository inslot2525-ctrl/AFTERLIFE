"""Canary watch: judge the new Cloud Run revision at partial traffic, then say
promote or rollback. Writes canary.json and canary.env (CANARY_RESULT).

Signals: 5xx rate and p95 latency of the canary revision from Cloud
Monitoring, plus a synthetic check on the revision's tagged URL: /health must
answer 200, and a feature retired by this merge must be gone.

    python -m ci.canary_watch --policy target-policy.yaml --census census.json
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from ci.policy import DEFAULT_POLICY, load_policy

RETIRE_MESSAGE = re.compile(r"AFTERLIFE: retire ([a-z0-9][a-z0-9_-]*) via !\d+")


def retired_feature(commit_message: str) -> str | None:
    match = RETIRE_MESSAGE.search(commit_message or "")
    return match.group(1) if match else None


def decide(requests: int, errors_5xx: int, p95_ms: float | None, synthetic_ok: bool,
           policy: dict) -> tuple[str, list[str]]:
    canary = policy["canary"]
    problems = []
    if not synthetic_ok:
        problems.append("synthetic check failed")
    # Too little traffic makes a rate meaningless; the synthetic check decides alone.
    if requests >= canary.get("min_requests", 20):
        rate = errors_5xx / requests
        if rate > canary["max_5xx_rate"]:
            problems.append(f"5xx rate {rate:.2%} above {canary['max_5xx_rate']:.2%}")
        limit = canary.get("max_p95_latency_ms", 1500)
        if p95_ms is not None and p95_ms > limit:
            problems.append(f"p95 latency {p95_ms:.0f} ms above {limit} ms")
    return ("rollback" if problems else "promote"), problems


def http_status(url: str) -> int:
    try:
        with urllib.request.urlopen(url, timeout=15) as response:
            return response.status
    except urllib.error.HTTPError as e:
        return e.code
    except urllib.error.URLError:
        return 0


def synthetic_ok(base_url: str, retired_route: str | None) -> bool:
    # Not /healthz: Cloud Run reserves paths ending in "z" and answers them itself with 404.
    if http_status(f"{base_url}/health") != 200:
        return False
    if retired_route:
        # /wrapped/{year} -> /wrapped/2025; the route must no longer exist (or be flagged off).
        path = re.sub(r"\{[^}]+\}", "2025", retired_route)
        if http_status(base_url + path) not in (404, 405, 410):
            return False
    return True


def revision_metrics(project: str, service: str, revision: str, minutes: int,
                     client=None) -> tuple[int, int, float | None]:
    from google.cloud import monitoring_v3

    client = client or monitoring_v3.MetricServiceClient()
    end = dt.datetime.now(dt.timezone.utc)
    interval = monitoring_v3.TimeInterval(end_time=end, start_time=end - dt.timedelta(minutes=minutes))
    scope = (f'resource.type="cloud_run_revision" AND resource.labels.service_name="{service}" '
             f'AND resource.labels.revision_name="{revision}"')
    full = monitoring_v3.ListTimeSeriesRequest.TimeSeriesView.FULL

    # list_time_series takes its options as one request; aggregation is not a keyword argument.
    requests = errors = 0
    for series in client.list_time_series(request={
        "name": f"projects/{project}", "interval": interval, "view": full,
        "filter": f'metric.type="run.googleapis.com/request_count" AND {scope}',
    }):
        n = sum(point.value.int64_value for point in series.points)
        requests += n
        if series.metric.labels.get("response_code_class") == "5xx":
            errors += n

    p95 = None
    aggregation = monitoring_v3.Aggregation(
        alignment_period={"seconds": minutes * 60},
        per_series_aligner=monitoring_v3.Aggregation.Aligner.ALIGN_PERCENTILE_95,
    )
    for series in client.list_time_series(request={
        "name": f"projects/{project}", "interval": interval, "view": full, "aggregation": aggregation,
        "filter": f'metric.type="run.googleapis.com/request_latencies" AND {scope}',
    }):
        for point in series.points:
            p95 = max(p95 or 0.0, point.value.double_value)
    return requests, errors, p95


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--census", help="census/latest.json, to find the retired feature's route")
    parser.add_argument("--minutes", type=int, help="override policy canary.watch_minutes")
    args = parser.parse_args()

    policy = load_policy(args.policy)
    minutes = args.minutes or policy["canary"]["watch_minutes"]
    feature = retired_feature(os.environ.get("CI_COMMIT_MESSAGE", ""))
    route = None
    if feature and args.census and Path(args.census).exists():
        entries = json.loads(Path(args.census).read_text())["features"]
        route = next((f["route"] for f in entries if f["feature"] == feature), None)

    base_url, revision = os.environ["CANARY_URL"], os.environ["CANARY_REVISION"]
    print(f"Watching {revision} for {minutes} min" + (f"; {route} must be gone" if route else ""), flush=True)
    ok = True
    deadline = time.monotonic() + minutes * 60
    while time.monotonic() < deadline:  # keep probing so the canary actually serves traffic
        ok = synthetic_ok(base_url, route) and ok
        time.sleep(15)

    try:
        requests, errors, p95 = revision_metrics(
            os.environ["GCP_PROJECT_ID"], os.environ.get("SERVICE", "shelf"), revision, minutes)
        result, problems = decide(requests, errors, p95, ok, policy)
    except Exception as error:  # noqa: BLE001 - any failure here must still end in a decision
        # Never promote an unverified revision, and never leave traffic split: roll back.
        requests, errors, p95 = 0, 0, None
        result, problems = "rollback", [f"metrics unavailable: {type(error).__name__}: {error}"]
    Path("canary.json").write_text(json.dumps({
        "revision": revision, "requests": requests, "errors_5xx": errors, "p95_ms": p95,
        "synthetic_ok": ok, "result": result, "problems": problems,
    }, indent=2))
    Path("canary.env").write_text(f"CANARY_RESULT={result}\n")
    print(f"Canary: {result.upper()} (requests={requests}, 5xx={errors}, p95={p95}) {problems or ''}")


if __name__ == "__main__":
    main()
