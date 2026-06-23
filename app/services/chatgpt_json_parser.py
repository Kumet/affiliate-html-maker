from __future__ import annotations

import json
from typing import Any

from app.schemas.product import Badge, PriceLine, Product
from app.schemas.section import Section
from app.services.amazon_link_builder import build_url


def parse_chatgpt_json(source_text: str, affiliate_tag: str) -> list[Section]:
    payload = load_chatgpt_json_payload(source_text)
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


def load_chatgpt_json_payload(source_text: str) -> Any:
    candidate = _unwrap_json_code_block(source_text)
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise ValueError(f"ChatGPTの返答JSONを解析できませんでした: {exc.msg}") from exc


def extract_chatgpt_item_indices(payload: Any) -> list[int]:
    sections = _coerce_sections(payload)
    indices: list[int] = []
    for section in sections:
        products = section.get("products")
        if not isinstance(products, list):
            continue
        for product in products:
            if not isinstance(product, dict):
                continue
            item_index = product.get("item_index")
            if isinstance(item_index, int):
                indices.append(item_index)
            elif isinstance(item_index, str) and item_index.isdigit():
                indices.append(int(item_index))
    return indices


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
    title = _as_optional_string(data.get("title")) or _fallback_product_title(data)

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

    if not title and not meta_lines and not badges and not price_lines:
        raise ValueError("product の内容が空です。")

    return Product(
        title=title,
        amazon_url=build_url(title or "costco item", affiliate_tag),
        search_keyword=title or "costco item",
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


def _fallback_product_title(data: dict[str, Any]) -> str:
    item_index = data.get("item_index")
    if item_index is not None:
        return f"商品 {item_index}"
    return "商品情報要確認"


def _unwrap_json_code_block(source_text: str) -> str:
    stripped = source_text.strip()
    if not stripped.startswith("```"):
        return stripped

    lines = stripped.splitlines()
    if len(lines) < 3:
        return stripped

    first_line = lines[0].strip().lower()
    last_line = lines[-1].strip()
    if first_line in {"```json", "```"} and last_line == "```":
        return "\n".join(lines[1:-1]).strip()
    return stripped
