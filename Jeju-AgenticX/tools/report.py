"""render_report · export_pdf — 상담용 리포트(HTML/PDF)."""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

import config

_env = Environment(loader=FileSystemLoader(str(config.REPORT_TEMPLATE_DIR)),
                   autoescape=select_autoescape(["html", "j2"]))


def render_report(report: dict) -> str:
    return _env.get_template("report.html.j2").render(r=report)


def export_pdf(html_path: Path | str, pdf_path: Path | str | None = None) -> Path | None:
    """HTML → PDF. Playwright(Chromium)가 설치된 경우에만 동작하며, 없으면 None.
    (센터 PC 에서는 리포트 화면의 'PDF로 저장' 버튼 = 브라우저 인쇄 → PDF 저장을 사용합니다.)"""
    html_path = Path(html_path)
    pdf_path = Path(pdf_path or html_path.with_suffix(".pdf"))
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page()
            page.goto(html_path.resolve().as_uri())
            page.pdf(path=str(pdf_path), format="A4", print_background=True, prefer_css_page_size=True)
            b.close()
        return pdf_path
    except Exception:  # noqa: BLE001
        return None
