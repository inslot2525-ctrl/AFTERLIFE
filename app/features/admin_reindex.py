"""Admin reindex. Rarely called, but listed in protected_paths: never auto-retired."""

import os
import secrets

from fastapi import APIRouter, Depends, Header, HTTPException

from app.catalog import BOOKS
from app.gate import feature_gate
from app.registry import Feature

FEATURE = Feature(
    name="admin_reindex",
    route="/admin/reindex",
    module="app/features/admin_reindex.py",
    owner="shelf-platform",
    born="2023-02-14",
    summary="Rebuilds the search index; used during incidents",
)

router = APIRouter(dependencies=[Depends(feature_gate(FEATURE.name))])


@router.post("/admin/reindex")
def reindex(x_admin_token: str = Header("")) -> dict:
    expected = os.environ.get("ADMIN_TOKEN", "")
    if not expected or not secrets.compare_digest(x_admin_token, expected):
        raise HTTPException(status_code=403, detail="Admin token required")
    return {"reindexed": len(BOOKS)}
