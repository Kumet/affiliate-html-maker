from __future__ import annotations

import re

from app.schemas.product import Badge, PriceLine, Product
from app.schemas.section import Section
from app.services.amazon_link_builder import build_url

BADGE_TEXTS = ("HOT BUY", "ONLINE ONLY", "NEW", "LAST CHANCE")
FOOTER_MARKERS = ("Follow Us", "【なりすましサイトについて】", "© Costco Wholesale")
HEADER_NOISE_MARKERS = (
    "何も選択されていません",
    "コンテンツへ",
    "メール でのスクリーン リーダーの使用",
    "受信トレイ",
    "To 自分",
    "登録解除",
    "メールが正しく表示されない方は、こちら をご覧ください。",
    "Costco Wholesale",
    "HOTBUY\tNEW\tONLINEONLY",
)
IGNORED_LINES = {"Costco", "auto", "ttl", "　"}
SECTION_PREFIXES = ("【",)
CURRENCY_RE = re.compile(r"^¥\s*[\d,]+(?:\s*-\s*¥\s*[\d,]+)?(?:\s*OFF)?$")
CTA_RE = re.compile(r".*(?:Shop Now >|もっと見る[＞>]).*")


def parse_email_text(source_text: str, affiliate_tag: str) -> list[Section]:
    lines = _normalize_lines(source_text)
    sections: list[Section] = []
    current_section = Section()
    sections.append(current_section)
    index = 0

    while index < len(lines):
        line = lines[index]

        if _is_section_heading(line):
            current_section = Section(title=_clean_section_title(line))
            sections.append(current_section)
            index += 1
            continue

        if _looks_like_product_pair_start(line):
            products, index = _parse_pair_block(lines, index, affiliate_tag)
            current_section.products.extend(products)
            continue

        index += 1

    parsed_sections = [section for section in sections if section.products]
    if not parsed_sections:
        raise ValueError("メール本文から商品情報を抽出できませんでした。内容を確認してください。")

    return parsed_sections


def _normalize_lines(source_text: str) -> list[str]:
    raw_lines = source_text.replace("\r\n", "\n").split("\n")
    lines: list[str] = []
    started = False

    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line:
            continue

        if any(marker in line for marker in FOOTER_MARKERS):
            break

        if _is_header_noise(line):
            continue

        if not started and not (_looks_like_product_pair_start(line) or _is_section_heading(line)):
            continue

        started = True
        lines.append(line)

    return lines


def _parse_pair_block(lines: list[str], start_index: int, affiliate_tag: str) -> tuple[list[Product], int]:
    teaser_parts = [part.strip() for part in lines[start_index].split("\t") if part.strip()]
    fallback_titles = teaser_parts[:2]
    index = start_index + 1

    while index < len(lines) and _is_block_badge_line(lines[index]):
        index += 1

    left_product, index = _parse_product_info(lines, index, fallback_titles[0], affiliate_tag)
    right_fallback = fallback_titles[1] if len(fallback_titles) > 1 else fallback_titles[0]
    right_product, index = _parse_product_info(lines, index, right_fallback, affiliate_tag)

    left_price_lines, left_badges, left_meta, index = _parse_price_block(lines, index)
    right_price_lines, right_badges, right_meta, index = _parse_price_block(lines, index)

    left_product.price_lines.extend(left_price_lines)
    left_product.badges.extend(left_badges)
    left_product.meta_lines.extend(left_meta)

    right_product.price_lines.extend(right_price_lines)
    right_product.badges.extend(right_badges)
    right_product.meta_lines.extend(right_meta)

    return [left_product, right_product], index


def _parse_product_info(
    lines: list[str], start_index: int, fallback_title: str, affiliate_tag: str
) -> tuple[Product, int]:
    info_lines: list[str] = []
    item_line = ""
    badges: list[Badge] = []
    index = start_index

    while index < len(lines):
        line = lines[index]
        if line.startswith("ITEM #"):
            item_line = line
            index += 1
            break
        if _looks_like_terminal_line(line):
            break
        if _looks_like_product_pair_start(line) or _is_section_heading(line):
            break
        if not _is_block_badge_line(line):
            info_lines.append(line)
        index += 1

    title = _choose_title(info_lines, fallback_title)
    meta_lines = []
    for line in info_lines:
        if line == title or _looks_like_english_line(line):
            continue
        meta_lines.append(line)

    if item_line:
        item_meta, item_badges = _parse_item_line(item_line)
        if item_meta:
            meta_lines.append(item_meta)
        badges.extend(item_badges)

    product = Product(
        title=title,
        amazon_url=build_url(title, affiliate_tag),
        search_keyword=title,
        meta_lines=meta_lines,
        badges=badges,
        price_lines=[],
        raw_lines=[fallback_title, *info_lines, item_line],
    )
    return product, index


