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
