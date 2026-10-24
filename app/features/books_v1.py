"""Legacy books listing. Superseded by /v2/books."""

from fastapi import APIRouter, Depends

from app.catalog import BOOKS
from app.gate import feature_gate
from app.registry import Feature

FEATURE = Feature(
    name="books_v1",
    route="/v1/books",
    module="app/features/books_v1.py",
    owner="shelf-api",
    born="2023-02-14",
    summary="Legacy flat books list, replaced by /v2/books",
)

router = APIRouter(dependencies=[Depends(feature_gate(FEATURE.name))])


@router.get("/v1/books")
def list_books_v1() -> list[dict]:
    return [{"title": b["title"], "author": b["author"]} for b in BOOKS]
