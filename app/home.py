"""Shelf's front page: the reading list, and a way into the graveyard.

Not a feature: it has no flag and the census never counts it.
"""

from html import escape

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.catalog import BOOKS
from app import theme
from app.graveyard import current_ledger, nav

router = APIRouter()

PAGE_STYLE = r"""
.split { display: grid; grid-template-columns: minmax(0, 1fr) 360px; gap: 28px; align-items: start; margin-top: 18px; }
@media (max-width: 920px) { .split { grid-template-columns: 1fr; } }
.stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; margin: 0 0 16px; }
.stats span { position: relative; padding: 30px 14px 14px; background: var(--panel); border: 1px solid var(--line);
  font: 500 10.5px/1.3 var(--display); letter-spacing: 0.16em; text-transform: uppercase; color: var(--quiet);
  clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%); }
.stats span::before { content: "COUNT"; position: absolute; top: 11px; left: 14px; font: 500 9.5px/1 var(--mono); color: var(--faint); }
.stats b { display: block; margin-bottom: 8px; font: 600 34px/1 var(--display); color: var(--ink); font-variant-numeric: tabular-nums; }
.books td:nth-child(2) { color: var(--quiet); }
.teaser { position: sticky; top: 76px; display: block; padding: 0; color: var(--ink); background: var(--panel);
  border: 1px solid var(--line-hi); clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 18px 100%, 0 calc(100% - 18px));
  transition: border-color .2s; }
.teaser:hover { border-color: var(--hazard); color: var(--ink); }
.teaser .flame { display: flex; justify-content: space-between; align-items: center; padding: 10px 16px;
  background: repeating-linear-gradient(-45deg, var(--hazard) 0 10px, var(--bg) 10px 20px); }
.teaser .flame::before { content: "RESTRICTED // MORGUE"; padding: 4px 8px; background: var(--bg); color: var(--hazard);
  font: 700 11px/1 var(--display); letter-spacing: 0.2em; }
.teaser h3 { margin: 22px 18px 8px; font: 700 28px/1 var(--display); letter-spacing: 0.04em; text-transform: uppercase; }
.teaser p { margin: 0 18px 18px; color: var(--quiet); font-size: 13px; }
.teaser dl { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; margin: 0 18px 18px; background: var(--line); border: 1px solid var(--line); }
.teaser dl > div { background: var(--panel-hi); padding: 12px; }
.teaser dt { font: 600 26px/1 var(--display); font-variant-numeric: tabular-nums; }
.teaser dd { margin: 6px 0 0; font: 600 10px/1 var(--display); letter-spacing: 0.18em; text-transform: uppercase; color: var(--faint); }
.teaser .go { display: block; padding: 14px 18px; border-top: 1px solid var(--line); font: 700 12px/1 var(--display);
  letter-spacing: 0.2em; text-transform: uppercase; color: var(--hazard); }
.teaser:hover .go { background: var(--hazard); color: var(--bg); }
"""


def _teaser(ledger: dict) -> str:
    counts = "".join(
        f"<div><dt>{len(ledger[key])}</dt><dd>{label}</dd></div>"
        for key, label in (("retired", "retired"), ("hibernating", "hibernating"),
                           ("resurrected", "resurrected"), ("protected", "protected"))
    )
    return (
        "<a class='teaser' href='/graveyard' data-reveal><span class='flame'></span>"
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
        theme.head("Shelf &middot; a reading list", PAGE_STYLE) + "<main>"
        + nav("Reading list")
        + "<header class='hero'>"
        + theme.case_header("INTAKE 2023-0001", "Shelf &middot; live specimen")
        + "<div class='eyebrow'>Shelf, a reading list</div>"
        "<h1>Still alive. <em>Under watch.</em></h1>"
        "<p class='lead'>Shelf is a small reading-list app with a few years of cruft. AFTERLIFE watches "
        "which of its features are still used, and retires the ones that are not.</p>"
        "</header>"
        f"<div class='split'><section data-reveal><div class='stats'>{stats}</div>"
        "<div class='scroll'><table class='books'><tr><th>Title</th><th>Author</th><th>Status</th></tr>"
        f"{rows}</table></div></section>{side}</div>"
        "<footer><span class='epitaph'>Every feature runs behind a flag</span>"
        "<span>API: <code>/v2/books</code> &middot; <a href='/graveyard'>Visit the graveyard</a></span></footer>"
        "</main>" + theme.REVEAL_SCRIPT + "</body></html>"
    )


@router.get("/", response_class=HTMLResponse)
def home() -> str:
    return render(BOOKS, current_ledger())
