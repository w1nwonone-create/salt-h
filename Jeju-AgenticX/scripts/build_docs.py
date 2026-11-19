"""docs/결과설명자료.md → docs/결과설명자료.html (PDF 는 브라우저 인쇄 또는 Playwright 로 변환)."""
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]
src = ROOT / "docs" / "결과설명자료.md"
body = markdown.markdown(src.read_text(encoding="utf-8"), extensions=["tables", "fenced_code"])
css = """
@page { size: A4; margin: 14mm 14mm 16mm; }
body { font-family: 'Pretendard','Malgun Gothic','Noto Sans KR',sans-serif; color:#1f2937; font-size:11.5px; line-height:1.6; }
h1 { font-size:22px; color:#0f766e; margin:0 0 4px; } h2 { font-size:16px; border-bottom:2px solid #0f766e; padding-bottom:3px; margin-top:20px; break-after:avoid; }
h3 { font-size:13px; margin:12px 0 4px; } table { border-collapse:collapse; width:100%; margin:6px 0; font-size:10.5px; }
th, td { border:1px solid #e5e7eb; padding:4px 6px; text-align:left; } th { background:#f1f5f9; }
pre { background:#f8fafc; border:1px solid #e5e7eb; padding:8px; font-size:10px; } blockquote { margin:6px 0; padding:4px 12px; background:#fffbeb; border-left:4px solid #f59e0b; }
img { max-width:100%; border:1px solid #e5e7eb; display:block; margin:8px auto; break-inside:avoid; } p img { max-height:235mm; }
hr { border:0; border-top:1px solid #e5e7eb; }
"""
html = f'<!doctype html><html lang="ko"><head><meta charset="utf-8"><title>Jeju-AgenticX 결과 설명자료</title><style>{css}</style></head><body>{body}</body></html>'
out = ROOT / "docs" / "결과설명자료.html"
out.write_text(html, encoding="utf-8")
print("→", out)
