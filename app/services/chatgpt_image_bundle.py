from __future__ import annotations

import io
import textwrap
import urllib.parse
import urllib.request
from dataclasses import dataclass

from PIL import Image, ImageOps

from app.services.image_mail_parser import _extract_image_entries, _fetch_html

CHATGPT_EXTRACTION_PROMPT = textwrap.dedent(
    """
    この画像は Costco の販促メールを縦に連結したものです。
    セクションごとに商品情報を抽出し、JSONのみを返してください。説明文は不要です。

    ルール:
    - セクション単位で sections 配列にまとめる
    - 各商品は title, meta_lines, badges, date_badge, original_price, discounted_price, notes を持つ
    - 値引き前価格がある場合は original_price、値引き後価格がある場合は discounted_price に入れる
    - 値引き前と値引き後の両方が読める商品は、必ず両方を入れる
    - Price, OFF, pricE などのラベルは価格値に含めない
    - OCRノイズは自然な日本語・価格として補正する
    - 日付の 6/28 や 6/28～7/5 は維持する
    - 不明な値は null または空配列にする
    - 出力は JSON のみ

    返答例:
    {
      "sections": [
        {
          "title": "P&G FOCUS",
          "products": [
            {
              "title": "アリエール ジェルボールプロ",
              "meta_lines": ["部屋干し用", "110個入", "ITEM #87700"],
              "badges": [],
              "date_badge": "～6/28",
              "original_price": "¥2,998",
              "discounted_price": "¥2,258",
              "notes": []
            }
          ]
        }
      ]
    }
    """
).strip()


@dataclass(frozen=True)
class ChatGptImageBundle:
    filename: str
    media_type: str
    content: bytes
    image_count: int


def build_chatgpt_image_bundle(source_url: str) -> ChatGptImageBundle:
    html = _fetch_html(source_url)
    entries = _extract_image_entries(html)
    image_urls = [urllib.parse.urljoin(source_url, entry.src) for entry in entries]
    if not image_urls:
        raise ValueError("画像メールURLから画像を抽出できませんでした。")

    images = [_download_image(url) for url in image_urls]
    bundle = _stitch_images(images)
    stem = _bundle_stem(source_url)
    return ChatGptImageBundle(
        filename=f"{stem}_chatgpt_bundle.png",
        media_type="image/png",
        content=bundle,
        image_count=len(images),
    )


def _download_image(url: str) -> Image.Image:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            image_bytes = response.read()
    except Exception as exc:
        raise ValueError(f"画像を取得できませんでした: {url} ({exc})") from exc

    image = Image.open(io.BytesIO(image_bytes))
    return ImageOps.exif_transpose(image).convert("RGB")


def _stitch_images(images: list[Image.Image]) -> bytes:
    spacing = 20
    padding = 24
    max_width = max(image.width for image in images)
    total_height = sum(image.height for image in images) + spacing * (len(images) - 1) + padding * 2
    canvas = Image.new("RGB", (max_width + padding * 2, total_height), "white")

    cursor_y = padding
    for image in images:
        offset_x = padding + (max_width - image.width) // 2
        canvas.paste(image, (offset_x, cursor_y))
        cursor_y += image.height + spacing

    buffer = io.BytesIO()
    canvas.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def _bundle_stem(source_url: str) -> str:
    path = urllib.parse.urlparse(source_url).path.rstrip("/")
    stem = path.rsplit("/", 1)[-1] or "mail"
    return stem.rsplit(".", 1)[0]
