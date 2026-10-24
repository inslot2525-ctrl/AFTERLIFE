"""Coma: switch a feature's GitLab feature flag off (or back on) in production.

With the flag off, Shelf answers 410 Gone and logs each request as a knock
(app/gate.py). Nothing is deleted. The flag name is the feature name.

    python -m ci.coma --feature books_v1          # off
    python -m ci.coma --feature books_v1 --on     # back on
"""

from __future__ import annotations

import argparse
import datetime as dt
import os

from ci.gitlab import GitLab


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--feature", required=True)
    parser.add_argument("--on", action="store_true", help="turn the flag back on")
    args = parser.parse_args()

    gitlab = GitLab()
    gitlab.set_flag(args.feature, active=args.on)
    now = dt.datetime.now(dt.timezone.utc)
    state = "on" if args.on else "off"
    print(f"Flag {args.feature} is {state} in production ({now:%Y-%m-%d %H:%M} UTC).")

    iid = os.environ.get("CI_MERGE_REQUEST_IID")
    if iid and not args.on:
        gitlab.comment_mr(iid, (
            f":zzz: **Coma.** Flag `{args.feature}` is off in production since {now:%Y-%m-%d %H:%M} UTC. "
            "The route now returns `410 Gone` and every request is logged as a knock. "
            "The vigil is listening; one knock resurrects it."
        ))


if __name__ == "__main__":
    main()
