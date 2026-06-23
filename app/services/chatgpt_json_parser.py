from __future__ import annotations

import json
from typing import Any

from app.schemas.product import Badge, PriceLine, Product
from app.schemas.section import Section
from app.services.amazon_link_builder import build_url


def parse_chatgpt_json(source_text: str, affiliate_tag: str) -> list[Section]:
    try:
        payload = json.loads(source_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"ChatGPTの返答JSONを解析できませんでした: {exc.msg}") from exc

    sections_data = _coerce_sections(payload)
    sections: list[Section] = []
    for section_data in sections_data:
        title = _as_optional_string(section_data.get("title") or section_data.get("section_title"))
        product_items = section_data.get("products")
        if not isinstance(product_items, list):
            raise ValueError("sections[].products は配列である必要があります。")

        products = [_build_product(item, affiliate_tag) for item in product_items]
        if products:
            sections.append(Section(title=title, products=products))

    if not sections:
        raise ValueError("ChatGPTの返答JSONから商品を抽出できませんでした。")
    return sections


def _coerce_sections(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if isinstance(payload.get("sections"), list):
            return _ensure_dict_list(payload["sections"], "sections")
        if isinstance(payload.get("products"), list):
            return [payload]
    if isinstance(payload, list):
        return _ensure_dict_list(payload, "root")
    raise ValueError("ChatGPTの返答JSONは sections 配列、products 配列、または配列ルートである必要があります。")


def _ensure_dict_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{label} はオブジェクト配列である必要があります。")
    return value


def _build_product(data: dict[str, Any], affiliate_tag: str) -> Product:
    title = _as_optional_string(data.get("title"))
    if not title:
        raise ValueError("各 product には title が必要です。")

    meta_lines = _as_string_list(data.get("meta_lines"))
    badges = [Badge(text=text) for text in _as_string_list(data.get("badges"))]

    date_badge = _as_optional_string(data.get("date_badge"))
    if date_badge:
        badges.insert(0, Badge(text=date_badge))

    notes = _as_string_list(data.get("notes"))
    meta_lines.extend(notes)

    price = _as_optional_string(data.get("original_price") or data.get("price"))
    discounted_price = _as_optional_string(
        data.get("discounted_price") or data.get("sale_price") or data.get("final_price")
    )
    price_lines: list[PriceLine] = []
    if price:
        price_lines.append(
            PriceLine(
                label="価格",
                value=price,
                discounted_value=discounted_price,
                raw=" / ".join([part for part in (price, discounted_price) if part]),
            )
        )
    elif discounted_price:
        price_lines.append(
            PriceLine(
                label="価格",
                value=discounted_price,
                raw=discounted_price,
            )
        )

    return Product(
        title=title,
        amazon_url=build_url(title, affiliate_tag),
        search_keyword=title,
        meta_lines=meta_lines,
        badges=badges,
        price_lines=price_lines,
        raw_lines=[],
    )


def _as_optional_string(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("配列項目は文字列配列である必要があります。")
    return [str(item).strip() for item in value if str(item).strip()]
