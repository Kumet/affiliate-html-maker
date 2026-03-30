from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field

from app.schemas.product import Product


class Section(BaseModel):
    title: Optional[str] = None
    products: List[Product] = Field(default_factory=list)
