"""The /graveyard page: retired, hibernating, resurrected and protected features."""

import os
from html import escape
from pathlib import Path

import yaml
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

DEFAULT_LEDGER = Path(__file__).resolve().parent.parent / "afterlife" / "graveyard.yaml"

router = APIRouter()


def load_ledger(path: Path | None = None) -> dict:
    path = path or Path(os.environ.get("AFTERLIFE_GRAVEYARD", DEFAULT_LEDGER))
    data = yaml.safe_load(path.read_text()) or {}
    return {key: data.get(key) or [] for key in ("retired", "hibernating", "resurrected", "protected")}


def _section(title: str, entries: list[dict]) -> str:
    if not entries:
        return f"<section><h2>{escape(title)}</h2><p class='empty'>None yet.</p></section>"
    rows = "".join(
        "<li>" + " &middot; ".join(f"<b>{escape(str(k))}</b> {escape(str(v))}" for k, v in entry.items()) + "</li>"
        for entry in entries
    )
    return f"<section><h2>{escape(title)}</h2><ul>{rows}</ul></section>"


@router.get("/graveyard", response_class=HTMLResponse)
def graveyard() -> str:
    ledger = load_ledger()
    sections = "".join(
        _section(title, ledger[key])
        for title, key in (
            ("Retired", "retired"),
            ("Hibernating", "hibernating"),
            ("Resurrected", "resurrected"),
            ("Protected", "protected"),
        )
    )
    return (
        "<!doctype html><html><head><meta charset='utf-8'><title>Graveyard</title>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'></head>"
        f"<body><h1>Graveyard</h1>{sections}</body></html>"
    )
