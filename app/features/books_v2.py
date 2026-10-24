"""Current books API, paginated and filterable."""

from fastapi import APIRouter, Depends, Query

from app.catalog import BOOKS
from app.gate import feature_gate
from app.registry import Feature

FEATURE = Feature(
    name="books_v2",
    route="/v2/books",
    module="app/features/books_v2.py",
    owner="shelf-api",
    born="2024-05-02",
    summary="Paginated books list with status filter",
)

router = APIRouter(dependencies=[Depends(feature_gate(FEATURE.name))])


@router.get("/v2/books")
def list_books_v2(
    status: str | None = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
) -> dict:
    books = [b for b in BOOKS if status is None or b["status"] == status]
    start = (page - 1) * per_page
    return {"total": len(books), "page": page, "items": books[start:start + per_page]}
