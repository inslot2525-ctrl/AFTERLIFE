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

from app import timeline
from app.features import FEATURES
from app.registry import Feature
from app.store import UsageStore

DEFAULT_LEDGER = Path(__file__).resolve().parent.parent / "afterlife" / "graveyard.yaml"
DEFAULT_POLICY = Path(__file__).resolve().parent.parent / "afterlife" / "policy.yaml"
# Reading every feature's daily counts costs Firestore reads, so the census
# section is reused for a few minutes instead of rebuilt on each page view.
CENSUS_TTL_SECONDS = 300

router = APIRouter()

STYLE = """
:root {
  --bg: #f6f5f2; --card: #ffffff; --ink: #1d1c1a; --quiet: #6b6862; --line: #dedbd4;
  --accent: #5b4bd6; --good: #1f7a4d; --warn: #9a5b00; --stone: #ebe8e1;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #121214; --card: #1b1b1f; --ink: #ecebe8; --quiet: #9d9a94; --line: #2e2e34;
    --accent: #9d93ff; --good: #5fd39b; --warn: #f0b45a; --stone: #24242a;
  }
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--bg); color: var(--ink);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }
main { max-width: 1040px; margin: 0 auto; padding: 20px 16px 48px; }
a { color: var(--accent); }
code, .mono { font-family: ui-monospace, Consolas, monospace; font-size: 0.92em; }
nav { display: flex; gap: 18px; align-items: baseline; padding-bottom: 14px; margin-bottom: 28px;
  border-bottom: 1px solid var(--line); font-size: 14px; flex-wrap: wrap; }
nav .brand { font-weight: 700; color: var(--ink); text-decoration: none; letter-spacing: 0.04em; margin-right: auto; }
nav a { color: var(--quiet); text-decoration: none; }
nav a:hover, nav a[aria-current] { color: var(--ink); }
h1 { font-size: 32px; margin: 0 0 6px; letter-spacing: -0.02em; }
h2 { font-size: 18px; margin: 40px 0 12px; display: flex; align-items: baseline; gap: 8px; scroll-margin-top: 16px; }
h2 .count { color: var(--quiet); font-weight: 500; font-size: 14px; font-variant-numeric: tabular-nums; }
.lead { color: var(--quiet); margin: 0 0 24px; max-width: 680px; }
h2 + .lead { margin-top: -4px; font-size: 14px; }
.totals { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
.total { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.total b { display: block; font-size: 26px; font-variant-numeric: tabular-nums; letter-spacing: -0.01em; }
.total span { color: var(--quiet); font-size: 13px; }
.total.good b { color: var(--good); }
.stones { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 20px 16px;
  padding-bottom: 14px; border-bottom: 6px solid var(--line); }
.stone { background: linear-gradient(180deg, var(--card), var(--stone)); border: 1px solid var(--line);
  border-bottom-width: 3px; border-radius: 140px 140px 8px 8px; padding: 34px 22px 18px; text-align: center; }
.stone .rip { font-size: 11px; letter-spacing: 0.3em; color: var(--quiet); margin-bottom: 8px; }
.stone h3 { margin: 0; font: 600 20px/1.3 Georgia, "Times New Roman", serif; overflow-wrap: anywhere; }
.stone .route { font-family: ui-monospace, Consolas, monospace; font-size: 13px; color: var(--quiet); }
.stone .dates { margin: 6px 0 10px; font-size: 13px; color: var(--quiet); }
.stone .cause { font-style: italic; margin: 0 0 14px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; justify-content: center; margin-bottom: 12px; }
.chip { background: var(--card); border: 1px solid var(--line); border-radius: 999px; padding: 2px 10px;
  font-size: 12.5px; font-variant-numeric: tabular-nums; }
.chip.good { color: var(--good); border-color: currentColor; }
.pending { color: var(--warn); font-size: 13px; margin: 0 0 12px; }
.links a { color: var(--accent); font-size: 13px; margin: 0 6px; }
table { width: 100%; border-collapse: collapse; background: var(--card); border: 1px solid var(--line);
  border-radius: 12px; overflow: hidden; }
th, td { text-align: left; padding: 10px 14px; border-bottom: 1px solid var(--line); vertical-align: top; }
th { font-size: 12.5px; color: var(--quiet); font-weight: 600; }
th.num, td.num { text-align: right; font-variant-numeric: tabular-nums; }
tr:last-child td { border-bottom: 0; }
.pill { display: inline-block; font-size: 12px; border: 1px solid currentColor; border-radius: 999px;
  padding: 0 9px; white-space: nowrap; }
.pill.candidate { color: var(--warn); } .pill.alive { color: var(--good); } .pill.protected { color: var(--accent); }
.pill.quiet { color: var(--quiet); }
.empty { color: var(--quiet); }
.scroll { overflow-x: auto; }
footer { margin-top: 40px; color: var(--quiet); font-size: 13px; }
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
        "image_mb_saved": round(sum(s.get("image_mb_saved") or 0 for s in measured), 1),
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
    return f"<nav><a class='brand' href='/'>SHELF</a>{items}</nav>"


def _h2(title: str, count: int | None = None, anchor: str = "") -> str:
    shown = "" if count is None else f"<span class='count'>{count}</span>"
    ident = f" id='{anchor}'" if anchor else ""
    return f"<h2{ident}>{escape(title)}{shown}</h2>"


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
    if s.get("image_mb_saved"):
        chips.append(f"{_num(s['image_mb_saved'])} MB image saved")
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
    return f"<div class='scroll'><table><tr>{head}</tr>{rows}</table></div>"


def render(ledger: dict, savings: dict[str, dict], census: list[dict] | None = None,
           window_days: int = 30, timeline_html: str | None = None) -> str:
    t = totals(ledger["retired"], savings)
    stones = ("".join(_stone(tomb, savings) for tomb in ledger["retired"])
              or "<p class='empty'>Nothing retired yet.</p>")
    live = ("" if timeline_html is None else
            _h2("Retirements, live", anchor="live")
            + "<p class='lead'>Each stage is a GitLab job; click one to open it. "
            f"This section refreshes every {timeline.REFRESH_MS // 1000} seconds.</p>"
            f"<section id='timeline'>{timeline_html}</section>")
    protected = {p.get("feature") for p in ledger["protected"]}
    mono = {"route": lambda e: f"<span class='mono'>{escape(str(e.get('route', '')))}</span>"}
    feature = {"feature": lambda e: f"<b>{escape(str(e.get('feature', '')))}</b>"}
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Graveyard</title><style>{STYLE}{timeline.STYLE}</style></head><body><main>"
        + nav("Graveyard")
        + "<h1>Graveyard</h1>"
        "<p class='lead'>Features AFTERLIFE retired from Shelf, what each one cost while it was alive, "
        "and the ones it chose to keep.</p>"
        "<section class='totals'>"
        + _total("features retired", t["retired"])
        + _total("lines removed", t["lines_removed"])
        + _total("dependencies removed", t["deps_removed"])
        + _total("CVEs removed", t["cves_removed"], good=True)
        + _total("MB image saved", t["image_mb_saved"])
        + _total("gCO2e saved per pipeline run", t["sci_gco2e_saved"], digits=4, good=True)
        + "</section>"
        + live
        + _h2("Retired", len(ledger["retired"]), "retired") + f"<section class='stones'>{stones}</section>"
        + _h2("Hibernating", len(ledger["hibernating"]), "hibernating")
        + "<p class='lead'>Quiet, but not dead. The Coroner refused to retire these.</p>"
        + _table(ledger["hibernating"], [("Feature", "feature"), ("Why it was kept", "reason"),
                                         ("Check again", "recheck")], "No hibernating features.", cells=feature)
        + _h2("Resurrected", len(ledger["resurrected"]), "resurrected")
        + "<p class='lead'>Switched off for the vigil, then somebody knocked. Nothing was deleted.</p>"
        + _table(ledger["resurrected"], [("Feature", "feature"), ("Who knocked", "caller"),
                                         ("When", "knocked_at"), ("Why", "reason"), ("Check again", "recheck")],
                 "Nobody has knocked yet.",
                 cells={**feature, "caller": lambda e: f"<span class='mono'>{escape(str(e.get('caller', '')))}</span>",
                        "knocked_at": lambda e: _when(e.get("knocked_at", ""))})
        + _h2("Protected", len(ledger["protected"]), "protected")
        + "<p class='lead'>Never auto-retired, however quiet. Policy decides, not the agents.</p>"
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
        + "<footer>Every number is measured by a CI job and links to it. Usage history in this demo is "
        "simulated and labelled as such in the census.</footer>"
        "</main>"
        + (timeline.REFRESH_SCRIPT if timeline_html is not None else "")
        + "</body></html>"
    )


@router.get("/graveyard", response_class=HTMLResponse)
def graveyard(request: Request) -> str:
    store = request.app.state.store
    window = census_window_days()
    return render(load_ledger(), store.all_savings(), cached_census(store, window), window,
                  timeline.render_timeline(*timeline.cached_timeline()))


@router.get("/graveyard/timeline", response_class=HTMLResponse)
def graveyard_timeline() -> str:
    """The timeline section alone, for the page's 15-second refresh."""
    return timeline.render_timeline(*timeline.cached_timeline())
