from __future__ import annotations

import json

from PIL import Image

from app.schemas.section import Section
from app.services.chatgpt_image_bundle import ChatGptImageBundle, build_chatgpt_image_bundle
from app.services.image_mail_parser import ProductImageGroup


def test_build_chatgpt_image_bundle_uses_product_groups(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.services.chatgpt_image_bundle._fetch_html",
        lambda _url: "<html></html>",
    )
    monkeypatch.setattr(
        "app.services.chatgpt_image_bundle._extract_image_entries",
        lambda _html: [],
    )
    monkeypatch.setattr(
        "app.services.chatgpt_image_bundle._collect_product_entries",
        lambda _entries: [
            (
                Section(title="P&G FOCUS"),
                ProductImageGroup(srcs=("https://example.com/img22/s87700.jpg",), alt=""),
            ),
            (
                Section(title="P&G FOCUS"),
                ProductImageGroup(
                    srcs=(
                        "https://example.com/img22/s73964.jpg",
                        "https://example.com/img22/s73964_1.jpg",
                    ),
                    alt="",
                ),
            ),
        ],
    )
    monkeypatch.setattr(
        "app.services.chatgpt_image_bundle._download_image",
        lambda _url: Image.new("RGB", (200, 200), "white"),
    )

    bundle = build_chatgpt_image_bundle("https://example.com/mail.html")

    assert isinstance(bundle, ChatGptImageBundle)
    assert bundle.product_count == 2
    manifest = json.loads(bundle.product_manifest_json)
    assert manifest[0]["image_names"] == ["s87700.jpg"]
    assert manifest[1]["image_names"] == ["s73964.jpg", "s73964_1.jpg"]
