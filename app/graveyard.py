"""The /graveyard page: retired, hibernating, resurrected and protected features.

Tombstones come from afterlife/graveyard.yaml (written by the agents in git).
Measured savings come from the store (published by CI after release), so a
tombstone without savings says so instead of showing a number nobody measured.
"""

import datetime as dt
import os
import time
from html import escape
from pathlib import Path

import yaml
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app import theme, timeline, verdicts
from app.features import FEATURES
from app.registry import Feature
from app.store import UsageStore

DEFAULT_LEDGER = Path(__file__).resolve().parent.parent / "afterlife" / "graveyard.yaml"
DEFAULT_POLICY = Path(__file__).resolve().parent.parent / "afterlife" / "policy.yaml"
# Reading every feature's daily counts costs Firestore reads, so the census
# section is reused for a few minutes instead of rebuilt on each page view.
CENSUS_TTL_SECONDS = 300

router = APIRouter()

STYLE = r"""
/* --- readouts: a row of glass instruments ------------------------------------ */
.totals { display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); margin-top: 56px; overflow: hidden;
  background: linear-gradient(180deg, var(--glass-hi), var(--glass)); border: 1px solid var(--edge); border-radius: var(--radius);
  backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur); box-shadow: inset 0 1px 0 var(--sheen); }
@media (max-width: 980px) { .totals { grid-template-columns: repeat(3, minmax(0, 1fr)); } }
@media (max-width: 560px) { .totals { grid-template-columns: repeat(2, minmax(0, 1fr)); } }
.total { min-width: 0; padding: 26px 18px 24px; border-left: 1px solid var(--edge); }
.total:first-child { border-left: 0; }
.total b { display: block; font: 400 clamp(20px, 2.1vw, 28px)/1 var(--display); white-space: nowrap; font-variant-numeric: tabular-nums; color: var(--ink); }
.total span { display: block; margin-top: 14px; font: 400 10.5px/1.4 var(--mono); letter-spacing: 0.1em; text-transform: uppercase; color: var(--faint); }
.total.good b { color: var(--mint); text-shadow: 0 0 28px rgba(147, 240, 200, 0.35); }

/* --- specimen cards: glass toe tags ------------------------------------------ */
.stones { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 20px; padding-top: 12px; }
.stone { position: relative; padding: 26px 26px 0; overflow: hidden;
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0.02) 60%);
  border: 1px solid var(--edge); border-radius: var(--radius); backdrop-filter: var(--blur); -webkit-backdrop-filter: var(--blur);
  box-shadow: inset 0 1px 0 var(--sheen), 0 40px 70px -45px rgba(0, 0, 0, 0.9); transition: transform .5s var(--ease), border-color .3s; }
.stone:hover { transform: translateY(-4px); border-color: var(--edge-hi); }
.stone::before { content: ""; position: absolute; top: 24px; right: 24px; width: 12px; height: 12px; border-radius: 50%;
  border: 1px solid var(--edge-hi); box-shadow: inset 0 0 0 3px rgba(5, 6, 8, 0.9), 0 0 0 1px var(--edge); }
.stone::after { content: ""; position: absolute; inset: -40% -20% auto auto; width: 70%; height: 80%; pointer-events: none;
  background: radial-gradient(closest-side, rgba(166, 220, 255, 0.10), transparent); }
.stone .rip { display: flex; gap: 12px; align-items: center; margin-bottom: 18px; font: 400 10px/1 var(--display); letter-spacing: 0.3em; color: var(--faint); }
.stone .rip::after { content: "DECEASED"; padding: 5px 9px; border-radius: 999px; font: 500 9.5px/1 var(--mono); letter-spacing: 0.16em;
  color: var(--coral); background: var(--coral-soft); }
.stone h3 { margin: 0; font: 400 clamp(18px, 2vw, 22px)/1.3 var(--display); letter-spacing: 0.04em; text-transform: uppercase;
  overflow-wrap: anywhere; color: var(--ink); }
.stone .route { margin-top: 8px; font: 400 12.5px/1 var(--mono); color: var(--ice); }
.stone .dates { margin: 20px 0 16px; font: 400 12px/1 var(--mono); letter-spacing: 0.06em; color: var(--quiet); }
.stone .dates::before { content: "LIFESPAN  "; color: var(--faint); letter-spacing: 0.14em; }
.stone .cause { margin: 0 0 20px; font-size: 13px; line-height: 1.7; color: var(--quiet); }
.stone .cause::before { content: "CAUSE OF DEATH"; display: block; margin-bottom: 6px; font: 400 9.5px/1 var(--display);
  letter-spacing: 0.24em; color: var(--faint); }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 20px; }
.chip { padding: 6px 10px; border-radius: 999px; font: 400 11px/1 var(--mono); color: var(--ink); background: var(--glass-hi);
  border: 1px solid var(--edge); font-variant-numeric: tabular-nums; }
.chip.good { color: var(--mint); background: var(--mint-soft); border-color: transparent; }
.pending { color: var(--ice); font-size: 12.5px; margin: 0 0 20px; }
.links { display: flex; flex-wrap: wrap; margin: 0 -26px; border-top: 1px solid var(--edge); }
.links a { flex: 1 1 auto; padding: 14px 10px; text-align: center; font: 400 9.5px/1 var(--display); letter-spacing: 0.16em;
  text-transform: uppercase; color: var(--quiet); border-right: 1px solid var(--edge); transition: background .2s, color .2s; }
.links a:last-child { border-right: 0; }
.links a:hover { color: var(--ink); background: var(--glass-hi); }
"""


