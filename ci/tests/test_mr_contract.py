"""The Sunset MR description is a contract between the Undertaker and CI.

This is the layout flows/afterlife-retire.yml tells the Undertaker to write.
If a parser or the prompt changes, this test should change with it.
"""

import yaml

from ci.obituary import census_issue
from ci.release_notes import deprecation_note
from ci.verdict_check import parse_verdicts

DESCRIPTION = """Census-Issue: #12

### Death certificate
books_v1 is DEAD: 0 calls in 30 days, silent 201 days, no callers in app/.

### Deprecation note
`GET /v1/books` is gone. Use `GET /v2/books`.

### Verdict
```afterlife-verdict
{"feature": "books_v1", "verdict": "DEAD", "confidence": 0.93, "evidence": ["0 calls in 30 days"],
 "files": ["app/features/books_v1.py"], "dependencies": [], "recheck": null}
```
"""


def test_every_ci_parser_reads_the_undertaker_layout():
    assert census_issue(DESCRIPTION) == 12
    assert deprecation_note(DESCRIPTION) == "`GET /v1/books` is gone. Use `GET /v2/books`."
    [verdict] = parse_verdicts(DESCRIPTION)
    assert verdict["feature"] == "books_v1" and verdict["verdict"] == "DEAD"


def test_prompt_still_describes_that_layout():
    flow = yaml.safe_load(open("flows/afterlife-retire.yml", encoding="utf-8"))
    undertaker = next(p for p in flow["prompts"] if p["prompt_id"] == "afterlife_undertaker")
    system = undertaker["prompt_template"]["system"]
    for marker in ("Census-Issue: #", "### Deprecation note", "### Verdict", "afterlife-verdict"):
        assert marker in system
    reviewer = next(p for p in flow["prompts"] if p["prompt_id"] == "afterlife_reviewer")
    assert "AFTERLIFE-REVIEW: PASS" in reviewer["prompt_template"]["system"]
