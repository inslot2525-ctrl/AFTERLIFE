"""Shelf: a small reading-list app with a few years of cruft, run by AFTERLIFE."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import graveyard, home
from app.features import MODULES
from app.flags import Flags, flags_from_env
from app.store import UsageStore, store_from_env


def create_app(store: UsageStore | None = None, flags: Flags | None = None) -> FastAPI:
    app = FastAPI(title="Shelf")
    # Partners embed the widget from their own sites (partner-site/ on GitLab Pages):
    # public GETs only, with the partner key header; no credentials.
    app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"],
                       allow_headers=["x-partner-key"])
    app.state.store = store or store_from_env()
    app.state.flags = flags or flags_from_env()

    for module in MODULES:
        app.include_router(module.router)
    app.include_router(graveyard.router)
    app.include_router(home.router)

    # /health is what Cloud Run checks: it reserves paths ending in "z", so /healthz
    # never reaches the app there. /healthz stays for local runs.
    @app.get("/health")
    @app.get("/healthz")
    def health() -> dict:
        return {"ok": True}

    return app


app = create_app()
