from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.services.chatgpt_image_bundle import CHATGPT_EXTRACTION_PROMPT
from app.services.html_builder import load_initial_text, load_static_asset, render_template

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    settings = get_settings()
    html = render_template(
        "pages/index.html",
        app_name=settings.app_name,
        initial_text=load_initial_text(),
        chatgpt_extraction_prompt=CHATGPT_EXTRACTION_PROMPT,
        enable_image_url_mode=settings.enable_image_url_mode,
        inline_assets_mode=settings.inline_assets_mode,
        inline_css=load_static_asset("css/app.css") if settings.inline_assets_mode else "",
        inline_js=load_static_asset("js/app.js") if settings.inline_assets_mode else "",
    )
    return HTMLResponse(content=html)
