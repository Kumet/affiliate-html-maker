from __future__ import annotations

from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import get_settings
from app.schemas.section import Section

CARD_STYLES = """
.csc-wrap{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,"Hiragino Kaku Gothic ProN","Hiragino Sans","Noto Sans JP","Yu Gothic",Meiryo,sans-serif;line-height:1.65;}
.csc-section{margin:16px 0 10px;}
.csc-section h2{font-size:16px;margin:0 0 10px;padding:8px 10px;background:#f3f7f5;border-left:5px solid #0b5;border-radius:10px;}
.csc-grid{display:grid;grid-template-columns:1fr;gap:10px;}
@media(min-width:900px){.csc-grid{grid-template-columns:1fr 1fr;}}
.csc-card{background:#fff;border:1px solid #e8eeea;border-radius:14px;padding:12px 12px;box-shadow:0 6px 18px rgba(0,0,0,.06);overflow:hidden;}
.csc-top{display:flex;gap:10px;align-items:flex-start;justify-content:space-between;}
.csc-title{font-size:15px;font-weight:800;margin:0;}
.csc-title a{text-decoration:none;color:#133;}
.csc-title a:hover{text-decoration:underline;}
.csc-badges{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end;}
.csc-badge{font-size:11px;padding:2px 8px;border-radius:999px;background:#eef7f1;color:#0a6;border:1px solid #d8efe1;font-weight:700;}
.csc-badge.gray{background:#f3f4f6;color:#555;border-color:#e5e7eb;}
.csc-meta{margin:8px 0 0;padding:0;list-style:none;}
.csc-meta li{font-size:13px;padding:3px 0;color:#233;display:flex;gap:8px;align-items:flex-start;word-break:break-word;}
.csc-meta li::before{content:"";display:block;width:0;height:0;flex:0 0 0;}
.csc-price{margin-top:10px;padding:10px;border-radius:12px;background:#f8faf9;border:1px dashed #d8e6de;}
.csc-price .line{font-size:14px;margin:0;display:flex;gap:8px;flex-wrap:wrap;align-items:baseline;}
.csc-price .label{font-weight:800;color:#155;}
.csc-red{color:#d01616;font-weight:900;}
.csc-black{color:#111;font-weight:800;}
.csc-divider{height:1px;background:#eef1ef;margin:14px 0;}
""".strip()


def _template_environment() -> Environment:
    settings = get_settings()
    return Environment(
        loader=FileSystemLoader(str(settings.template_dir)),
        autoescape=select_autoescape(("html", "xml")),
        trim_blocks=True,
        lstrip_blocks=True,
    )


def render_template(template_name: str, **context: object) -> str:
    environment = _template_environment()
    template = environment.get_template(template_name)
    return template.render(**context)


def build_preview_html(sections: list[Section]) -> str:
    return render_template("partials/preview.html", sections=sections, card_styles=CARD_STYLES)


def build_download_html(sections: list[Section], title: str = "affiliate") -> str:
    fragment = build_preview_html(sections)
    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="ja">',
            "<head>",
            '  <meta charset="utf-8">',
            '  <meta name="viewport" content="width=device-width, initial-scale=1">',
            f"  <title>{title}</title>",
            "</head>",
            "<body>",
            fragment,
            f"<!-- generated {datetime.now().isoformat(timespec='seconds')} -->",
            "</body>",
            "</html>",
        ]
    )


def load_initial_text() -> str:
    sample_path = Path(get_settings().sample_input_path)
    if not sample_path.exists():
        return ""
    return sample_path.read_text(encoding="utf-8")
