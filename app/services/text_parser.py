from __future__ import annotations

import re

from app.config import get_settings
from app.schemas.product import Badge, PriceLine, Product
from app.schemas.section import Section
from app.services.amazon_link_builder import build_url

DATE_LINE_RE = re.compile(r"^(?:発券期間\s*:\s*)?(?:\d{1,2}/\d{1,2})?(?:～\d{1,2}/\d{1,2})?(?:限定)?$")
MODEL_CODE_RE = re.compile(r"[A-Z0-9]{2,}(?:[-/][A-Z0-9]{2,})+|[A-Z]{2,}\d[A-Z0-9-]*")
MEASUREMENT_RE = re.compile(
    r"\d[\d,./x× ()-]*(?:g|kg|ml|mL|L|cm|mm|m|型|玉|本|袋|枚|個|食|缶|包|回分|パック|ピース|セット|カラット|錠)"
)
DESCRIPTION_MARKERS = ("。", "！", "!", "おすすめ", "快適", "使用", "仕上", "発行", "有効")


def parse_text(source_text: str) -> list[Section]:
    settings = get_settings()
    lines = [line.strip() for line in source_text.replace("\r\n", "\n").split("\n")]
    sections: list[Section] = []
    current_section: Section | None = None
    current_block: list[str] = []

    def ensure_section() -> Section:
        nonlocal current_section
        if current_section is None:
            current_section = Section()
            sections.append(current_section)
        return current_section

    def flush_block() -> None:
        nonlocal current_block
        if not current_block:
            return
        ensure_section().products.append(_parse_product_block(current_block, settings.affiliate_tag))
        current_block = []

    for line in lines:
        if not line:
            flush_block()
            continue

        if not current_block and _is_section_heading(line):
            current_section = Section(title=line)
            sections.append(current_section)
            continue

        current_block.append(line)

    flush_block()

    parsed_sections = [section for section in sections if section.products]
    if not parsed_sections:
        raise ValueError("商品テキストを解析できませんでした。入力内容を確認してください。")

    return parsed_sections


def _parse_product_block(lines: list[str], affiliate_tag: str) -> Product:
    title_line_count = _determine_title_line_count(lines)
    title = " ".join(lines[:title_line_count]).strip()

    meta_lines: list[str] = []
    badges: list[Badge] = []
    price_lines: list[PriceLine] = []

    for line in lines[title_line_count:]:
        if _is_date_line(line):
            badges.append(Badge(text=line))
            continue

        if _is_note_line(line):
            note_text = line[1:].strip()
            badges.append(Badge(text=note_text, variant="gray"))
            meta_lines.append(line)
            continue

        if _is_price_line(line):
            price_line = _parse_price_line(line)
            price_lines.append(price_line)
            if _should_promote_price_to_badge(price_line):
                badges.append(Badge(text=price_line.raw))
            continue

        meta_lines.append(line)

    return Product(
        title=title,
        amazon_url=build_url(title, affiliate_tag),
        search_keyword=title,
        meta_lines=meta_lines,
        badges=badges,
        price_lines=price_lines,
        raw_lines=lines,
    )


def _determine_title_line_count(lines: list[str]) -> int:
    if len(lines) == 1:
        return 1

    first_special_index = next(
        (index for index, line in enumerate(lines) if _is_price_line(line) or _is_date_line(line) or _is_note_line(line)),
        len(lines),
    )
    leading_lines = lines[:first_special_index]
    price_count = sum(1 for line in lines if _is_price_line(line))

    if len(leading_lines) < 2:
        return 1

    second = leading_lines[1]
    if _looks_like_description(second):
        return 1

    if _looks_like_size_or_spec(second):
        if second.endswith("型") and _contains_ascii(leading_lines[0]):
            return 2
        return 1

    if price_count > 1 and len(leading_lines) == 2 and not _contains_ascii(leading_lines[0]):
        return 1

    first = leading_lines[0]
    if _contains_ascii(first):
        return 2

    if len(first) <= 8 and len(second) <= 18:
        return 2

    return 1


def _parse_price_line(line: str) -> PriceLine:
    raw = line.strip()

    if "⇒" in raw:
        left, right = [part.strip() for part in raw.split("⇒", 1)]
        label_prefix, value = _split_label_and_value(left)
        label = label_prefix or "価格"
        return PriceLine(label=label, value=value, discounted_value=right, raw=raw)

    label_prefix, value = _split_label_and_value(raw)
    if label_prefix.endswith("特別価格") and label_prefix not in {"特別価格", "各種 特別価格"}:
        return PriceLine(label="価格", value=raw, raw=raw)

    label = label_prefix or ("割引" if "OFF" in raw else "価格")
    value_text = value if label_prefix else raw
    return PriceLine(label=label, value=value_text, raw=raw)


def _split_label_and_value(line: str) -> tuple[str, str]:
    yen_index = line.find("￥")
    if yen_index == -1:
        return "", line.strip()

    label = line[:yen_index].strip()
    value = line[yen_index:].strip()
    return label, value


def _is_section_heading(line: str) -> bool:
    settings = get_settings()
    return line in settings.section_keywords


def _is_note_line(line: str) -> bool:
    return line.startswith("※")


def _is_date_line(line: str) -> bool:
    return bool(DATE_LINE_RE.fullmatch(line))


def _is_price_line(line: str) -> bool:
    return "￥" in line and not _is_note_line(line)


def _should_promote_price_to_badge(price_line: PriceLine) -> bool:
    return price_line.discounted_value is None and "/" in price_line.raw


def _looks_like_description(line: str) -> bool:
    if any(marker in line for marker in DESCRIPTION_MARKERS):
        return True
    return len(line) >= 22 and not _contains_ascii(line)


def _looks_like_size_or_spec(line: str) -> bool:
    if MODEL_CODE_RE.search(line):
        return True
    if line.startswith("[") and line.endswith("]"):
        return True
    if "サイズ" in line:
        return True
    return bool(MEASUREMENT_RE.search(line))


def _contains_ascii(line: str) -> bool:
    return any(character.isascii() and character.isalpha() for character in line)
