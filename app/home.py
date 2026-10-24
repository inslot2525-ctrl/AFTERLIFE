"""Shelf's front page: the reading list, and a way into the graveyard.

Not a feature: it has no flag and the census never counts it.
"""

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.catalog import BOOKS
from app.graveyard import STYLE

router = APIRouter()


def render(books: list[dict]) -> str:
    rows = "".join(
        f"<tr><td>{escape(b['title'])}</td><td>{escape(b['author'])}</td><td>{escape(b['status'])}</td></tr>"
        for b in books
    )
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Shelf</title><style>{STYLE}</style></head><body><main>"
        "<h1>Shelf</h1>"
        "<p class='lead'>A small reading list with a few years of cruft. AFTERLIFE watches which of its "
        "features are still used and retires the ones that are not. "
        "<a href='/graveyard'>Visit the graveyard</a>.</p>"
        "<div class='scroll'><table><tr><th>Title</th><th>Author</th><th>Status</th></tr>"
        f"{rows}</table></div>"
        "<footer>API: <code>/v2/books</code>. Every feature runs behind a feature flag.</footer>"
        "</main></body></html>"
    )


@router.get("/", response_class=HTMLResponse)
def home() -> str:
    return render(BOOKS)
