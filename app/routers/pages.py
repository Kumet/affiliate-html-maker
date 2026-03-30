from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.services.html_builder import load_initial_text, render_template

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    html = render_template(
        "pages/index.html",
        app_name=get_settings().app_name,
        initial_text=load_initial_text(),
    )
    return HTMLResponse(content=html)
