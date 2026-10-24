import pytest

from ci.policy import load_policy
from ci.verdict_check import check, parse_verdicts


@pytest.fixture
def policy():
    return load_policy()


def signals(name, **overrides):
    base = {
        "feature": name,
        "calls_in_window": 0,
        "days_silent": 200,
        "protected": False,
        "seasonal_suspect": False,
    }
    return {**base, **overrides}


def dead(name, files, confidence=0.9):
    return {"feature": name, "verdict": "DEAD", "confidence": confidence, "evidence": ["0 calls"], "files": files}


V1_FILES = ["app/features/books_v1.py"]
V1_CHANGES = V1_FILES + ["app/features/__init__.py", "afterlife/graveyard.yaml"]


def test_parses_fenced_verdict_blocks():
    text = 'Intro\n```afterlife-verdict\n{"feature": "books_v1", "verdict": "DEAD"}\n```\nOutro'
    assert parse_verdicts(text) == [{"feature": "books_v1", "verdict": "DEAD"}]


def test_clean_sunset_passes(policy):
    census = {"features": [signals("books_v1")]}
    assert check([dead("books_v1", V1_FILES)], census, policy, V1_CHANGES) == []


def test_recent_calls_block_dead(policy):
    census = {"features": [signals("books_v1", calls_in_window=3)]}
    assert check([dead("books_v1", V1_FILES)], census, policy, V1_CHANGES)


def test_seasonal_usage_blocks_dead(policy):
    census = {"features": [signals("wrapped", seasonal_suspect=True)]}
    problems = check([dead("wrapped", ["app/features/wrapped.py"])], census, policy, ["app/features/wrapped.py"])
    assert any("seasonal" in p for p in problems)


def test_low_confidence_blocks_dead(policy):
    census = {"features": [signals("books_v1")]}
    assert check([dead("books_v1", V1_FILES, confidence=0.5)], census, policy, V1_CHANGES)


def test_protected_feature_blocks_dead(policy):
    census = {"features": [signals("admin_reindex", protected=True)]}
    files = ["app/features/admin_reindex.py"]
    problems = check([dead("admin_reindex", files)], census, policy, files)
    assert any("protected" in p for p in problems)


def test_change_outside_verdict_files_fails(policy):
    census = {"features": [signals("books_v1")]}
    problems = check([dead("books_v1", V1_FILES)], census, policy, V1_CHANGES + ["app/features/books_v2.py"])
    assert any("books_v2.py" in p for p in problems)


def test_mr_cannot_edit_policy(policy):
    census = {"features": [signals("books_v1")]}
    problems = check([dead("books_v1", V1_FILES)], census, policy, V1_CHANGES + ["afterlife/policy.yaml"])
    assert any("policy.yaml" in p for p in problems)


def test_changes_without_dead_verdict_fail(policy):
    hibernating = {"feature": "wrapped", "verdict": "HIBERNATING", "confidence": 0.9, "evidence": ["Dec"], "files": []}
    census = {"features": [signals("wrapped")]}
    assert check([hibernating], census, policy, ["app/features/wrapped.py"])


def test_unknown_feature_fails(policy):
    assert check([dead("ghost", ["app/features/ghost.py"])], {"features": []}, policy, ["app/features/ghost.py"])


def test_orphan_files_must_be_in_the_verdict(policy):
    census = {"features": [signals("import_goodreads")]}
    verdict = dead("import_goodreads", ["app/features/import_goodreads.py", "app/catalog.py"])
    verdict["orphans"] = ["app/catalog.py:add_books"]
    changes = ["app/features/import_goodreads.py", "app/catalog.py", "app/features/__init__.py"]
    assert check([verdict], census, policy, changes) == []

    verdict["files"] = ["app/features/import_goodreads.py"]
    problems = check([verdict], census, policy, changes)
    assert any("orphan app/catalog.py:add_books" in p for p in problems)


def test_mr_cannot_edit_the_pipeline(policy):
    census = {"features": [signals("books_v1")]}
    problems = check([dead("books_v1", V1_FILES)], census, policy, V1_CHANGES + [".gitlab-ci.yml"])
    assert any(".gitlab-ci.yml" in p for p in problems)
