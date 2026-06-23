from __future__ import annotations

from app.services.chatgpt_json_parser import parse_chatgpt_json


def test_parse_chatgpt_json_builds_sections() -> None:
    payload = """
    {
      "sections": [
        {
          "title": "P&G FOCUS",
          "products": [
            {
              "title": "アリエール ジェルボールプロ",
              "meta_lines": ["部屋干し用", "110個入"],
              "badges": ["特価"],
              "date_badge": "～6/28",
              "original_price": "¥2,998",
              "discounted_price": "¥2,258",
              "notes": ["ITEM #87700"]
            }
          ]
        }
      ]
    }
    """

    sections = parse_chatgpt_json(payload, "costco-item-22")

    assert len(sections) == 1
    assert sections[0].title == "P&G FOCUS"
    product = sections[0].products[0]
    assert product.title == "アリエール ジェルボールプロ"
    assert "ITEM #87700" in product.meta_lines
    assert product.price_lines[0].discounted_value == "¥2,258"


def test_parse_chatgpt_json_accepts_sale_price_aliases() -> None:
    payload = """
    {
      "sections": [
        {
          "title": "P&G FOCUS",
          "products": [
            {
              "title": "アリエール ジェルボールプロ",
              "original_price": "¥2,998",
              "sale_price": "¥2,258"
            }
          ]
        }
      ]
    }
    """

    sections = parse_chatgpt_json(payload, "costco-item-22")

    price_line = sections[0].products[0].price_lines[0]
    assert price_line.value == "¥2,998"
    assert price_line.discounted_value == "¥2,258"
