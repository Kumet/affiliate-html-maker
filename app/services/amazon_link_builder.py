from __future__ import annotations

from urllib.parse import quote_plus

AMAZON_SEARCH_URL = "https://www.amazon.co.jp/s"


def build_url(name: str, tag: str) -> str:
    keyword = quote_plus(name.strip())
    return f"{AMAZON_SEARCH_URL}?k={keyword}&tag={tag}"
