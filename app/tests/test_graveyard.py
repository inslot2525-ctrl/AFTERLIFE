from app.graveyard import render, totals
from app.store import JsonFileStore

LEDGER = {
    "retired": [
        {"feature": "books_v1", "route": "/v1/books", "born": "2023-02-14", "died": "2026-10-25",
         "cause": "0 calls in 30 days, silent 201 days"},
        {"feature": "import_goodreads", "route": "/import/goodreads", "born": "2023-06-30", "died": "2026-10-25",
         "cause": "never called"},
    ],
    "hibernating": [{"feature": "wrapped", "reason": "busy every December", "recheck": "2026-12-01"}],
    "resurrected": [],
    "protected": [{"feature": "admin_reindex", "reason": "Admin path"}],
}

SAVINGS = {
    "import_goodreads": {
        "feature": "import_goodreads", "mr_iid": 3, "lines_removed": 48, "deps_removed": ["requests"],
        "cves_removed": ["PYSEC-1", "PYSEC-2"], "image_mb_saved": 1.2,
        "sci": {"delta_gco2e": 0.0123}, "mr_url": "https://gitlab.com/x/-/merge_requests/3",
    },
}


def test_totals_count_only_measured_retirements():
    t = totals(LEDGER["retired"], SAVINGS)
    assert t == {"retired": 2, "lines_removed": 48, "deps_removed": 1, "cves_removed": 2,
                 "image_mb_saved": 1.2, "sci_gco2e_saved": 0.0123}


def test_totals_without_sci_stay_empty():
    assert totals(LEDGER["retired"], {})["sci_gco2e_saved"] is None


def test_page_shows_measured_numbers_and_admits_missing_ones():
    html = render(LEDGER, SAVINGS)
    assert "2 CVEs removed" in html and "deps: requests" in html
    assert "merge_requests/3" in html
    # books_v1 has a tombstone but no savings yet: say so, show no number.
    assert html.count("Savings not measured yet") == 1


def test_page_lists_kept_features():
    html = render(LEDGER, {})
    assert "busy every December" in html and "admin_reindex" in html
    assert "Nobody has knocked yet." in html


def test_page_escapes_ledger_text():
    ledger = {**LEDGER, "retired": [{"feature": "<script>x</script>", "cause": "a & b"}]}
    html = render(ledger, {})
    assert "<script>x" not in html and "&lt;script&gt;" in html


def test_json_store_keeps_savings(tmp_path):
    path = tmp_path / "store.json"
    JsonFileStore(path).record_savings("books_v1", {"feature": "books_v1", "lines_removed": 20})
    assert JsonFileStore(path).all_savings() == {"books_v1": {"feature": "books_v1", "lines_removed": 20}}


def test_census_rows_put_silent_features_first():
    import datetime as dt

    from app.graveyard import census_rows
    from app.tests.planted import PLANTED_FEATURES
    from app.store import InMemoryStore

    today = dt.date(2026, 10, 24)
    store = InMemoryStore()
    store.record_hit("books_v2", today, 5)
    store.record_hit("books_v1", today - dt.timedelta(days=200), 3)
    rows = {r["feature"]: r for r in census_rows(PLANTED_FEATURES, store, 30, today)}

    assert rows["books_v2"] == {"feature": "books_v2", "route": "/v2/books", "calls_in_window": 5,
                                     "last_seen": "2026-10-24", "days_silent": 0, "candidate": "no"}
    assert rows["books_v1"]["days_silent"] == 200 and rows["books_v1"]["candidate"] == "yes"
    assert rows["import_goodreads"]["last_seen"] == "never"
    ordered = [r["feature"] for r in census_rows(PLANTED_FEATURES, store, 30, today)]
    assert ordered[-1] == "books_v2"


def test_page_shows_census_and_obituary_link():
    savings = {"import_goodreads": {**SAVINGS["import_goodreads"], "obituary_url": "https://gitlab.com/x/-/issues/1"}}
    census = [{"feature": "books_v1", "route": "/v1/books", "calls_in_window": 0, "last_seen": "2026-04-06",
               "days_silent": 201, "candidate": "yes"}]
    html = render(LEDGER, savings, census, 30)
    assert "Calls, last 30 days" in html and "2026-04-06" in html
    assert "issues/1'>Obituary" in html


def test_totals_show_megabytes_with_one_decimal():
    html = render(LEDGER, {"import_goodreads": {**SAVINGS["import_goodreads"], "image_mb_saved": 0.6}})
    assert "<b>0.6</b>" in html and "0.6000" not in html
    assert "<b>0.0123</b>" in html


def test_census_marks_protected_features_and_formats_knock_times():
    census = [{"feature": "admin_reindex", "route": "/admin/reindex", "calls_in_window": 0,
               "last_seen": "2025-12-30", "days_silent": 300, "candidate": "yes"},
              {"feature": "books_v2", "route": "/v2/books", "calls_in_window": 3218,
               "last_seen": "2026-10-26", "days_silent": 0, "candidate": "no"}]
    ledger = {**LEDGER, "resurrected": [{"feature": "embed_widget", "caller": "acme",
                                         "knocked_at": "2026-10-26T12:03:00Z", "reason": "partner", "recheck": "2027-01-26"}]}
    html = render(ledger, {}, census, 30)
    assert "pill protected'>protected" in html and "pill candidate" not in html
    assert "3,218" in html and "pill alive'>in use" in html
    assert "2026-10-26 12:03 UTC" in html
