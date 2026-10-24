from app.verdicts import latest_verdicts, parse_verdicts, with_verdicts

NOTE = """Census results

```afterlife-verdict
{"feature": "wrapped", "verdict": "HIBERNATING", "confidence": 0.9,
 "evidence": ["0 calls in 30 days", "busy only in December"], "files": [], "recheck": "2026-12-01"}
```

```afterlife-verdict
{"feature": "admin_reindex", "verdict": "PROTECTED", "confidence": 1, "evidence": ["protected path"], "files": []}
```

```afterlife-verdict
not json
```
"""

LEDGER = {"retired": [{"feature": "books_v1"}], "hibernating": [], "resurrected": [],
          "protected": [{"feature": "admin_reindex", "reason": "Admin path"}]}


def fake_gitlab(issues, notes):
    def fetch(path):
        if path.startswith("/issues?"):
            return issues
        return notes[int(path.split("/")[2])]
    return fetch


def test_parse_skips_malformed_blocks():
    assert [v["feature"] for v in parse_verdicts(NOTE)] == ["wrapped", "admin_reindex"]


def test_newest_census_issue_with_verdicts_wins():
    fetch = fake_gitlab(
        [{"iid": 7, "title": "AFTERLIFE census 2"}, {"iid": 3, "title": "Unrelated bug"}, {"iid": 1, "title": "AFTERLIFE census"}],
        {7: [{"body": "Coroner is thinking..."}, {"body": NOTE}], 1: [{"body": "old"}]},
    )
    verdicts, issue = latest_verdicts(fetch)
    assert issue["iid"] == 7 and len(verdicts) == 2


def test_hibernating_verdicts_join_the_ledger_once():
    verdicts = parse_verdicts(NOTE)
    merged = with_verdicts(LEDGER, verdicts, {"iid": 7})
    assert merged["hibernating"] == [{"feature": "wrapped", "reason": "0 calls in 30 days; busy only in December",
                                      "recheck": "2026-12-01", "source": "Coroner, census #7"}]
    assert merged["protected"] == LEDGER["protected"]  # already in the ledger: not duplicated
    assert with_verdicts(merged, verdicts, {"iid": 7})["hibernating"] == merged["hibernating"]


def test_no_verdicts_leaves_the_ledger_alone():
    assert with_verdicts(LEDGER, [], None) is LEDGER
