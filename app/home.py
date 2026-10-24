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
.split { display: grid; grid-template-columns: minmax(0, 1fr) 340px; gap: 24px; align-items: start; margin-top: 18px; }
@media (max-width: 920px) { .split { grid-template-columns: 1fr; } }
.stats { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); margin: 0 0 16px; overflow: hidden;
  background: linear-gradient(180deg, var(--glass-hi), var(--glass)); border: 1px solid var(--edge); border-radius: var(--radius);
  backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur); box-shadow: inset 0 1px 0 var(--sheen); }
.stats span { padding: 22px 20px; border-left: 1px solid var(--edge); font: 400 10.5px/1.3 var(--mono); letter-spacing: 0.1em;
  text-transform: uppercase; color: var(--faint); }
.stats span:first-child { border-left: 0; }
.stats b { display: block; margin-bottom: 10px; font: 400 28px/1 var(--display); color: var(--ink); font-variant-numeric: tabular-nums; }
.books td:nth-child(2) { color: var(--quiet); }
.teaser { position: sticky; top: 96px; display: block; padding: 28px 26px 0; overflow: hidden; color: var(--ink);
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02) 65%); border: 1px solid var(--edge);
  border-radius: 24px; backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur);
  box-shadow: inset 0 1px 0 var(--sheen), 0 50px 80px -50px rgba(0, 0, 0, 0.9); transition: transform .5s var(--ease), border-color .3s; }
.teaser:hover { transform: translateY(-4px); border-color: var(--edge-hi); color: var(--ink); }
.teaser::after { content: ""; position: absolute; top: -80px; right: -60px; width: 240px; height: 240px; pointer-events: none; border-radius: 50%;
  background: radial-gradient(closest-side, rgba(201, 168, 255, 0.25), transparent); filter: blur(10px); }
.teaser .flame { display: block; width: 10px; height: 10px; margin-bottom: 26px; border-radius: 50%; background: var(--aura);
  box-shadow: 0 0 0 6px var(--aura-soft), 0 0 22px var(--aura); animation: breathe 2.6s ease-in-out infinite; }
.teaser h3 { margin: 0 0 10px; font: 400 20px/1.2 var(--display); letter-spacing: 0.06em; text-transform: uppercase; }
.teaser p { margin: 0 0 22px; color: var(--quiet); font-size: 13px; }
.teaser dl { display: grid; grid-template-columns: 1fr 1fr; gap: 1px; margin: 0 0 22px; overflow: hidden; border-radius: 14px;
  background: var(--edge); border: 1px solid var(--edge); }
.teaser dl > div { background: rgba(8, 10, 14, 0.6); padding: 14px; }
.teaser dt { font: 400 22px/1 var(--display); font-variant-numeric: tabular-nums; }
.teaser dd { margin: 8px 0 0; font: 400 10px/1 var(--mono); letter-spacing: 0.12em; text-transform: uppercase; color: var(--faint); }
.teaser .go { display: block; margin: 0 -26px; padding: 16px 26px; border-top: 1px solid var(--edge); font: 400 10px/1 var(--display);
  letter-spacing: 0.24em; text-transform: uppercase; color: var(--ice); transition: background .2s; }
.teaser:hover .go { background: var(--glass-hi); }
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
