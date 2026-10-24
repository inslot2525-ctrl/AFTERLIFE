"""Vigil: with the flag off, wait for knocks before anything is deleted.

Exits 0 when the vigil passes (gate-merge may run) and 1 on a knock, so the
`resurrect` job can run with `when: on_failure`. Writes vigil.json either way.

    python -m ci.vigil --feature books_v1 --minutes 10
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import time
from pathlib import Path
from typing import Callable

from app.store import UsageStore, store_from_env
from ci.policy import DEFAULT_POLICY, load_policy


def decide(knock_count: int, elapsed_minutes: float, vigil_minutes: float) -> str:
    if knock_count > 0:
        return "resurrect"
    if elapsed_minutes >= vigil_minutes:
        return "pass"
    return "waiting"


def run_vigil(
    store: UsageStore,
    feature: str,
    vigil_minutes: float,
    now: Callable[[], dt.datetime] = lambda: dt.datetime.now(dt.timezone.utc),
    sleep: Callable[[float], None] = time.sleep,
    poll_seconds: float = 30,
) -> tuple[str, list[dict]]:
    started = now()
    while True:
        knocks = store.knocks(feature, since=started)
        elapsed = (now() - started).total_seconds() / 60
        decision = decide(len(knocks), elapsed, vigil_minutes)
        print(f"[vigil] {feature}: {elapsed:.1f}/{vigil_minutes} min, {len(knocks)} knock(s) -> {decision}", flush=True)
        if decision != "waiting":
            return decision, knocks
        sleep(poll_seconds)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", required=True)
    parser.add_argument("--policy", default=str(DEFAULT_POLICY))
    parser.add_argument("--minutes", type=float, help="override policy vigil_minutes")
    parser.add_argument("--out", default="vigil.json")
    args = parser.parse_args()

    minutes = args.minutes if args.minutes is not None else load_policy(args.policy)["vigil_minutes"]
    decision, knocks = run_vigil(store_from_env(), args.feature, minutes)
    Path(args.out).write_text(json.dumps({"feature": args.feature, "decision": decision, "knocks": knocks}, indent=2))
    sys.exit(0 if decision == "pass" else 1)


if __name__ == "__main__":
    main()
