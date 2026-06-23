from __future__ import annotations

from app.services.image_mail_parser import (
    _extract_image_entries,
    _extract_price_lines,
    _parse_ocr_product_text,
)


def test_extract_image_entries_finds_product_images() -> None:
    html = """
    <img src="https://example.com/img22/gray2.jpg" alt="P&G FOCUS" />
    <img src="https://example.com/img22/s87700.jpg" alt="" />
    <img src="https://example.com/img22/s73964.jpg" alt="" />
    """

    entries = _extract_image_entries(html)

    assert len(entries) == 3
    assert entries[0].alt == "P&G FOCUS"
    assert entries[1].src.endswith("s87700.jpg")


def test_parse_ocr_product_text_extracts_title_meta_and_price() -> None:
    ocr_text = "\n".join(
        [
            "限定処方",
            "食べ物ジミ 洗浄力UP",
            "たっぷり110cmo",
            "アリエール",
            "ジェルボール",
            "アリエール",
            "ジェルボールプロ",
            "食べ物ジミ洗浄力UP",
            "部屋干し用",
            "110個入",
            "GEL BALL DETERGENT FOR INDOOR DRY",
            "ITEM# 87700",
            "～6/28",
            "PRICE",
            "OFF",
            "¥2,998",
            "- ¥740",
            "¥2,258",
        ]
    )

    product = _parse_ocr_product_text(
        ocr_text,
        "https://cds2.costcojapan.jp/cds/mail-images/upz/260622_a94g/img22/s87700.jpg",
        "costco-item-22",
    )

    assert product.title == "アリエール ジェルボールプロ"
    assert "110個入" in product.meta_lines
    assert "ITEM #87700" in product.meta_lines
    assert any(badge.text == "～6/28" for badge in product.badges)
    assert product.price_lines[0].value == "¥2,998"
    assert product.price_lines[0].discounted_value == "¥2,258"


def test_extract_price_lines_normalizes_noise_and_slash_digits() -> None:
    price_lines = _extract_price_lines(["pricE ¥26,980", "OFF", "¥ 21,/80"])

    assert len(price_lines) == 1
    assert price_lines[0].label == "価格"
    assert price_lines[0].value == "¥26,980"
    assert price_lines[0].discounted_value == "¥21,780"
