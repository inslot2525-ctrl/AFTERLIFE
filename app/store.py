"""Usage storage: per-feature daily call counts, the knock log, and savings.

A knock is a request to a feature whose flag is off. During a vigil, one knock
is enough to resurrect the feature. Savings are the measured results CI's
measure job publishes after a retirement ships; /graveyard shows them.
"""

from __future__ import annotations

import datetime as dt
import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Protocol


class UsageStore(Protocol):
    def record_hit(self, feature: str, day: dt.date, n: int = 1, simulated: bool = False) -> None: ...

    def record_knock(self, feature: str, caller: str, at: dt.datetime, user_agent: str = "") -> None: ...

    def daily_counts(self, feature: str) -> dict[dt.date, dict[str, int]]: ...

    def knocks(self, feature: str, since: dt.datetime) -> list[dict]: ...

    def record_savings(self, feature: str, savings: dict) -> None: ...

    def all_savings(self) -> dict[str, dict]: ...


class InMemoryStore:
    def __init__(self) -> None:
        self._days: dict[str, dict[dt.date, dict[str, int]]] = defaultdict(dict)
        self._knocks: list[dict] = []
        self._savings: dict[str, dict] = {}

    def record_hit(self, feature: str, day: dt.date, n: int = 1, simulated: bool = False) -> None:
        row = self._days[feature].setdefault(day, {"count": 0, "simulated": 0})
        row["count"] += n
        if simulated:
            row["simulated"] += n

    def record_knock(self, feature: str, caller: str, at: dt.datetime, user_agent: str = "") -> None:
        self._knocks.append({"feature": feature, "caller": caller, "user_agent": user_agent, "at": at.isoformat()})

    def daily_counts(self, feature: str) -> dict[dt.date, dict[str, int]]:
        return {day: dict(row) for day, row in self._days[feature].items()}

    def knocks(self, feature: str, since: dt.datetime) -> list[dict]:
        return [
            k for k in self._knocks
            if k["feature"] == feature and dt.datetime.fromisoformat(k["at"]) >= since
        ]

    def record_savings(self, feature: str, savings: dict) -> None:
        self._savings[feature] = savings

    def all_savings(self) -> dict[str, dict]:
        return dict(self._savings)


class JsonFileStore(InMemoryStore):
    """Local development store that survives restarts. Not for production."""

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self._path = Path(path)
        if self._path.exists():
            data = json.loads(self._path.read_text())
            for feature, days in data["days"].items():
                self._days[feature] = {dt.date.fromisoformat(d): row for d, row in days.items()}
            self._knocks = data["knocks"]
            self._savings = data.get("savings", {})

    def _save(self) -> None:
        data = {
            "days": {
                feature: {d.isoformat(): row for d, row in days.items()}
                for feature, days in self._days.items()
            },
            "knocks": self._knocks,
            "savings": self._savings,
        }
        self._path.write_text(json.dumps(data))

    def record_hit(self, feature: str, day: dt.date, n: int = 1, simulated: bool = False) -> None:
        super().record_hit(feature, day, n, simulated)
        self._save()

    def record_knock(self, feature: str, caller: str, at: dt.datetime, user_agent: str = "") -> None:
        super().record_knock(feature, caller, at, user_agent)
        self._save()

    def record_savings(self, feature: str, savings: dict) -> None:
        super().record_savings(feature, savings)
        self._save()


class FirestoreStore:
    """usage/{feature}/days/{YYYY-MM-DD} holds counts; knocks/ holds the knock log."""

    def __init__(self, client=None) -> None:
        from google.cloud import firestore

        self._firestore = firestore
        self._db = client or firestore.Client()

    def record_hit(self, feature: str, day: dt.date, n: int = 1, simulated: bool = False) -> None:
        update = {"count": self._firestore.Increment(n)}
        if simulated:
            update["simulated"] = self._firestore.Increment(n)
        (
            self._db.collection("usage").document(feature)
            .collection("days").document(day.isoformat())
            .set(update, merge=True)
        )

    def record_knock(self, feature: str, caller: str, at: dt.datetime, user_agent: str = "") -> None:
        self._db.collection("knocks").add(
            {"feature": feature, "caller": caller, "user_agent": user_agent, "at": at.isoformat()}
        )

    def daily_counts(self, feature: str) -> dict[dt.date, dict[str, int]]:
        days = self._db.collection("usage").document(feature).collection("days").stream()
        counts = {}
        for doc in days:
            data = doc.to_dict()
            counts[dt.date.fromisoformat(doc.id)] = {
                "count": data.get("count", 0),
                "simulated": data.get("simulated", 0),
            }
        return counts

    def knocks(self, feature: str, since: dt.datetime) -> list[dict]:
        from google.cloud.firestore_v1 import FieldFilter

        docs = self._db.collection("knocks").where(filter=FieldFilter("feature", "==", feature)).stream()
        # Filtering time in Python avoids needing a composite index.
        return [
            doc.to_dict() for doc in docs
            if dt.datetime.fromisoformat(doc.to_dict()["at"]) >= since
        ]

    def record_savings(self, feature: str, savings: dict) -> None:
        self._db.collection("savings").document(feature).set(savings)

    def all_savings(self) -> dict[str, dict]:
        return {doc.id: doc.to_dict() for doc in self._db.collection("savings").stream()}


def store_from_env() -> UsageStore:
    """AFTERLIFE_STORE = firestore | json:<path> | memory (default)."""
    choice = os.environ.get("AFTERLIFE_STORE", "memory")
    if choice == "firestore":
        return FirestoreStore()
    if choice.startswith("json:"):
        return JsonFileStore(choice.removeprefix("json:"))
    return InMemoryStore()
