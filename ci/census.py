"""Census: join usage history with static analysis into census/latest.json.

The census reports signals; it does not decide. The Coroner agent writes the
verdicts, and verdict_check enforces the hard rules on them.

    python -m ci.census --out census/latest.json --vulture
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path

from app.registry import Feature
from app.store import UsageStore, store_from_env
from ci.policy import DEFAULT_POLICY, is_protected, load_policy

VULTURE_LINE = re.compile(r"^(?P<path>[^:]+):(?P<line>\d+): (?P<message>.+)$")


def feature_signals(feature: Feature, store: UsageStore, policy: dict, today: dt.date) -> dict:
    counts = store.daily_counts(feature.name)
    window_start = today - dt.timedelta(days=policy["census_window_days"])
    lookback_start = today - dt.timedelta(days=policy["lookback_days"])

    calls_in_window = sum(row["count"] for day, row in counts.items() if window_start < day <= today)
    seen = [day for day, row in counts.items() if row["count"] > 0 and day <= today]
    last_seen = max(seen) if seen else None

    monthly: dict[str, int] = defaultdict(int)
    total = simulated = 0
    for day, row in counts.items():
        if lookback_start < day <= today:
            monthly[day.strftime("%Y-%m")] += row["count"]
            total += row["count"]
            simulated += row.get("simulated", 0)
    active_months = sum(1 for n in monthly.values() if n > 0)
    peak = max(monthly.values(), default=0)
    seasonal = policy["seasonal"]

    return {
        "feature": feature.name,
        "route": feature.route,
        "module": feature.module,
        "owner": feature.owner,
        "born": feature.born,
        "summary": feature.summary,
        "calls_in_window": calls_in_window,
        "last_seen": last_seen.isoformat() if last_seen else None,
        # None means no call anywhere in the stored history.
        "days_silent": (today - last_seen).days if last_seen else None,
        "monthly_calls": dict(sorted(monthly.items())),
        "active_months": active_months,
        "seasonal_suspect": (
            calls_in_window == 0
            and 0 < active_months <= seasonal["max_active_months"]
            and peak >= seasonal["min_peak_calls"]
        ),
        "protected": is_protected(feature.module, policy),
        "candidate": calls_in_window == 0,
        "simulated_share": round(simulated / total, 3) if total else None,
    }


def parse_vulture(output: str) -> dict[str, list[str]]:
    findings: dict[str, list[str]] = defaultdict(list)
    for line in output.splitlines():
        match = VULTURE_LINE.match(line.strip())
        if match:
            path = match["path"].replace("\\", "/")
            findings[path].append(f"line {match['line']}: {match['message']}")
    return dict(findings)


def run_vulture(paths: list[str]) -> dict[str, list[str]]:
    result = subprocess.run(
        ["vulture", *paths, "--min-confidence", "60", "--exclude", "app/tests"],
        capture_output=True, text=True, check=False,
    )
    return parse_vulture(result.stdout)


def build_census(
    features: list[Feature],
    store: UsageStore,
    policy: dict,
    today: dt.date,
    static_findings: dict[str, list[str]] | None = None,
) -> dict:
    static_findings = static_findings or {}
    entries = []
    first_day = None
    for feature in features:
        signals = feature_signals(feature, store, policy, today)
        signals["static_unused"] = static_findings.get(feature.module, [])
        entries.append(signals)
        days = [day for day in store.daily_counts(feature.name) if day <= today]
        if days and (first_day is None or min(days) < first_day):
            first_day = min(days)
    return {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "today": today.isoformat(),
        "window_days": policy["census_window_days"],
        # How long usage has been recorded at all. A project that just adopted
        # AFTERLIFE has none, and "never called" then means "not watched yet".
        "observed_since": first_day.isoformat() if first_day else None,
        "history_days": (today - first_day).days if first_day else 0,
        "features": entries,
    }


def main() -> None:
    from app.features import FEATURES

    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="census/latest.json")
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    parser.add_argument("--vulture", action="store_true", help="add static unused-code findings")
    args = parser.parse_args()

    findings = run_vulture(["app"]) if args.vulture else None
    census = build_census(FEATURES, store_from_env(), load_policy(args.policy), args.today, findings)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(census, indent=2))
    candidates = [f["feature"] for f in census["features"] if f["candidate"]]
    print(f"Census written to {out}. Candidates: {', '.join(candidates) or 'none'}")


if __name__ == "__main__":
    main()
