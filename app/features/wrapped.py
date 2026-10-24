"""Year-in-review. Quiet most of the year, busy every December."""

from fastapi import APIRouter, Depends

from app.catalog import BOOKS
from app.gate import feature_gate
from app.registry import Feature

FEATURE = Feature(
    name="wrapped",
    route="/wrapped/{year}",
    module="app/features/wrapped.py",
    owner="shelf-growth",
    born="2023-11-20",
    summary="Year-in-review summary of finished books",
)

router = APIRouter(dependencies=[Depends(feature_gate(FEATURE.name))])


@router.get("/wrapped/{year}")
def wrapped(year: int) -> dict:
    finished = [b for b in BOOKS if b["finished"] and b["finished"].startswith(str(year))]
    authors = sorted({b["author"] for b in finished})
    return {"year": year, "books_finished": len(finished), "authors": authors}