def _parse_price_block(
    lines: list[str], start_index: int
) -> tuple[list[PriceLine], list[Badge], list[str], int]:
    raw_lines: list[str] = []
    badges: list[Badge] = []
    meta_lines: list[str] = []
    index = start_index

    while index < len(lines):
        line = lines[index]
        if _is_cta_line(line):
            index += 1
            break
        if _looks_like_product_pair_start(line) or _is_section_heading(line):
            break
        if line not in IGNORED_LINES:
            raw_lines.append(line)
        index += 1

    price_lines = _build_price_lines(raw_lines)

    for line in raw_lines:
        if "定期購入対象" in line:
            badges.append(Badge(text=line, variant="gray"))
            meta_lines.append(f"※{line}")

    return price_lines, badges, meta_lines, index


def _build_price_lines(raw_lines: list[str]) -> list[PriceLine]:
    cleaned = [line for line in raw_lines if line and "定期購入対象" not in line]
    if not cleaned:
        return []

    original_price = ""
    final_price = ""
    direct_lines: list[str] = []

    for line in cleaned:
        if line.startswith("Price\t"):
            original_price = line.split("\t", 1)[1].strip()
        elif line.startswith("Off\t"):
            continue
        elif CURRENCY_RE.fullmatch(line):
            if original_price and not final_price:
                final_price = line
            else:
                direct_lines.append(line)

    if original_price:
        discounted = final_price or None
        return [
            PriceLine(
                label="価格",
                value=original_price,
                discounted_value=discounted,
                raw=" / ".join(cleaned),
            )
        ]

    if direct_lines:
        return [
            PriceLine(
                label="割引" if "OFF" in line else "価格",
                value=line,
                raw=line,
            )
            for line in direct_lines
        ]

    return []


def _parse_item_line(item_line: str) -> tuple[str, list[Badge]]:
    parts = [part.strip() for part in item_line.split("\t") if part.strip()]
    item_meta = parts[0]
    badges: list[Badge] = []

    for part in parts[1:]:
        for badge_text in _extract_badge_tokens(part):
            badges.append(Badge(text=badge_text))

    return item_meta, badges


def _extract_badge_tokens(text: str) -> list[str]:
    found: list[str] = []
    for badge_text in BADGE_TEXTS:
        if badge_text in text and badge_text not in found:
            found.append(badge_text)
    return found


def _choose_title(info_lines: list[str], fallback_title: str) -> str:
    for line in info_lines:
        if not _looks_like_english_line(line):
            return line
    return fallback_title


def _looks_like_product_pair_start(line: str) -> bool:
    if "\t" not in line:
        return False
    if any(token in line for token in ("Price\t", "Off\t", "ITEM #", "Shop Now >", "Facebook icon")):
        return False
    if "もっと見る" in line:
        return False
    parts = [part.strip() for part in line.split("\t") if part.strip()]
    return len(parts) >= 2


def _is_block_badge_line(line: str) -> bool:
    if "\t" in line:
        return False
    return any(badge_text in line for badge_text in BADGE_TEXTS)


def _looks_like_terminal_line(line: str) -> bool:
    return line.startswith("Price\t") or line.startswith("Off\t") or CURRENCY_RE.fullmatch(line) is not None


def _is_cta_line(line: str) -> bool:
    return CTA_RE.fullmatch(line) is not None


def _looks_like_english_line(line: str) -> bool:
    ascii_letters = sum(character.isascii() and character.isalpha() for character in line)
    japanese_chars = sum(
        ("\u3040" <= character <= "\u30ff") or ("\u4e00" <= character <= "\u9fff") for character in line
    )
    return ascii_letters > 0 and japanese_chars == 0


def _is_section_heading(line: str) -> bool:
    return line.startswith(SECTION_PREFIXES)


def _clean_section_title(line: str) -> str:
    return line.replace("　", " ").strip()


def _is_header_noise(line: str) -> bool:
    if line in IGNORED_LINES:
        return True
    return any(marker in line for marker in HEADER_NOISE_MARKERS)
