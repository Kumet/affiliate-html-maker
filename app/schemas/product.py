from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class Badge(BaseModel):
    text: str
    variant: str = "default"


class PriceLine(BaseModel):
    label: str = "価格"
    value: str
    discounted_value: Optional[str] = None
    raw: str


class Product(BaseModel):
    title: str
    amazon_url: str
    search_keyword: str
    meta_lines: List[str] = Field(default_factory=list)
    badges: List[Badge] = Field(default_factory=list)
    price_lines: List[PriceLine] = Field(default_factory=list)
    raw_lines: List[str] = Field(default_factory=list)
