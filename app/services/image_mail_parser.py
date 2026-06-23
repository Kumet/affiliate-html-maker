from __future__ import annotations

import json
import re
import tempfile
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import PurePosixPath
from typing import Iterable, NamedTuple

import pytesseract
from PIL import Image, ImageOps

from app.schemas.product import Badge, PriceLine, Product
from app.schemas.section import Section
from app.services.amazon_link_builder import build_url

OCR_API_URL = "https://api.ocr.space/parse/imageurl"
PRODUCT_IMAGE_RE = re.compile(r'/img\d+/s[\w-]+(?:_\d+)?\.(?:jpg|jpeg|png)$', re.IGNORECASE)
SECTION_IMAGE_RE = re.compile(r'/img\d+/(gray\d*|gray)\.(?:jpg|jpeg|png)$', re.IGNORECASE)
IMG_TAG_RE = re.compile(r'<img[^>]+src="([^"]+)"[^>]*alt="([^"]*)"', re.IGNORECASE)
YEN_RE = re.compile(r"¥\s*[\d,./]+(?:\s*-\s*¥\s*[\d,./]+)?(?:\s*OFF)?")
DATE_RE = re.compile(r"^(?:～?\d{1,2}/\d{1,2})(?:～\d{1,2}/\d{1,2})?$")
SIZE_RE = re.compile(
    r"\d[\d,./x×X() -]*(?:g|kg|ml|mL|L|cm|mm|個|本|袋|枚|台|セット|入り|入|回分|パック)"
)
ITEM_RE = re.compile(r"ITEM[#＃]?\s*([0-9A-Z# ]+)")
ENGLISH_HINT_RE = re.compile(r"^[A-Za-z0-9/&+,'\"(). -]+$")
NOISE_MARKERS = {"PRICE", "OFF", "SHOP NOW", "ONLINE ONLY", "HOT BUY", "NEW", "LAST CHANCE"}
GENERIC_META_RE = re.compile(
    r"(衣料用柔軟剤|液体洗濯洗剤|手洗い用食器洗剤|車用消臭芳香剤|本体\d|つめかえ|トイレ用消臭剤|ヘアマスク|電動歯ブラシ)$"
)
METAISH_RE = re.compile(r"(?:UP|%|回分|[^\s]+用$|つめかえ|詰替|詰め替え|本体\d|個パック)")


class ImageEntry(NamedTuple):
    src: str
    alt: str


class ProductImageGroup(NamedTuple):
    srcs: tuple[str, ...]
    alt: str


@lru_cache(maxsize=16)
def parse_image_mail_url(url: str, affiliate_tag: str, api_key: str) -> list[Section]:
    html = _fetch_html(url)
    entries = _extract_image_entries(html)
    sections = _build_sections_from_images(entries, affiliate_tag, api_key)
    parsed_sections = [section for section in sections if section.products]
    if not parsed_sections:
        raise ValueError("画像メールURLから商品情報を抽出できませんでした。URLかOCR結果を確認してください。")
    return parsed_sections


