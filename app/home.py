"""Shelf's front page: the reading list, and a way into the graveyard.

Not a feature: it has no flag and the census never counts it.
"""

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.catalog import BOOKS
from app.graveyard import STYLE, current_ledger, nav

router = APIRouter()

PAGE_STYLE = """
.split { display: grid; grid-template-columns: minmax(0, 1fr) 300px; gap: 20px; align-items: start; }
@media (max-width: 760px) { .split { grid-template-columns: 1fr; } }
.stats { display: flex; gap: 22px; margin: 0 0 16px; color: var(--quiet); font-size: 14px; flex-wrap: wrap; }
.stats b { color: var(--ink); font-size: 18px; margin-right: 4px; font-variant-numeric: tabular-nums; }
.pill.read { color: var(--good); } .pill.reading { color: var(--warn); } .pill.to-read { color: var(--quiet); }
.teaser { display: block; background: var(--card); border: 1px solid var(--line); border-radius: 12px;
  padding: 16px 18px; color: var(--ink); text-decoration: none; }
.teaser:hover { border-color: var(--accent); }
.teaser h3 { margin: 0 0 4px; font: 600 18px/1.3 Georgia, "Times New Roman", serif; }
.teaser p { margin: 0 0 12px; color: var(--quiet); font-size: 13.5px; }
.teaser dl { display: grid; grid-template-columns: auto 1fr; gap: 4px 12px; margin: 0 0 12px; font-size: 14px; }
.teaser dt { font-weight: 700; text-align: right; font-variant-numeric: tabular-nums; }
.teaser dd { margin: 0; color: var(--quiet); }
.teaser .go { color: var(--accent); font-size: 14px; }
"""


def _teaser(ledger: dict) -> str:
    counts = "".join(
        f"<dt>{len(ledger[key])}</dt><dd>{label}</dd>"
        for key, label in (("retired", "retired"), ("hibernating", "hibernating"),
                           ("resurrected", "resurrected"), ("protected", "protected"))
    )
    return (
        "<a class='teaser' href='/graveyard'>"
        "<h3>The graveyard</h3>"
        "<p>Where Shelf's unused features go, with the evidence and what removing them saved.</p>"
        f"<dl>{counts}</dl><span class='go'>Visit the graveyard &rarr;</span></a>"
    )


def render(books: list[dict], ledger: dict | None = None) -> str:
    rows = "".join(
        f"<tr><td><b>{escape(b['title'])}</b></td><td>{escape(b['author'])}</td>"
        f"<td><span class='pill {escape(b['status'])}'>{escape(b['status'])}</span></td></tr>"
        for b in books
    )
    stats = "".join(
        f"<span><b>{sum(1 for b in books if b['status'] == status)}</b>{label}</span>"
        for status, label in (("read", "read"), ("reading", "reading now"), ("to-read", "to read"))
    )
    side = _teaser(ledger) if ledger is not None else ""
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Shelf</title><style>{STYLE}{PAGE_STYLE}</style></head><body><main>"
        + nav("Reading list")
        + "<h1>Reading list</h1>"
        "<p class='lead'>Shelf is a small reading-list app with a few years of cruft. AFTERLIFE watches "
        "which of its features are still used, and retires the ones that are not.</p>"
        f"<div class='split'><section><div class='stats'>{stats}</div>"
        "<div class='scroll'><table><tr><th>Title</th><th>Author</th><th>Status</th></tr>"
        f"{rows}</table></div></section>{side}</div>"
        "<footer>API: <code>/v2/books</code>. Every feature runs behind a feature flag. "
        "<a href='/graveyard'>Visit the graveyard</a>.</footer>"
        "</main></body></html>"
    )


@router.get("/", response_class=HTMLResponse)
def home() -> str:
    return render(BOOKS, current_ledger())
