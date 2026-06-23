from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.services.email_parser import parse_email_text
from app.services.html_builder import build_download_html
from app.services.image_mail_parser import parse_image_mail_url
from app.services.text_parser import parse_text

router = APIRouter()


@router.post("/download", response_class=HTMLResponse)
async def download(source_text: str = Form(...), parse_mode: str = Form("product")) -> HTMLResponse:
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
    filename = f"affiliate_{date.today().strftime('%Y%m%d')}.html"
    html = build_download_html(sections, title=filename[:-5])

    return HTMLResponse(
        content=html,
        media_type="text/html",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
