from __future__ import annotations

from datetime import date

import pytest


@pytest.fixture(scope="module")
def client():
    pytest.importorskip("fastapi")

    from fastapi.testclient import TestClient

    from app.main import app

    return TestClient(app)


def test_preview_endpoint_returns_fragment(client, sample_text: str, expected_card_count: int) -> None:
    response = client.post("/preview", data={"source_text": sample_text})

    assert response.status_code == 200
    assert response.text.count('class="csc-card"') == expected_card_count
    assert "HTMLをダウンロード" not in response.text


def test_index_page_contains_both_input_tabs(client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "商品テキスト" in response.text
    assert "メール内容" in response.text
    assert "画像メールURL" in response.text
    assert 'id="source_text"' in response.text
    assert 'id="mail_source_text"' in response.text
    assert 'id="image_url_source"' in response.text


def test_download_endpoint_returns_attachment(client, sample_text: str) -> None:
    response = client.post("/download", data={"source_text": sample_text})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="affiliate_{date.today().strftime("%Y%m%d")}.html"'
    )
    assert response.text.lower().startswith("<!doctype html>")


def test_chatgpt_json_preview_endpoint_returns_fragment(client) -> None:
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
              "price": "¥2,998",
              "discounted_price": "¥2,258",
              "notes": ["ITEM #87700"]
            }
          ]
        }
      ]
    }
    """

    response = client.post("/preview", data={"source_text": payload, "parse_mode": "chatgpt_json"})

    assert response.status_code == 200
    assert "アリエール ジェルボールプロ" in response.text
    assert "¥2,258" in response.text


def test_chatgpt_json_preview_warns_when_product_count_is_low(client, monkeypatch) -> None:
    payload = """
    {
      "total_products": 1,
      "sections": [
        {
          "title": "P&G FOCUS",
          "products": [
            {
              "item_index": 1,
              "title": "アリエール ジェルボールプロ",
              "original_price": "¥2,998",
              "discounted_price": "¥2,258"
            }
          ]
        }
      ]
    }
    """

    monkeypatch.setattr("app.routers.htmx.estimate_image_mail_product_count", lambda _url: 3)
    response = client.post(
        "/preview",
        data={
            "source_text": payload,
            "parse_mode": "chatgpt_json",
            "original_image_url": "https://example.com/mail.html",
        },
    )

    assert response.status_code == 200
    assert "商品数が不足している可能性があります" in response.text
    assert "想定商品数は 3 件" in response.text


def test_chatgpt_json_download_endpoint_returns_attachment(client) -> None:
    payload = """
    {
      "sections": [
        {
          "title": "P&G FOCUS",
          "products": [
            {
              "title": "アリエール ジェルボールプロ",
              "price": "¥2,998"
            }
          ]
        }
      ]
    }
    """

    response = client.post("/download", data={"source_text": payload, "parse_mode": "chatgpt_json"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text.lower().startswith("<!doctype html>")


def test_chatgpt_pdf_download_endpoint_returns_attachment(client, monkeypatch) -> None:
    from app.services.chatgpt_image_bundle import ChatGptImageBundle

    monkeypatch.setattr(
        "app.routers.download.build_chatgpt_image_bundle",
        lambda _url: ChatGptImageBundle(
            filename="sample_chatgpt_bundle.pdf",
            media_type="application/pdf",
            content=b"%PDF-1.4\n%",
            product_count=3,
            product_manifest_json='[{"item_index":1,"image_names":["s1.jpg"]}]',
        ),
    )

    response = client.post("/download-chatgpt-image", data={"source_text": "https://example.com/mail.html"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/pdf")
    assert response.headers["content-disposition"] == 'attachment; filename="sample_chatgpt_bundle.pdf"'
    assert response.headers["x-expected-products"] == "3"


def test_email_preview_endpoint_returns_fragment(client) -> None:
    source_text = (
        "SOJAG LITO サンシェルター 3m x 3.6m ガゼボ\trècolte スライドラックトースター\n"
        "HOT BUY ONLINE ONLY\n"
        "SOJAG LITO サンシェルター 3m x 3.6m ガゼボ\n"
        "Sun Shelter 10x12' Gazebo\n"
        "ITEM #1807308\tHOT BUY\n"
        "rècolte スライドラックトースター 各色\n"
        "Slide Rack Toaster RSR-2\n"
        "ITEM #71468\n"
        "Price\t¥ 199,800\n"
        "Off\t¥ 48,000\n"
        "¥ 151,800\n"
        "Shop Now >\n"
        "Price\t¥ 9,998\n"
        "Off\t¥ 2,000\n"
        "¥ 7,998\n"
        "Shop Now >\n"
    )

    response = client.post("/preview", data={"source_text": source_text, "parse_mode": "email"})

    assert response.status_code == 200
    assert "SOJAG LITO サンシェルター 3m x 3.6m ガゼボ" in response.text
    assert "rècolte スライドラックトースター 各色" in response.text
    assert "¥ 151,800" in response.text


def test_email_download_endpoint_returns_attachment(client) -> None:
    source_text = (
        "SOJAG LITO サンシェルター 3m x 3.6m ガゼボ\trècolte スライドラックトースター\n"
        "HOT BUY ONLINE ONLY\n"
        "SOJAG LITO サンシェルター 3m x 3.6m ガゼボ\n"
        "Sun Shelter 10x12' Gazebo\n"
        "ITEM #1807308\tHOT BUY\n"
        "rècolte スライドラックトースター 各色\n"
        "Slide Rack Toaster RSR-2\n"
        "ITEM #71468\n"
        "Price\t¥ 199,800\n"
        "Off\t¥ 48,000\n"
        "¥ 151,800\n"
        "Shop Now >\n"
        "Price\t¥ 9,998\n"
        "Off\t¥ 2,000\n"
        "¥ 7,998\n"
        "Shop Now >\n"
    )

    response = client.post("/download", data={"source_text": source_text, "parse_mode": "email"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.text.lower().startswith("<!doctype html>")
