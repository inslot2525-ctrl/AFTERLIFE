import datetime as dt

import pytest

from app.tests.planted import PLANTED_FEATURES
from app.store import InMemoryStore
from ci.census import build_census, parse_vulture
from ci.policy import load_policy
from scripts.seed_history import seed

TODAY = dt.date(2026, 10, 24)


@pytest.fixture(scope="module")
def census():
    store = InMemoryStore()
    seed(store, TODAY)
    return {f["feature"]: f for f in build_census(PLANTED_FEATURES, store, load_policy(), TODAY)["features"]}


def test_live_feature_is_not_a_candidate(census):
    assert census["books_v2"]["calls_in_window"] > 0
    assert not census["books_v2"]["candidate"]


def test_legacy_api_is_a_clean_candidate(census):
    v1 = census["books_v1"]
    assert v1["candidate"] and not v1["seasonal_suspect"] and not v1["protected"]
    assert v1["days_silent"] >= 200


def test_never_called_feature_has_no_last_seen(census):
    assert census["import_goodreads"]["last_seen"] is None
    assert census["import_goodreads"]["candidate"]


def test_december_feature_is_flagged_seasonal(census):
    assert census["wrapped"]["seasonal_suspect"]


def test_partner_widget_looks_dead(census):
    widget = census["embed_widget"]
    assert widget["candidate"] and not widget["seasonal_suspect"]
    assert widget["days_silent"] == 71


def test_admin_path_is_protected(census):
    assert census["admin_reindex"]["protected"]


def test_seeded_history_is_marked_simulated(census):
    assert census["books_v2"]["simulated_share"] == 1.0


def test_parse_vulture_groups_by_file():
    output = (
        "app/features/books_v1.py:22: unused function 'list_books_v1' (60% confidence)\n"
        "app\\catalog.py:12: unused function 'add_books' (60% confidence)\n"
    )
    findings = parse_vulture(output)
    assert findings["app/features/books_v1.py"] == ["line 22: unused function 'list_books_v1' (60% confidence)"]
    assert "app/catalog.py" in findings


def test_partner_widget_fades_out_instead_of_stopping(census):
    # An abrupt stop reads as a measurement gap; a fade reads as a dying integration.
    months = list(census["embed_widget"]["monthly_calls"].values())
    steady, fading, last = max(months), months[-2], months[-1]
    assert 0 < last < fading < steady / 2
