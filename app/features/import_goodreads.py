"""Goodreads CSV import. The only user of `requests` in the app."""

import csv
import io

import requests
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.catalog import add_books
from app.gate import feature_gate
from app.registry import Feature

FEATURE = Feature(
    name="import_goodreads",
    route="/import/goodreads",
    module="app/features/import_goodreads.py",
    owner="shelf-growth",
    born="2023-06-30",
    summary="Imports a Goodreads library export",
)

router = APIRouter(dependencies=[Depends(feature_gate(FEATURE.name))])


class ImportRequest(BaseModel):
    csv_text: str | None = None
    csv_url: str | None = None


def parse_goodreads_csv(text: str) -> list[dict]:
    reader = csv.DictReader(io.StringIO(text))
    return [
        {
            "title": row["Title"].strip(),
            "author": row["Author"].strip(),
            "status": row.get("Exclusive Shelf") or "to-read",
        }
        for row in reader
        if row.get("Title")
    ]


@router.post("/import/goodreads")
def import_goodreads(req: ImportRequest) -> dict:
    if req.csv_text is None and req.csv_url is None:
        raise HTTPException(status_code=422, detail="Send csv_text or csv_url")
    text = req.csv_text if req.csv_text is not None else requests.get(req.csv_url, timeout=10).text
    books = parse_goodreads_csv(text)
    add_books(books)
    return {"imported": len(books)}
