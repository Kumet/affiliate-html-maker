from __future__ import annotations

import json

from fastapi import APIRouter, Form
from fastapi.responses import HTMLResponse

from app.config import get_settings
from app.services.chatgpt_json_parser import (
    extract_chatgpt_item_indices,
    load_chatgpt_json_payload,
    parse_chatgpt_json,
)
from app.services.email_parser import parse_email_text
from app.services.html_builder import build_preview_html, render_template
from app.services.image_mail_parser import estimate_image_mail_product_count, parse_image_mail_url
from app.services.text_parser import parse_text

router = APIRouter()


@router.post("/preview", response_class=HTMLResponse)
async def preview(
    source_text: str = Form(...),
    parse_mode: str = Form("product"),
    original_image_url: str = Form(""),
    expected_product_count: int = Form(0),
    product_manifest_json: str = Form(""),
) -> HTMLResponse:
    try:
        settings = get_settings()
        warning_html = ""
        if parse_mode == "email":
            sections = parse_email_text(source_text, settings.affiliate_tag)
        elif parse_mode == "chatgpt_json":
            payload = load_chatgpt_json_payload(source_text)
            sections = parse_chatgpt_json(source_text, settings.affiliate_tag)
            expected_count = expected_product_count
            if expected_count <= 0 and original_image_url.strip():
                expected_count = estimate_image_mail_product_count(original_image_url.strip())

            actual_count = sum(len(section.products) for section in sections)
            if expected_count > 0 and actual_count < expected_count:
                missing_message = ""
                if product_manifest_json.strip():
                    try:
                        manifest = json.loads(product_manifest_json)
                    except json.JSONDecodeError:
                        manifest = []
                    actual_indices = set(extract_chatgpt_item_indices(payload))
                    missing_items = [
                        item for item in manifest
                        if isinstance(item, dict) and item.get("item_index") not in actual_indices
                    ]
                    if missing_items:
                        labels = []
                        for item in missing_items:
                            image_names = item.get("image_names") or []
                            label = f"#{item.get('item_index')}"
                            if image_names:
                                label += f" ({', '.join(str(name) for name in image_names)})"
                            labels.append(label)
                        missing_message = " 未返却の画像: " + " / ".join(labels)

                warning_html = render_template(
                    "partials/warning.html",
                    title="商品数が不足している可能性があります。",
                    message=(
                        f"画像URLからの想定商品数は {expected_count} 件ですが、"
                        f"ChatGPT返答JSONでは {actual_count} 件でした。"
                        " 省略せず全商品を返すよう再抽出してください。"
                        f"{missing_message}"
                    ),
                )
        elif parse_mode == "image_url":
            if not settings.enable_image_url_mode:
                raise ValueError("この環境では画像メールURL機能は無効です。")
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
    return HTMLResponse(content=f"{warning_html}{preview_html}")
