from __future__ import annotations

from pathlib import Path

from app.services.email_parser import parse_email_text


def test_parse_email_text_extracts_products_and_removes_mail_noise() -> None:
    sample_path = Path(
        "/Users/kume/.codex/attachments/87a9497c-d181-45e6-9b56-ce0cd0b797b1/pasted-text.txt"
    )
    source_text = sample_path.read_text(encoding="utf-8")

    sections = parse_email_text(source_text, "costco-item-22")
    products = [product for section in sections for product in section.products]

    assert products
    assert products[0].title == "SOJAG LITO サンシェルター 3m x 3.6m ガゼボ"
    assert products[0].price_lines[0].value == "¥ 199,800"
    assert products[0].price_lines[0].discounted_value == "¥ 151,800"
    assert "ITEM #1807308" in products[0].meta_lines
    assert all("受信トレイ" not in product.title for product in products)


def test_parse_email_text_keeps_mac_section_title() -> None:
    sample_path = Path(
        "/Users/kume/.codex/attachments/87a9497c-d181-45e6-9b56-ce0cd0b797b1/pasted-text.txt"
    )
    source_text = sample_path.read_text(encoding="utf-8")

    sections = parse_email_text(source_text, "costco-item-22")

    assert any(section.title == "【Mac】デスクトップ & ハイエンド" for section in sections)