def load_ledger(path: Path | None = None) -> dict:
    path = path or Path(os.environ.get("AFTERLIFE_GRAVEYARD", DEFAULT_LEDGER))
    data = yaml.safe_load(path.read_text()) or {}
    return {key: data.get(key) or [] for key in ("retired", "hibernating", "resurrected", "protected")}


def census_rows(features: list[Feature], store: UsageStore, window_days: int, today: dt.date) -> list[dict]:
    """The live candidate list: calls in the census window and days since the last call."""
    window_start = today - dt.timedelta(days=window_days)
    rows = []
    for feature in features:
        counts = store.daily_counts(feature.name)
        seen = [day for day, row in counts.items() if row["count"] > 0 and day <= today]
        last_seen = max(seen) if seen else None
        calls = sum(row["count"] for day, row in counts.items() if window_start < day <= today)
        rows.append({
            "feature": feature.name,
            "route": feature.route,
            "calls_in_window": calls,
            "last_seen": last_seen.isoformat() if last_seen else "never",
            "days_silent": (today - last_seen).days if last_seen else "never called",
            "candidate": "yes" if calls == 0 else "no",
        })
    # Quietest first: those are the ones the Coroner will look at.
    return sorted(rows, key=lambda r: (r["candidate"] != "yes", r["calls_in_window"]))


_census_cache: dict = {"at": 0.0, "store": None, "rows": None}


def cached_census(store: UsageStore, window_days: int) -> list[dict]:
    fresh = time.monotonic() - _census_cache["at"] < CENSUS_TTL_SECONDS
    if not (fresh and _census_cache["store"] is store):
        today = dt.datetime.now(dt.timezone.utc).date()
        _census_cache.update(at=time.monotonic(), store=store,
                             rows=census_rows(FEATURES, store, window_days, today))
    return _census_cache["rows"]


def census_window_days(path: Path = DEFAULT_POLICY) -> int:
    return int((yaml.safe_load(path.read_text()) or {}).get("census_window_days", 30))


def _num(value, digits: int = 1) -> str:
    if isinstance(value, float):
        return f"{value:,.{digits}f}"
    return f"{value:,}"


