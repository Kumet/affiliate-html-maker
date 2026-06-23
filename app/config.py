from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("\"'"))


@dataclass(frozen=True)
class Settings:
    app_name: str
    affiliate_tag: str
    ocr_space_api_key: str
    template_dir: Path
    static_dir: Path
    sample_input_path: Path
    section_keywords: tuple[str, ...]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    _load_dotenv(PROJECT_ROOT / ".env")

    return Settings(
        app_name=os.getenv("APP_NAME", "Affiliate HTML Maker"),
        affiliate_tag=os.getenv("AFFILIATE_TAG", "costco-item-22"),
        ocr_space_api_key=os.getenv("OCR_SPACE_API_KEY", "helloworld"),
        template_dir=PROJECT_ROOT / "app" / "templates",
        static_dir=PROJECT_ROOT / "app" / "static",
        sample_input_path=PROJECT_ROOT / "sample" / "sample_info.txt",
        section_keywords=(
            "EVERYONE’S FAVORITE",
            "GREAT VALUES",
            "NEW LIFE",
            "GAS STATION SPECIAL COUPON",
        ),
    )
