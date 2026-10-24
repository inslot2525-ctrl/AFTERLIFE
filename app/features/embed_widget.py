"""Embeddable "currently reading" card for partner sites."""

from html import escape

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from app.catalog import BOOKS
from app.gate import feature_gate
from app.registry import Feature

FEATURE = Feature(
    name="embed_widget",
    route="/embed/widget",
    module="app/features/embed_widget.py",
    owner="shelf-partners",
    born="2024-01-09",
    summary="HTML card partners embed to show what a reader is reading",
)

router = APIRouter(dependencies=[Depends(feature_gate(FEATURE.name))])


@router.get("/embed/widget", response_class=HTMLResponse)
def embed_widget() -> str:
    reading = [b for b in BOOKS if b["status"] == "reading"]
    items = "".join(f"<li>{escape(b['title'])} by {escape(b['author'])}</li>" for b in reading)
    return f"<div class='shelf-widget'><strong>Currently reading</strong><ul>{items}</ul></div>"
