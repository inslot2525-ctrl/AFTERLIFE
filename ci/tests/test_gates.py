import pytest

from ci.canary_watch import decide as canary_decide
from ci.canary_watch import retired_feature
from ci.gate_merge import decide as gate_decide
from ci.gate_merge import merge_message
from ci.gitlab import GitLabError, feature_from_branch
from ci.policy import load_policy
from ci.review_check import latest_review


@pytest.fixture(scope="module")
def policy():
    return load_policy()


PASSED = {"feature": "books_v1", "decision": "pass", "knocks": []}
DIFF = ["app/features/books_v1.py", "app/features/__init__.py", "afterlife/graveyard.yaml"]


def test_feature_from_branch():
    assert feature_from_branch("afterlife/books_v1") == "books_v1"
    for bad in ("main", "afterlife/census", "afterlife/../main", "afterlife/Books V1"):
        with pytest.raises(GitLabError):
            feature_from_branch(bad)


def test_gate_merges_after_silent_vigil(policy):
    assert gate_decide("books_v1", PASSED, DIFF, policy, codeowner_approved=False) == []


def test_gate_refuses_without_a_passed_vigil(policy):
    assert gate_decide("books_v1", None, DIFF, policy, False)
    assert gate_decide("books_v1", {**PASSED, "decision": "resurrect"}, DIFF, policy, False)
    assert gate_decide("books_v1", {**PASSED, "feature": "wrapped"}, DIFF, policy, False)


def test_gate_refuses_protected_paths_but_allows_collateral(policy):
    problems = gate_decide("books_v1", PASSED, DIFF + ["ci/vigil.py"], policy, True)
    assert problems == ["ci/vigil.py: protected path in the diff"]


def test_gate_requires_codeowner_when_policy_says(policy):
    supervised = {**policy, "requires_approval": ["books_v1"]}
    assert gate_decide("books_v1", PASSED, DIFF, supervised, False) == ["books_v1 requires a CODEOWNERS approval"]
    assert gate_decide("books_v1", PASSED, DIFF, supervised, True) == []


def test_merge_message_round_trips_to_the_canary():
    assert retired_feature(merge_message("import_goodreads", 12)) == "import_goodreads"
    assert retired_feature("Merge branch 'feature/x' into 'main'") is None


def test_review_latest_from_agent_wins():
    notes = [
        {"author": {"username": "afterlife-bot"}, "body": "AFTERLIFE-REVIEW: PASS"},
        {"author": {"username": "someone"}, "body": "AFTERLIFE-REVIEW: BLOCK"},
    ]
    assert latest_review(notes, "afterlife-bot") == "PASS"
    assert latest_review(notes, None) == "BLOCK"
    later_block = {"author": {"username": "afterlife-bot"}, "body": "AFTERLIFE-REVIEW: BLOCK\nwhy"}
    assert latest_review(notes + [later_block], "afterlife-bot") == "BLOCK"


def test_review_must_start_a_line():
    assert latest_review([{"body": "quoting AFTERLIFE-REVIEW: PASS"}], None) is None


def test_canary_promotes_healthy_revision(policy):
    assert canary_decide(500, 1, 300.0, True, policy) == ("promote", [])


def test_canary_rolls_back(policy):
    assert canary_decide(500, 50, 300.0, True, policy)[0] == "rollback"
    assert canary_decide(500, 0, 5000.0, True, policy)[0] == "rollback"
    assert canary_decide(500, 0, 300.0, False, policy)[0] == "rollback"


def test_canary_low_traffic_trusts_the_synthetic_check(policy):
    assert canary_decide(3, 3, None, True, policy) == ("promote", [])
    assert canary_decide(3, 0, None, False, policy)[0] == "rollback"