def totals(retired: list[dict], savings: dict[str, dict]) -> dict:
    measured = [savings[t["feature"]] for t in retired if t.get("feature") in savings]
    sci = [s["sci"]["delta_gco2e"] for s in measured if s.get("sci")]
    return {
        "retired": len(retired),
        "lines_removed": sum(s.get("lines_removed", 0) for s in measured),
        "deps_removed": sum(len(s.get("deps_removed", [])) for s in measured),
        "cves_removed": sum(len(s.get("cves_removed", [])) for s in measured),
        # None, not 0, when no retirement has a measured image size: shown as a dash.
        "image_mb_saved": (round(sum(s["image_mb_saved"] for s in measured if s.get("image_mb_saved") is not None), 1)
                           if any(s.get("image_mb_saved") is not None for s in measured) else None),
        "sci_gco2e_saved": round(sum(sci), 4) if sci else None,
    }


def _total(label: str, value, digits: int = 1, good: bool = False) -> str:
    shown = "&mdash;" if value is None else escape(_num(value, digits))
    lit = " good" if good and value else ""
    return f"<div class='total{lit}'><b>{shown}</b><span>{escape(label)}</span></div>"


def nav(current: str) -> str:
    """The bar shared by Shelf's pages, so the video can move between them."""
    links = [("Reading list", "/"), ("Graveyard", "/graveyard")]
    items = "".join(
        f"<a href='{href}'{' aria-current=\"page\"' if label == current else ''}>{label}</a>"
        for label, href in links
    )
    watch = "<span class='watch'><b>&#9679;</b>MONITORING</span>"
    return f"<nav><a class='brand' href='/'><i></i>SHELF<small>// AFTERLIFE LAB</small></a>{items}{watch}</nav>"


SECTION_NUMBERS = {"live": "01", "retired": "02", "hibernating": "03", "resurrected": "04",
                   "protected": "05", "census": "06"}


def _h2(title: str, count: int | None = None, anchor: str = "") -> str:
    shown = "" if count is None else f"<span class='count'>{count}</span>"
    ident = f" id='{anchor}'" if anchor else ""
    number = f" data-index='{SECTION_NUMBERS[anchor]}'" if anchor in SECTION_NUMBERS else ""
    return f"<h2{ident}{number}>{escape(title)}{shown}</h2>"


def _when(value) -> str:
    """2026-10-26T12:03:00Z -> 2026-10-26 12:03 UTC; anything else is shown as given."""
    try:
        at = dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return escape(str(value))
    if at.tzinfo:
        at = at.astimezone(dt.timezone.utc)
    return f"{at:%Y-%m-%d %H:%M} UTC"


def _census_status(row: dict, protected: set[str]) -> str:
    if row["feature"] in protected:
        return "<span class='pill protected'>protected</span>"
    if row["candidate"] == "yes":
        return "<span class='pill candidate'>candidate</span>"
    return "<span class='pill alive'>in use</span>"


def _chips(s: dict) -> str:
    chips = []
    if s.get("lines_removed"):
        chips.append(f"{_num(s['lines_removed'])} lines removed")
    if s.get("deps_removed"):
        chips.append("deps: " + ", ".join(s["deps_removed"]))
    if s.get("cves_removed"):
        chips.append(f"{len(s['cves_removed'])} CVEs removed")
    # Show the measured sizes, not a "saved" figure: removing code can leave the
    # image the same size (a dependency other libraries still need stays installed).
    if s.get("image_mb_before") is not None and s.get("image_mb_after") is not None:
        chips.append(f"image {_num(s['image_mb_before'])} → {_num(s['image_mb_after'])} MB")
    if s.get("sci"):
        chips.append(f"{_num(s['sci']['delta_gco2e'], 4)} gCO2e/run saved")
    good = {i for i, c in enumerate(chips) if "CVE" in c or "gCO2e" in c}
    return "".join(
        f"<span class='chip{' good' if i in good else ''}'>{escape(c)}</span>" for i, c in enumerate(chips)
    )


