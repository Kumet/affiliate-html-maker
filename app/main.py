from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers import download, htmx, pages


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)
    app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")
    app.include_router(pages.router)
    app.include_router(htmx.router)
    app.include_router(download.router)
    return app


app = create_app()
