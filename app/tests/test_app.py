import datetime as dt

import pytest
from fastapi.testclient import TestClient

from app.flags import EnvFlags
from app.main import create_app
from app.store import InMemoryStore


@pytest.fixture
def store():
    return InMemoryStore()


@pytest.fixture
def flags():
    return EnvFlags(off=set())


@pytest.fixture
def client(store, flags):
    return TestClient(create_app(store=store, flags=flags))


def test_calls_are_counted(client, store):
    assert client.get("/v2/books").status_code == 200
    assert client.get("/v2/books").status_code == 200
    today = dt.datetime.now(dt.timezone.utc).date()
    assert store.daily_counts("books_v2")[today]["count"] == 2


def test_flag_off_returns_410_and_logs_knock(client, store, flags):
    flags.set("embed_widget", False)
    response = client.get("/embed/widget", headers={"x-partner-key": "acme"})
    assert response.status_code == 410
    knocks = store.knocks("embed_widget", since=dt.datetime(2000, 1, 1, tzinfo=dt.timezone.utc))
    assert [k["caller"] for k in knocks] == ["acme"]
    assert knocks[0]["user_agent"] == "testclient"
    assert store.daily_counts("embed_widget") == {}


def test_flag_back_on_restores_feature(client, flags):
    flags.set("books_v1", False)
    assert client.get("/v1/books").status_code == 410
    flags.set("books_v1", True)
    assert client.get("/v1/books").status_code == 200


def test_goodreads_import_from_text(client):
    csv_text = "Title,Author,Exclusive Shelf\nDune,Frank Herbert,read\n"
    response = client.post("/import/goodreads", json={"csv_text": csv_text})
    assert response.json() == {"imported": 1}


def test_goodreads_import_needs_input(client):
    assert client.post("/import/goodreads", json={}).status_code == 422


def test_wrapped_counts_finished_books(client):
    body = client.get("/wrapped/2025").json()
    assert body["books_finished"] == 2


def test_admin_reindex_requires_token(client, monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "s3cret")
    assert client.post("/admin/reindex").status_code == 403
    assert client.post("/admin/reindex", headers={"x-admin-token": "s3cret"}).status_code == 200


def test_graveyard_lists_protected_feature(client):
    response = client.get("/graveyard")
    assert response.status_code == 200
    assert "admin_reindex" in response.text


def test_graveyard_census_reflects_live_calls(client):
    import app.graveyard as graveyard

    graveyard._census_cache["at"] = 0.0
    client.get("/v2/books")
    response = client.get("/graveyard")
    assert "Census" in response.text and "/v2/books" in response.text


def test_home_page_lists_books_and_links_graveyard(client, store):
    response = client.get("/")
    assert response.status_code == 200
    assert "The Pragmatic Programmer" in response.text and "/graveyard" in response.text
    # The front page is not a feature, so it is never counted.
    assert all(not store.daily_counts(f) for f in ("books_v1", "books_v2"))