def _links(tomb: dict, s: dict) -> str:
    links = [("Sunset MR", s.get("mr_url") or tomb.get("mr")), ("Release", s.get("release_url")),
             ("Obituary", s.get("obituary_url")), ("Measured by", s.get("measured_job_url"))]
    return "".join(f"<a href='{escape(str(url))}'>{escape(label)}</a>" for label, url in links if url)


def _stone(tomb: dict, savings: dict[str, dict]) -> str:
    s = savings.get(tomb.get("feature"), {})
    measured = (f"<div class='chips'>{_chips(s)}</div>" if s
                else "<p class='pending'>Savings not measured yet: they appear after the release ships.</p>")
    return (
        "<article class='stone'>"
        "<div class='rip'>HERE LIES</div>"
        f"<h3>{escape(str(tomb.get('feature', '?')))}</h3>"
        f"<div class='route'>{escape(str(tomb.get('route', '')))}</div>"
        f"<div class='dates'>{escape(str(tomb.get('born', '?')))} &ndash; {escape(str(tomb.get('died', '?')))}</div>"
        f"<p class='cause'>{escape(str(tomb.get('cause', '')))}</p>"
        f"{measured}<div class='links'>{_links(tomb, s)}</div>"
        "</article>"
    )


def _table(entries: list[dict], columns: list[tuple[str, str]], empty: str,
           cells: dict | None = None, classes: dict[str, str] | None = None) -> str:
    """cells maps a column key to a function returning that cell's (already escaped) HTML."""
    if not entries:
        return f"<p class='empty'>{escape(empty)}</p>"
    cells, classes = cells or {}, classes or {}

    def cls(key: str) -> str:
        return f" class='{classes[key]}'" if key in classes else ""

    def cell(entry: dict, key: str) -> str:
        return cells[key](entry) if key in cells else escape(str(entry.get(key, "")))

    head = "".join(f"<th{cls(key)}>{escape(title)}</th>" for title, key in columns)
    rows = "".join(
        "<tr>" + "".join(f"<td{cls(key)}>{cell(entry, key)}</td>" for _, key in columns) + "</tr>"
        for entry in entries
    )
    return f"<div class='scroll' data-reveal><table><tr>{head}</tr>{rows}</table></div>"


