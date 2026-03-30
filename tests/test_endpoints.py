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
    assert 'id="download-button-slot"' in response.text
    assert "HTMLをダウンロード" in response.text


def test_download_endpoint_returns_attachment(client, sample_text: str) -> None:
    response = client.post("/download", data={"source_text": sample_text})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["content-disposition"] == (
        f'attachment; filename="affiliate_{date.today().strftime("%Y%m%d")}.html"'
    )
    assert response.text.lower().startswith("<!doctype html>")
