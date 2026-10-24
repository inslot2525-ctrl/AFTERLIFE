"""The /graveyard page: retired, hibernating, resurrected and protected features.

Tombstones come from afterlife/graveyard.yaml (written by the agents in git).
Measured savings come from the store (published by CI after release), so a
tombstone without savings says so instead of showing a number nobody measured.
"""

import os
from html import escape
from pathlib import Path

import yaml
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

DEFAULT_LEDGER = Path(__file__).resolve().parent.parent / "afterlife" / "graveyard.yaml"

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
main { max-width: 1040px; margin: 0 auto; padding: 32px 16px 48px; }
h1 { font-size: 28px; margin: 0 0 4px; letter-spacing: -0.01em; }
h2 { font-size: 18px; margin: 36px 0 12px; }
.lead { color: var(--quiet); margin: 0 0 24px; max-width: 680px; }
.totals { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
.total { background: var(--card); border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px; }
.total b { display: block; font-size: 24px; font-variant-numeric: tabular-nums; }
.total span { color: var(--quiet); font-size: 13px; }
.stones { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.stone { background: var(--stone); border: 1px solid var(--line); border-radius: 120px 120px 12px 12px;
  padding: 40px 20px 18px; text-align: center; }
.stone h3 { margin: 0; font-size: 18px; }
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
tr:last-child td { border-bottom: 0; }
.empty { color: var(--quiet); }
.scroll { overflow-x: auto; }
footer { margin-top: 40px; color: var(--quiet); font-size: 13px; }
"""


def load_ledger(path: Path | None = None) -> dict:
    path = path or Path(os.environ.get("AFTERLIFE_GRAVEYARD", DEFAULT_LEDGER))
    data = yaml.safe_load(path.read_text()) or {}
    return {key: data.get(key) or [] for key in ("retired", "hibernating", "resurrected", "protected")}


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


def _total(label: str, value) -> str:
    shown = "&mdash;" if value is None else escape(_num(value, 4) if isinstance(value, float) and value < 1 else _num(value))
    return f"<div class='total'><b>{shown}</b><span>{escape(label)}</span></div>"


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
             ("Measured by", s.get("measured_job_url"))]
    return "".join(f"<a href='{escape(str(url))}'>{escape(label)}</a>" for label, url in links if url)


def _stone(tomb: dict, savings: dict[str, dict]) -> str:
    s = savings.get(tomb.get("feature"), {})
    measured = (f"<div class='chips'>{_chips(s)}</div>" if s
                else "<p class='pending'>Savings not measured yet: they appear after the release ships.</p>")
    return (
        "<article class='stone'>"
        f"<h3>{escape(str(tomb.get('feature', '?')))}</h3>"
        f"<div class='route'>{escape(str(tomb.get('route', '')))}</div>"
        f"<div class='dates'>{escape(str(tomb.get('born', '?')))} &ndash; {escape(str(tomb.get('died', '?')))}</div>"
        f"<p class='cause'>{escape(str(tomb.get('cause', '')))}</p>"
        f"{measured}<div class='links'>{_links(tomb, s)}</div>"
        "</article>"
    )


def _table(entries: list[dict], columns: list[tuple[str, str]], empty: str) -> str:
    if not entries:
        return f"<p class='empty'>{escape(empty)}</p>"
    head = "".join(f"<th>{escape(title)}</th>" for title, _ in columns)
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(entry.get(key, '')))}</td>" for _, key in columns) + "</tr>"
        for entry in entries
    )
    return f"<div class='scroll'><table><tr>{head}</tr>{rows}</table></div>"


def render(ledger: dict, savings: dict[str, dict]) -> str:
    t = totals(ledger["retired"], savings)
    stones = ("".join(_stone(tomb, savings) for tomb in ledger["retired"])
              or "<p class='empty'>Nothing retired yet.</p>")
    return (
        "<!doctype html><html lang='en'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>Graveyard</title><style>{STYLE}</style></head><body><main>"
        "<h1>Graveyard</h1>"
        "<p class='lead'>Features AFTERLIFE retired from Shelf, what each one cost while it was alive, "
        "and the ones it chose to keep.</p>"
        "<section class='totals'>"
        + _total("features retired", t["retired"])
        + _total("lines removed", t["lines_removed"])
        + _total("dependencies removed", t["deps_removed"])
        + _total("CVEs removed", t["cves_removed"])
        + _total("MB image saved", t["image_mb_saved"])
        + _total("gCO2e saved per pipeline run", t["sci_gco2e_saved"])
        + "</section>"
        f"<h2>Retired</h2><section class='stones'>{stones}</section>"
        "<h2>Hibernating</h2>"
        + _table(ledger["hibernating"], [("Feature", "feature"), ("Why it was kept", "reason"),
                                         ("Check again", "recheck")], "No hibernating features.")
        + "<h2>Resurrected</h2>"
        + _table(ledger["resurrected"], [("Feature", "feature"), ("Who knocked", "caller"),
                                         ("When", "knocked_at"), ("Why", "reason"), ("Check again", "recheck")],
                 "Nobody has knocked yet.")
        + "<h2>Protected</h2>"
        + _table(ledger["protected"], [("Feature", "feature"), ("Reason", "reason")], "No protected features.")
        + "<footer>Every number is measured by a CI job and links to it. Usage history in this demo is "
        "simulated and labelled as such in the census.</footer>"
        "</main></body></html>"
    )


@router.get("/graveyard", response_class=HTMLResponse)
def graveyard(request: Request) -> str:
    return render(load_ledger(), request.app.state.store.all_savings())