def _fetch_html(url: str) -> str:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            content = response.read()
    except Exception as exc:  # pragma: no cover - network specific
        raise ValueError(f"画像メールURLを取得できませんでした: {exc}") from exc

    for encoding in ("shift_jis", "cp932", "utf-8"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    return content.decode("utf-8", "ignore")


def _extract_image_entries(html: str) -> list[ImageEntry]:
    entries = [ImageEntry(src=src, alt=alt.strip()) for src, alt in IMG_TAG_RE.findall(html)]
    if not entries:
        raise ValueError("画像メールHTMLから画像を抽出できませんでした。")
    return entries


def _build_sections_from_images(
    entries: list[ImageEntry], affiliate_tag: str, api_key: str
) -> list[Section]:
    sections: list[Section] = []
    current_section = Section()
    sections.append(current_section)

    product_entries: list[tuple[Section, ProductImageGroup]] = []
    pending_section = current_section
    pending_group: ProductImageGroup | None = None
    for entry in entries:
        if SECTION_IMAGE_RE.search(entry.src):
            if pending_group is not None:
                product_entries.append((pending_section, pending_group))
                pending_group = None
            title = entry.alt or None
            if title:
                current_section = Section(title=title)
                sections.append(current_section)
                pending_section = current_section
            continue
        if PRODUCT_IMAGE_RE.search(entry.src):
            if pending_group is None:
                pending_group = ProductImageGroup(srcs=(entry.src,), alt=entry.alt)
                pending_section = current_section
            elif _image_group_key(pending_group.srcs[-1]) == _image_group_key(entry.src):
                pending_group = ProductImageGroup(srcs=(*pending_group.srcs, entry.src), alt=entry.alt)
            else:
                product_entries.append((pending_section, pending_group))
                pending_group = ProductImageGroup(srcs=(entry.src,), alt=entry.alt)
                pending_section = current_section

    if pending_group is not None:
        product_entries.append((pending_section, pending_group))

    if not product_entries:
        raise ValueError("商品画像が見つかりませんでした。")

    with ThreadPoolExecutor(max_workers=4) as executor:
        parsed_products = list(
            executor.map(
                lambda item: _ocr_and_parse_product(item[1], affiliate_tag, api_key),
                product_entries,
            )
        )

    for (section, _), product in zip(product_entries, parsed_products):
        section.products.append(product)

    return sections


def _ocr_and_parse_product(entry: ProductImageGroup, affiliate_tag: str, api_key: str) -> Product:
    ocr_text = "\n".join(_ocr_image_url(src, api_key) for src in entry.srcs)
    return _parse_ocr_product_text(ocr_text, entry.srcs[0], affiliate_tag)


@lru_cache(maxsize=256)
def _ocr_image_url(image_url: str, api_key: str) -> str:
    if api_key == "helloworld":
        return _ocr_image_url_local(image_url)

    params = urllib.parse.urlencode(
        {
            "apikey": api_key,
            "url": image_url,
            "language": "jpn",
            "OCREngine": 2,
            "isOverlayRequired": "false",
            "scale": "true",
        }
    )
    request_url = f"{OCR_API_URL}?{params}"
    try:
        with urllib.request.urlopen(request_url, timeout=90) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception:
        return _ocr_image_url_local(image_url)

    if data.get("IsErroredOnProcessing"):
        return _ocr_image_url_local(image_url)

    parsed_results = data.get("ParsedResults") or []
    if not parsed_results:
        raise ValueError("OCR結果が空でした。")

    parsed_text = parsed_results[0].get("ParsedText", "").strip()
    if not parsed_text:
        return _ocr_image_url_local(image_url)
    return parsed_text


@lru_cache(maxsize=256)
def _ocr_image_url_local(image_url: str) -> str:
    try:
        with urllib.request.urlopen(image_url, timeout=60) as response:
            image_bytes = response.read()
    except Exception as exc:  # pragma: no cover - network specific
        raise ValueError(f"商品画像を取得できませんでした: {exc}") from exc

    with tempfile.NamedTemporaryFile(suffix=".jpg") as temp_file:
        temp_file.write(image_bytes)
        temp_file.flush()
        image = Image.open(temp_file.name)
        image = image.convert("L")
        image = ImageOps.autocontrast(image)
        image = image.resize((image.width * 2, image.height * 2))
        text = pytesseract.image_to_string(image, lang="jpn+eng", config="--psm 6")

    if not text.strip():
        raise ValueError("ローカルOCRでもテキストを抽出できませんでした。")
    return text


def _parse_ocr_product_text(ocr_text: str, image_url: str, affiliate_tag: str) -> Product:
    lines = _normalize_ocr_lines(ocr_text)
    item_code = ""
    date_text = ""
    item_index = None
    date_index = None
    price_index = None

    for index, line in enumerate(lines):
        if item_index is None and "ITEM" in line.upper():
            item_index = index
            match = ITEM_RE.search(line.upper().replace(" ", ""))
            if match:
                item_code = match.group(1)
        if date_index is None and DATE_RE.fullmatch(line):
            date_index = index
            date_text = line
        if price_index is None and YEN_RE.search(line):
            price_index = index

    cutoff_candidates = [idx for idx in (item_index, date_index, price_index) if idx is not None]
    cutoff_index = min(cutoff_candidates) if cutoff_candidates else len(lines)
    content_lines = lines[:cutoff_index]
    price_lines_source = lines[cutoff_index:]

    title, meta_lines = _extract_title_and_meta(content_lines)
    if not title:
        title = image_url.rsplit("/", 1)[-1]

    badges: list[Badge] = []
    if date_text:
        badges.append(Badge(text=date_text))

    if item_code:
        meta_lines.append(f"ITEM #{item_code}")

    price_lines = _extract_price_lines(price_lines_source)
    for price_line in price_lines:
        if price_line.discounted_value is None and "/" in price_line.value:
            badges.append(Badge(text=price_line.value))

    return Product(
        title=title,
        amazon_url=build_url(title, affiliate_tag),
        search_keyword=title,
        meta_lines=meta_lines,
        badges=badges,
        price_lines=price_lines,
        raw_lines=lines,
    )


def _normalize_ocr_lines(ocr_text: str) -> list[str]:
    normalized: list[str] = []
    for raw_line in ocr_text.splitlines():
        line = raw_line.strip().replace("✕", "x").replace("　", " ")
        line = re.sub(r"\s+", " ", line)
        line = line.replace("ITEM# ", "ITEM#").replace("ITEM # ", "ITEM#")
        if not line:
            continue
        upper = line.upper()
        if upper in NOISE_MARKERS:
            continue
        line = re.sub(r"^(?:price|off|or)\b[:\s]*", "", line, flags=re.IGNORECASE)
        normalized.append(line)
    return normalized


def _extract_title_and_meta(lines: list[str]) -> tuple[str, list[str]]:
    if not lines:
        return "", []

    start_index = _find_product_block_start(lines)
    duplicate_started = start_index > 0 and lines[start_index] in lines[:start_index]
    block = lines[start_index:]

    title_lines: list[str] = []
    meta_lines: list[str] = []
    filtered_title_candidates: list[str] = []
    for line in block:
        if SIZE_RE.search(line) or _is_metaish_line(line):
            meta_lines.append(line)
            continue
        if ENGLISH_HINT_RE.fullmatch(line):
            continue
        filtered_title_candidates.append(line)

    title_lines = _choose_title_lines(filtered_title_candidates, duplicate_started)
    used = set(title_lines)
    for line in filtered_title_candidates:
        if line in used:
            used.remove(line)
            continue
        meta_lines.append(line)

    return " ".join(title_lines).strip(), meta_lines


def _find_product_block_start(lines: list[str]) -> int:
    seen: dict[str, int] = {}
    for index, line in enumerate(lines):
        seen[line] = seen.get(line, 0) + 1
        if seen[line] == 2:
            return index
    if len(lines) <= 2:
        return 0
    return max(0, len(lines) - 6)


def _choose_title_lines(candidates: list[str], duplicate_started: bool) -> list[str]:
    if not candidates:
        return []

    if len(candidates) == 1:
        return candidates

    if duplicate_started:
        return candidates[:2]

    if GENERIC_META_RE.search(candidates[-1]) and len(candidates) >= 2:
        title_slice = candidates[-3:-1] if len(candidates) >= 3 else candidates[:-1]
        return title_slice

    if len(candidates) >= 3 and len(candidates[-3]) <= 12:
        return candidates[-3:]
    return candidates[-2:]


def _image_group_key(image_url: str) -> str:
    name = PurePosixPath(urllib.parse.urlparse(image_url).path).stem
    return re.sub(r"_\d+$", "", name)


def _is_metaish_line(line: str) -> bool:
    return GENERIC_META_RE.search(line) is not None or METAISH_RE.search(line) is not None


def _extract_price_lines(lines: Iterable[str]) -> list[PriceLine]:
    normalized_prices = [_normalize_price_line(line) for line in lines if line]
    normalized_prices = [line for line in normalized_prices if line]
    currencies = [line for line in normalized_prices if YEN_RE.search(line)]
    off_line = next((line for line in currencies if "OFF" in line.upper() or line.startswith("- ¥")), "")

    if len(currencies) >= 2:
        original = currencies[0]
        discounted = currencies[-1] if currencies[-1] != original else None
        if discounted:
            return [
                PriceLine(
                    label="価格",
                    value=original,
                    discounted_value=discounted,
                    raw=" / ".join(normalized_prices),
                )
            ]

    if currencies:
        label = "割引" if "OFF" in off_line.upper() else "価格"
        return [PriceLine(label=label, value=currencies[0], raw=" / ".join(normalized_prices))]

    return []


def _normalize_price_line(line: str) -> str:
    cleaned = re.sub(r"^(?:price|off|or)\b[:\s]*", "", line, flags=re.IGNORECASE).strip()
    if "¥" not in cleaned:
        return cleaned

    cleaned = re.sub(r"\b(?:price|off)\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"¥\s+", "¥", cleaned)
    cleaned = re.sub(r"\s*-\s*¥\s*", "- ¥", cleaned)
    cleaned = re.sub(r"\s*⇒\s*", "⇒", cleaned)

    def replace_currency(match: re.Match[str]) -> str:
        return f"¥{_normalize_yen_amount(match.group(1))}"

    cleaned = re.sub(r"¥\s*([0-9,./]+)", replace_currency, cleaned)
    cleaned = re.sub(
        r"-\s*¥([0-9,./]+)",
        lambda match: f"- ¥{_normalize_yen_amount(match.group(1))}",
        cleaned,
    )
    return cleaned.strip(" /")


def _normalize_yen_amount(amount: str) -> str:
    normalized = amount.replace(" ", "")
    normalized = normalized.replace("/", "7")
    normalized = normalized.replace(".", ",")
    normalized = re.sub(r"[^0-9,]", "", normalized)
    normalized = re.sub(r",{2,}", ",", normalized).strip(",")

    if "," not in normalized and len(normalized) >= 4:
        normalized = f"{normalized[:-3]},{normalized[-3:]}"

    return normalized
