"""Seed 400 days of SIMULATED usage history, one profile per planted feature.

Every seeded call is marked simulated, and the census reports the simulated
share, so the demo never passes off generated traffic as real.

    AFTERLIFE_STORE=firestore python -m scripts.seed_history
"""

from __future__ import annotations

import argparse
import datetime as dt
import random

from app.store import UsageStore, store_from_env

LOOKBACK_DAYS = 400


def seed(store: UsageStore, today: dt.date, rng_seed: int = 7) -> None:
    rng = random.Random(rng_seed)

    def hit(feature: str, days_ago: int, n: int) -> None:
        if n > 0:
            store.record_hit(feature, today - dt.timedelta(days=days_ago), n, simulated=True)

    for days_ago in range(LOOKBACK_DAYS - 1, -1, -1):
        # books_v2: the live API, busy every day.
        hit("books_v2", days_ago, rng.randint(80, 140))
        # books_v1: traffic drained away after v2 shipped; silent for ~200 days.
        if days_ago > 200:
            hit("books_v1", days_ago, round(60 * (days_ago - 200) / 200) + rng.randint(0, 3))
        # embed_widget: steady partner traffic that faded out over two months and
        # went silent 71 days ago, the way a forgotten integration dies. (An abrupt
        # stop reads as a measurement gap, and the Coroner rightly won't call it.)
        if days_ago > 130:
            hit("embed_widget", days_ago, rng.randint(3, 8))
        elif days_ago > 70:
            share = (days_ago - 70) / 60  # 1.0 two months ago, falling to 0
            calls = rng.randint(1, max(1, round(5 * share))) if rng.random() < share else 0
            hit("embed_widget", days_ago, max(calls, 1 if days_ago == 71 else 0))

    # wrapped: busy every December, a short tail into January, otherwise silent.
    december = dt.date(today.year - 1, 12, 1)
    for offset in range(31):
        hit("wrapped", (today - (december + dt.timedelta(days=offset))).days, rng.randint(30, 90))
    for offset in range(7):
        hit("wrapped", (today - dt.date(today.year, 1, 1 + offset)).days, rng.randint(2, 6))

    # admin_reindex: one incident, long ago. Protected regardless.
    hit("admin_reindex", 300, 2)
    # import_goodreads: no calls in the whole lookback.


SEEDED_FEATURES = ["books_v1", "books_v2", "import_goodreads", "wrapped", "embed_widget", "admin_reindex"]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--today", type=dt.date.fromisoformat, default=dt.date.today())
    parser.add_argument("--reset", action="store_true",
                        help="delete existing usage for the seeded features first (seeding adds to counts)")
    args = parser.parse_args()
    store = store_from_env()
    if args.reset:
        for feature in SEEDED_FEATURES:
            store.clear_usage(feature)
        print(f"Cleared usage for {', '.join(SEEDED_FEATURES)}.")
    seed(store, args.today)
    print(f"Seeded {LOOKBACK_DAYS} days of simulated history ending {args.today}.")


if __name__ == "__main__":
    main()
