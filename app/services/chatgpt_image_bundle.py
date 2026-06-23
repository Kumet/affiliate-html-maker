from __future__ import annotations

import io
import json
import textwrap
import urllib.parse
import urllib.request
from dataclasses import dataclass

from PIL import Image, ImageOps

from app.services.image_mail_parser import (
    _collect_product_entries,
    _extract_image_entries,
    _fetch_html,
)

CHATGPT_EXTRACTION_PROMPT = textwrap.dedent(
    """
    この PDF は Costco の販促メール画像を複数ページにまとめたものです。
    セクションごとに商品情報を抽出し、JSONのみを返してください。説明文は不要です。

    ルール:
    - セクション単位で sections 配列にまとめる
    - PDF全ページ内に見えている商品を1件も省略せず、すべて返す
    - 省略記号や「他同様」などでまとめない
    - 各商品に item_index を 1 から順に振る
    - ルートに total_products を入れ、抽出した商品総数を返す
    - ルートに expected_products も入れ、画像上で見えている想定商品数を書く
    - 各商品は title, meta_lines, badges, date_badge, original_price, discounted_price, notes を持つ
    - 値引き前価格がある場合は original_price、値引き後価格がある場合は discounted_price に入れる
    - 値引き前と値引き後の両方が読める商品は、必ず両方を入れる
    - 商品情報が不完全でも、その商品を消さずに JSON に残す
    - title が曖昧でも null にして残す
    - meta_lines, badges, notes は分かる範囲だけ入れる
    - Price, OFF, pricE などのラベルは価格値に含めない
    - OCRノイズは自然な日本語・価格として補正する
    - 日付の 6/28 や 6/28～7/5 は維持する
    - 不明な値は null または空配列にする
    - 返答は ```json で始まる Markdown のコードブロック1つだけにする
    - コードブロックの前後に説明文、補足、見出し、注意書きを一切書かない
    - JSON の外には1文字も出力しない
    - コードブロック内はそのまま貼り付け可能な有効JSONにする

    返答例:
    ```json
    {
      "total_products": 1,
      "expected_products": 1,
      "sections": [
        {
          "title": "P&G FOCUS",
          "products": [
            {
              "item_index": 1,
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
    ```
    """
).strip()


@dataclass(frozen=True)
class ChatGptImageBundle:
    filename: str
    media_type: str
    content: bytes
    product_count: int
    product_manifest_json: str


def build_chatgpt_image_bundle(source_url: str) -> ChatGptImageBundle:
    html = _fetch_html(source_url)
    entries = _extract_image_entries(html)
    product_entries = _collect_product_entries(entries)
    if not product_entries:
        raise ValueError("画像メールURLから商品関連画像を抽出できませんでした。")

    pages: list[Image.Image] = []
    manifest: list[dict[str, object]] = []
    for item_index, (section, group) in enumerate(product_entries, start=1):
        page_images = [_download_image(urllib.parse.urljoin(source_url, src)) for src in group.srcs]
        pages.append(_build_product_page(page_images))
        manifest.append(
            {
                "item_index": item_index,
                "section_title": section.title,
                "image_names": [urllib.parse.urlparse(src).path.rsplit("/", 1)[-1] for src in group.srcs],
            }
        )

    bundle = _build_pdf(pages)
    stem = _bundle_stem(source_url)
    return ChatGptImageBundle(
        filename=f"{stem}_chatgpt_bundle.pdf",
        media_type="application/pdf",
        content=bundle,
        product_count=len(product_entries),
        product_manifest_json=json.dumps(manifest, ensure_ascii=False),
    )


def _download_image(url: str) -> Image.Image:
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            image_bytes = response.read()
    except Exception as exc:
        raise ValueError(f"画像を取得できませんでした: {url} ({exc})") from exc

    image = Image.open(io.BytesIO(image_bytes))
    return ImageOps.exif_transpose(image).convert("RGB")


def _build_pdf(images: list[Image.Image]) -> bytes:
    buffer = io.BytesIO()
    first_page, *rest_pages = [_fit_pdf_page(image) for image in images]
    first_page.save(
        buffer,
        format="PDF",
        save_all=True,
        append_images=rest_pages,
        resolution=144.0,
    )
    return buffer.getvalue()


def _build_product_page(images: list[Image.Image]) -> Image.Image:
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

    return canvas


def _fit_pdf_page(image: Image.Image) -> Image.Image:
    page_width = max(image.width, 1400)
    page_height = image.height + 120
    canvas = Image.new("RGB", (page_width, page_height), "white")
    offset_x = (page_width - image.width) // 2
    offset_y = 60
    canvas.paste(image, (offset_x, offset_y))
    return canvas


def _bundle_stem(source_url: str) -> str:
    path = urllib.parse.urlparse(source_url).path.rstrip("/")
    stem = path.rsplit("/", 1)[-1] or "mail"
    return stem.rsplit(".", 1)[0]
