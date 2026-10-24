"""The demo partner site (partner-site/, on GitLab Pages) and Shelf's side of it."""

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.flags import EnvFlags
from app.main import create_app
from app.store import InMemoryStore
from scripts.traffic import PARTNER_KEY as SCRIPT_KEY

PAGE = (Path(__file__).resolve().parents[2] / "partner-site" / "index.html").read_text(encoding="utf-8")


@pytest.fixture
def client():
    return TestClient(create_app(store=InMemoryStore(), flags=EnvFlags(off=set())))


def test_partner_site_only_requests_the_widget_when_clicked():
    # The one request is inside the click handler: opening the page never knocks.
    assert PAGE.count("fetch(") == 1
    assert PAGE.index("addEventListener('click'") < PAGE.index("fetch(")
    assert "made up" in PAGE


def test_partner_key_matches_the_traffic_script():
    assert re.search(r"PARTNER_KEY = '([^']+)'", PAGE).group(1) == SCRIPT_KEY


def test_partner_site_lives_outside_the_app():
    # Nothing in app/ calls the widget route, so the Coroner's grep finds no caller.
    app_dir = Path(__file__).resolve().parents[1]
    callers = [p for p in app_dir.rglob("*.py")
               if "tests" not in p.parts and p.name != "embed_widget.py" and "/embed/widget" in p.read_text()]
    assert callers == []


def test_widget_answers_cross_site_requests_with_the_partner_key(client):
    preflight = client.options("/embed/widget", headers={
        "Origin": "https://afterlife-transcend.gitlab.io",
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "x-partner-key",
    })
    assert preflight.status_code == 200
    assert "x-partner-key" in preflight.headers["access-control-allow-headers"].lower()
    response = client.get("/embed/widget", headers={"Origin": "https://partner.example", "x-partner-key": "acme"})
    assert response.status_code == 200 and response.headers["access-control-allow-origin"] == "*"


def test_cross_site_requests_cannot_send_the_admin_token(client):
    preflight = client.options("/admin/reindex", headers={
        "Origin": "https://partner.example",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "x-admin-token",
    })
    assert preflight.status_code == 400
