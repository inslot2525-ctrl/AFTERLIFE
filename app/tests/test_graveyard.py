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
