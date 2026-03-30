from __future__ import annotations

from app.services.html_builder import build_download_html, build_preview_html
from app.services.text_parser import parse_text


def test_preview_html_contains_expected_structure(
    sample_text: str, expected_card_count: int
) -> None:
    html = build_preview_html(parse_text(sample_text))

    assert "<style>" in html
    assert html.count('class="csc-card"') == expected_card_count
    assert "<h2>EVERYONE’S FAVORITE</h2>" in html
    assert "tag=costco-item-22" in html
    assert "ガスステーションご利用で、倉庫店で即日使えるクーポンを発行!" in html


def test_download_html_is_standalone_document(sample_text: str) -> None:
    html = build_download_html(parse_text(sample_text))

    assert html.lower().startswith("<!doctype html>")
    assert "<html lang=\"ja\">" in html
    assert "<body>" in html
    assert "generated " in html


def test_preview_html_without_section_heading_has_no_fallback_h2() -> None:
    source_text = "\n".join(
        [
            "塩さばフィレ",
            "脂がのったノルウェー産塩さばです。",
            "特別価格 ￥238/100g",
            "3/30～4/5",
        ]
    )

    html = build_preview_html(parse_text(source_text))

    assert "<h2>" not in html
    assert "塩さばフィレ" in html
