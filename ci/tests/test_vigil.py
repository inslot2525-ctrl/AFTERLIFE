import datetime as dt

from app.store import InMemoryStore
from ci.vigil import decide, run_vigil

START = dt.datetime(2026, 10, 25, 12, 0, tzinfo=dt.timezone.utc)


class FakeClock:
    def __init__(self):
        self.now = START

    def __call__(self):
        return self.now

    def sleep(self, seconds):
        self.now += dt.timedelta(seconds=seconds)


def test_decide():
    assert decide(0, 3, 10) == "waiting"
    assert decide(0, 10, 10) == "pass"
    assert decide(1, 3, 10) == "resurrect"


def test_silent_vigil_passes():
    clock = FakeClock()
    decision, knocks = run_vigil(InMemoryStore(), "books_v1", 10, now=clock, sleep=clock.sleep)
    assert decision == "pass" and knocks == []
    assert clock.now - START >= dt.timedelta(minutes=10)


def test_knock_resurrects():
    store = InMemoryStore()
    clock = FakeClock()

    def sleep_then_knock(seconds):
        clock.sleep(seconds)
        store.record_knock("embed_widget", "acme", clock.now)

    decision, knocks = run_vigil(store, "embed_widget", 10, now=clock, sleep=sleep_then_knock)
    assert decision == "resurrect"
    assert knocks[0]["caller"] == "acme"


def test_knocks_before_vigil_are_ignored():
    store = InMemoryStore()
    store.record_knock("books_v1", "old", START - dt.timedelta(hours=1))
    clock = FakeClock()
    decision, _ = run_vigil(store, "books_v1", 1, now=clock, sleep=clock.sleep)
    assert decision == "pass"
