import pytest
from fastapi.testclient import TestClient

from app.flags import EnvFlags
from app.main import create_app
from app.partner import PARTNER_KEY, render
from app.store import InMemoryStore
from scripts.traffic import PARTNER_KEY as SCRIPT_KEY


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def client(store):
    return TestClient(create_app(store=store, flags=EnvFlags(off=set())))


def test_partner_page_only_knocks_when_clicked():
    html = render()
    # The one request is inside the click handler: opening the page never knocks.
    assert html.count("fetch('/embed/widget'") == 1
    assert html.index("addEventListener('click'") < html.index("fetch('/embed/widget'")
    assert "made up for the demo" in html


def test_partner_key_matches_the_traffic_script():
    assert PARTNER_KEY == SCRIPT_KEY


def test_partner_page_is_served_and_not_counted(client, store):
    assert client.get("/partner").status_code == 200
    assert store.daily_counts("embed_widget") == {}
    assert "/partner" in client.get("/").text  # in the shared nav
