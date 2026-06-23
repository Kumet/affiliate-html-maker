from __future__ import annotations

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.services.email_parser import parse_email_text
from app.services.html_builder import build_preview_html, render_template
from app.services.image_mail_parser import parse_image_mail_url
from app.services.text_parser import parse_text

router = APIRouter()


@router.post("/preview", response_class=HTMLResponse)
async def preview(source_text: str = Form(...), parse_mode: str = Form("product")) -> HTMLResponse:
    try:
        if parse_mode == "email":
            sections = parse_email_text(source_text, get_settings().affiliate_tag)
        elif parse_mode == "image_url":
            settings = get_settings()
            sections = parse_image_mail_url(
                source_text.strip(),
                settings.affiliate_tag,
                settings.ocr_space_api_key,
            )
        else:
            sections = parse_text(source_text)
    except ValueError as exc:
        error_html = render_template("partials/error.html", message=str(exc))
        return HTMLResponse(content=error_html, status_code=400)

    preview_html = build_preview_html(sections)
    return HTMLResponse(content=preview_html)
