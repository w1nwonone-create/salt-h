"""make_chart — 리포트용 SVG 차트(외부 라이브러리·인터넷 없이 렌더링, 인쇄/PDF 선명).

글자는 브라우저 글꼴을 쓰므로 한글이 깨지지 않습니다. 색은 후보지 A·B·C 고정.
"""
from __future__ import annotations

from html import escape

COLORS = ["#2563eb", "#ea580c", "#059669"]  # A 파랑 · B 주황 · C 초록
INK, MUTED, GRID = "#1f2937", "#6b7280", "#e5e7eb"
FONT = "font-family=\"'Pretendard','Malgun Gothic','Apple SD Gothic Neo','Noto Sans KR',sans-serif\""


def _svg(w: int, h: int, body: str, title: str) -> str:
    return (f'<svg viewBox="0 0 {w} {h}" width="100%" role="img" aria-label="{escape(title)}" '
            f'xmlns="http://www.w3.org/2000/svg" {FONT}>{body}</svg>')


def _nice_max(v: float) -> float:
    if v <= 0:
        return 1
    import math

    e = 10 ** math.floor(math.log10(v))
    for m in (1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * e >= v:
            return m * e
    return 10 * e


def legend(names: list[str], x: int, y: int) -> str:
    out, cx = [], x
    for i, n in enumerate(names):
        out.append(f'<rect x="{cx}" y="{y - 9}" width="12" height="12" rx="2" fill="{COLORS[i % 3]}"/>'
                   f'<text x="{cx + 17}" y="{y + 1}" font-size="12" fill="{INK}">{escape(n)}</text>')
        cx += 30 + 12 * len(n)
    return "".join(out)


def grouped_bars(categories: list[str], series: list[tuple[str, list[float | None]]], title: str,
                 fmt=lambda v: f"{v:.0%}", vmax: float | None = None, note: str = "") -> str:
    """categories × series 묶음 막대. None 은 '–' 로 표시."""
    w, h, left, right, top, bottom = 640, 300, 48, 16, 40, 56
    pw, ph = w - left - right, h - top - bottom
    vals = [v for _, s in series for v in s if v is not None]
    vmax = vmax or _nice_max(max(vals) if vals else 1)
    body = [legend([n for n, _ in series], left, 20)]
    for i in range(5):
        y = top + ph - ph * i / 4
        body.append(f'<line x1="{left}" x2="{w - right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>'
                    f'<text x="{left - 6}" y="{y + 4:.1f}" font-size="11" fill="{MUTED}" text-anchor="end">{escape(fmt(vmax * i / 4))}</text>')
    gw = pw / max(1, len(categories))
    bw = min(34, gw * 0.75 / max(1, len(series)))
    for ci, cat in enumerate(categories):
        gx = left + gw * ci + (gw - bw * len(series)) / 2
        for si, (_, s) in enumerate(series):
            v = s[ci]
            x = gx + si * bw
            if v is None:
                body.append(f'<text x="{x + bw / 2:.1f}" y="{top + ph - 4}" font-size="11" fill="{MUTED}" text-anchor="middle">–</text>')
                continue
            bh = max(0.0, ph * min(v, vmax) / vmax)
            body.append(f'<rect x="{x:.1f}" y="{top + ph - bh:.1f}" width="{bw - 3:.1f}" height="{bh:.1f}" rx="2" fill="{COLORS[si % 3]}"/>'
                        f'<text x="{x + (bw - 3) / 2:.1f}" y="{top + ph - bh - 4:.1f}" font-size="11" fill="{INK}" text-anchor="middle">{escape(fmt(v))}</text>')
        body.append(f'<text x="{left + gw * ci + gw / 2:.1f}" y="{h - bottom + 18}" font-size="12" fill="{INK}" text-anchor="middle">{escape(cat)}</text>')
    if note:
        body.append(f'<text x="{left}" y="{h - 8}" font-size="11" fill="{MUTED}">{escape(note)}</text>')
    return _svg(w, h, "".join(body), title)


def line_chart(xlabels: list[str], series: list[tuple[str, list[float | None]]], title: str,
               fmt=lambda v: f"{v:,.0f}", shade: list[int] | None = None, shade2: list[int] | None = None,
               note: str = "") -> str:
    """월별 추이. shade(성수기)/shade2(비수기) 는 강조할 x 인덱스."""
    w, h, left, right, top, bottom = 640, 300, 64, 16, 40, 60
    pw, ph = w - left - right, h - top - bottom
    vals = [v for _, s in series for v in s if v is not None]
    vmax = _nice_max(max(vals) if vals else 1)
    n = len(xlabels)
    step = pw / max(1, n - 1)
    body = [legend([s for s, _ in series], left, 20)]
    for idxs, color in ((shade or [], "#fef3c7"), (shade2 or [], "#e0f2fe")):
        for i in idxs:
            body.append(f'<rect x="{left + step * (i - .5):.1f}" y="{top}" width="{step:.1f}" height="{ph}" fill="{color}"/>')
    for i in range(5):
        y = top + ph - ph * i / 4
        body.append(f'<line x1="{left}" x2="{w - right}" y1="{y:.1f}" y2="{y:.1f}" stroke="{GRID}"/>'
                    f'<text x="{left - 6}" y="{y + 4:.1f}" font-size="11" fill="{MUTED}" text-anchor="end">{escape(fmt(vmax * i / 4))}</text>')
    for si, (_, s) in enumerate(series):
        pts, segs = [], []
        for i, v in enumerate(s):
            if v is None:
                if pts:
                    segs.append(pts)
                pts = []
                continue
            pts.append(f"{left + step * i:.1f},{top + ph - ph * v / vmax:.1f}")
        if pts:
            segs.append(pts)
        for seg in segs:
            body.append(f'<polyline points="{" ".join(seg)}" fill="none" stroke="{COLORS[si % 3]}" stroke-width="2.2"/>')
        for i, v in enumerate(s):
            if v is not None:
                body.append(f'<circle cx="{left + step * i:.1f}" cy="{top + ph - ph * v / vmax:.1f}" r="2.6" fill="{COLORS[si % 3]}"/>')
    every = max(1, n // 8)
    for i, lab in enumerate(xlabels):
        if i % every == 0 or i == n - 1:
            body.append(f'<text x="{left + step * i:.1f}" y="{h - bottom + 16}" font-size="11" fill="{MUTED}" text-anchor="middle">{escape(lab)}</text>')
    if note:
        body.append(f'<text x="{left}" y="{h - 10}" font-size="11" fill="{MUTED}">{escape(note)}</text>')
    return _svg(w, h, "".join(body), title)
