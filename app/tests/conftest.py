import pytest


@pytest.fixture(autouse=True)
def no_live_gitlab(monkeypatch):
    """App tests never call GitLab; timeline tests pass a fake fetch instead."""
    monkeypatch.setenv("AFTERLIFE_TIMELINE", "off")
