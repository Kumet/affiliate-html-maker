from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(scope="session")
def sample_text() -> str:
    return (PROJECT_ROOT / "sample" / "sample_info.txt").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def sample_html() -> str:
    return (PROJECT_ROOT / "sample" / "costco_coupon_from_text_same_structure.html").read_text(
        encoding="utf-8"
    )


@pytest.fixture(scope="session")
def expected_card_count(sample_html: str) -> int:
    return sample_html.count('class="csc-card"')
