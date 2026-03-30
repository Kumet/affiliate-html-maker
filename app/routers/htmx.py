from __future__ import annotations

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from app.services.html_builder import build_preview_html, render_template
from app.services.text_parser import parse_text

router = APIRouter()


@router.post("/preview", response_class=HTMLResponse)
async def preview(source_text: str = Form(...)) -> HTMLResponse:
    try:
        sections = parse_text(source_text)
    except ValueError as exc:
        error_html = render_template("partials/error.html", message=str(exc))
        button_html = render_template("partials/download_button.html", disabled=True, oob=True)
        return HTMLResponse(content=error_html + button_html, status_code=400)

    preview_html = build_preview_html(sections)
    button_html = render_template("partials/download_button.html", disabled=False, oob=True)
    return HTMLResponse(content=preview_html + button_html)