def render(ledger: dict, savings: dict[str, dict], census: list[dict] | None = None,
           window_days: int = 30, timeline_html: str | None = None) -> str:
    t = totals(ledger["retired"], savings)
    stones = ("".join(_stone(tomb, savings) for tomb in ledger["retired"])
              or "<p class='empty'>Nothing retired yet.</p>")
    live = ("" if timeline_html is None else
            _h2("Active cases", anchor="live")
            + "<p class='lead'>Each retirement is a case moving through the lab. Every stage is a real GitLab job; click one to open it. "
            f"This section refreshes every {timeline.REFRESH_MS // 1000} seconds.</p>"
            f"<section id='timeline' data-reveal>{timeline_html}</section>")
    protected = {p.get("feature") for p in ledger["protected"]}
    mono = {"route": lambda e: f"<span class='mono'>{escape(str(e.get('route', '')))}</span>"}
    feature = {"feature": lambda e: f"<b>{escape(str(e.get('feature', '')))}</b>"}
    return (
        theme.head("Graveyard &middot; Shelf", STYLE + timeline.STYLE) + "<main>"
        + nav("Graveyard")
        + "<header class='hero'>"
        + theme.case_header("CASE AFT-0001", "Shelf &middot; morgue register")
        + "<div class='eyebrow'>Cause of death</div>"
        "<h1>Nobody <em>used it.</em></h1>"
        "<p class='lead'>Every feature AFTERLIFE retired from Shelf, what each one cost while it was alive, "
        "and the ones it chose to keep. <em>Every number was measured by a CI job, never guessed.</em></p>"
        "</header>"
        "<section class='totals' data-reveal>"
        + _total("features retired", t["retired"])
        + _total("lines removed", t["lines_removed"])
        + _total("dependencies removed", t["deps_removed"])
        + _total("CVEs removed", t["cves_removed"], good=True)
        + _total("MB image change (saved)", t["image_mb_saved"])
        + _total("gCO2e saved per pipeline run", t["sci_gco2e_saved"], digits=4, good=True)
        + "</section>"
        + live
        + _h2("Deceased", len(ledger["retired"]), "retired") + f"<section class='stones' data-reveal>{stones}</section>"
        + _h2("Hibernating", len(ledger["hibernating"]), "hibernating")
        + "<p class='lead'>Quiet, but not dead. The Coroner refused to sign a death certificate.</p>"
        + _table(ledger["hibernating"], [("Feature", "feature"), ("Why it was kept", "reason"),
                                         ("Check again", "recheck"), ("Decided by", "source")],
                 "No hibernating features.", cells=feature)
        + _h2("Resurrected", len(ledger["resurrected"]), "resurrected")
        + "<p class='lead'>Flatlined for the vigil, then somebody knocked. Revived; nothing was deleted.</p>"
        + _table(ledger["resurrected"], [("Feature", "feature"), ("Who knocked", "caller"),
                                         ("When", "knocked_at"), ("Why", "reason"), ("Check again", "recheck")],
                 "Nobody has knocked yet.",
                 cells={**feature, "caller": lambda e: f"<span class='mono'>{escape(str(e.get('caller', '')))}</span>",
                        "knocked_at": lambda e: _when(e.get("knocked_at", ""))})
        + _h2("Protected", len(ledger["protected"]), "protected")
        + "<p class='lead'>Never sent to the morgue, however quiet. Policy decides, not the agents.</p>"
        + _table(ledger["protected"], [("Feature", "feature"), ("Reason", "reason")], "No protected features.",
                 cells=feature)
        + _h2("Census", len(census or []), "census")
        + f"<p class='lead'>Every live feature, quietest first. A feature with no calls in the last "
        f"{window_days} days is a candidate; the Coroner decides whether it is really dead.</p>"
        + _table(census or [], [("Feature", "feature"), ("Route", "route"),
                                (f"Calls, last {window_days} days", "calls_in_window"),
                                ("Last call", "last_seen"), ("Days silent", "days_silent"),
                                ("Status", "candidate")], "No usage recorded yet.",
                 cells={**feature, **mono,
                        "calls_in_window": lambda e: escape(_num(e["calls_in_window"])),
                        "candidate": lambda e: _census_status(e, protected)},
                 classes={"calls_in_window": "num", "days_silent": "num"})
        + "<footer><span class='epitaph'>End of report</span>"
        "<span>Every number is measured by a CI job and links to it. Usage history in this demo is "
        "simulated and labelled as such in the census.</span></footer>"
        "</main>"
        + (timeline.REFRESH_SCRIPT if timeline_html is not None else "")
        + theme.REVEAL_SCRIPT
        + "</body></html>"
    )


def _knocks(store: UsageStore) -> timeline.Knocks:
    """How many knocks a feature has had since its vigil began, for the countdown."""
    return lambda feature, since: len(store.knocks(feature, since))


@router.get("/graveyard", response_class=HTMLResponse)
def graveyard(request: Request) -> str:
    store = request.app.state.store
    window = census_window_days()
    return render(current_ledger(), store.all_savings(), cached_census(store, window), window,
                  timeline.render_timeline(*timeline.cached_timeline(knocks=_knocks(store))))


def current_ledger() -> dict:
    """The ledger in git, plus the features the Coroner's latest verdicts kept."""
    return verdicts.with_verdicts(load_ledger(), *verdicts.cached_verdicts())


@router.get("/graveyard/timeline", response_class=HTMLResponse)
def graveyard_timeline(request: Request) -> str:
    """The timeline section alone, for the page's 15-second refresh."""
    return timeline.render_timeline(*timeline.cached_timeline(knocks=_knocks(request.app.state.store)))
