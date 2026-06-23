from __future__ import annotations

import base64
from datetime import date

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse, Response

from app.config import get_settings
from app.services.chatgpt_image_bundle import build_chatgpt_image_bundle
from app.services.chatgpt_json_parser import parse_chatgpt_json
from app.services.email_parser import parse_email_text
from app.services.html_builder import build_download_html
from app.services.image_mail_parser import parse_image_mail_url
from app.services.text_parser import parse_text

router = APIRouter()


@router.post("/download", response_class=HTMLResponse)
async def download(source_text: str = Form(...), parse_mode: str = Form("product")) -> HTMLResponse:
    settings = get_settings()
    if parse_mode == "email":
        sections = parse_email_text(source_text, settings.affiliate_tag)
    elif parse_mode == "chatgpt_json":
        sections = parse_chatgpt_json(source_text, settings.affiliate_tag)
    elif parse_mode == "image_url":
        if not settings.enable_image_url_mode:
            return HTMLResponse(content="この環境では画像メールURL機能は無効です。", status_code=400)
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


@router.post("/download-chatgpt-image")
async def download_chatgpt_image(source_text: str = Form(...)) -> Response:
    bundle = build_chatgpt_image_bundle(source_text.strip())
    return Response(
        content=bundle.content,
        media_type=bundle.media_type,
        headers={
            "Content-Disposition": f'attachment; filename="{bundle.filename}"',
            "X-Expected-Products": str(bundle.product_count),
            "X-Product-Manifest": base64.b64encode(bundle.product_manifest_json.encode("utf-8")).decode("ascii"),
        },
    )
