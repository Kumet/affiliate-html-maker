from __future__ import annotations

from app.services.text_parser import parse_text


def test_parse_text_matches_sample_card_count(sample_text: str, expected_card_count: int) -> None:
    sections = parse_text(sample_text)

    assert [section.title for section in sections] == [
        "EVERYONE’S FAVORITE",
        "GREAT VALUES",
        "NEW LIFE",
        "GAS STATION SPECIAL COUPON",
    ]
    assert sum(len(section.products) for section in sections) == expected_card_count


def test_parse_text_extracts_price_badges_and_notes(sample_text: str) -> None:
    sections = parse_text(sample_text)
    beef = sections[1].products[2]

    assert beef.title == "黒毛和牛 4等級 焼肉 / 山形牛 焼肉"
    assert beef.meta_lines[:2] == ["黒毛和牛", "山形牛"]
    assert [badge.text for badge in beef.badges] == [
        "特別価格 ￥638/100g",
        "特別価格 ￥738/100g",
        "3/30～4/12",
        "取り扱い商品につきましては、各倉庫店にてご確認ください",
    ]
    assert [price.value for price in beef.price_lines] == ["￥638/100g", "￥738/100g"]


def test_parse_text_handles_coupon_intro_card(sample_text: str) -> None:
    sections = parse_text(sample_text)
    intro_card = sections[-1].products[0]

    assert intro_card.title == "ガスステーションご利用で、倉庫店で即日使えるクーポンを発行!"
    assert intro_card.price_lines == []
    assert intro_card.meta_lines == []


def test_parse_text_without_section_heading_does_not_inject_default_title() -> None:
    source_text = "\n".join(
        [
            "塩さばフィレ",
            "脂がのったノルウェー産塩さばです。",
            "特別価格 ￥238/100g",
            "3/30～4/5",
        ]
    )

    sections = parse_text(source_text)

    assert len(sections) == 1
    assert sections[0].title is None
    assert sections[0].products[0].title == "塩さばフィレ"
