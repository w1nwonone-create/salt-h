"""Critic 검증 Tool — check_sample_size · check_missing · check_period_bias · verify_numbers."""
from __future__ import annotations

import re

import config


def _c(status: str, name: str, message: str, metric: str = "", candidate: str = "") -> dict:
    return {"status": status, "check": name, "metric": metric, "candidate": candidate, "message": message}


def check_sample_size(results: dict, cands: dict) -> list[dict]:
    out = []
    s = results.get("season_stability")
    if s:
        for cid, r in s["candidates"].items():
            tag = cands[cid]["tag"]
            card = r["card"]
            if card["peak_months_n"] < 2 or card["off_months_n"] < 2:
                out.append(_c("warn", "sample_size", f"{tag}: 성수기 {card['peak_months_n']}개월·비수기 {card['off_months_n']}개월만 "
                              "비교 가능해 참고용입니다.", "season", cid))
            if card.get("total_cnt", 0) < config.MIN_USE_CNT * 12:
                out.append(_c("warn", "sample_size", f"{tag}: 이 격자의 업종 이용 건수가 매우 적어 참고용입니다.", "season", cid))
            if r["masked_months"]:
                out.append(_c("info", "min_aggregation", f"{tag}: 이용 건수 {config.MIN_USE_CNT}건 미만인 "
                              f"{len(r['masked_months'])}개월은 최소 집계 기준에 따라 제외했습니다.", "season", cid))
            pos = r.get("pos")
            if pos and pos.get("suppressed"):
                out.append(_c("info", "min_aggregation", f"{tag}: 외식업 포스 표본 점포가 평균 {pos['store_cnt_avg']:.1f}곳으로 "
                              f"기준({config.MIN_POS_STORES}곳) 미만이라 포스 매출은 표시하지 않습니다.", "season", cid))
    w = results.get("weather_sensitivity")
    if w:
        for cid, r in w["candidates"].items():
            tag = cands[cid]["tag"]
            for src, label in (("visit_pop", "방문인구"), ("bus", "버스 이용")):
                x = r.get(src)
                if not x:
                    out.append(_c("warn", "sample_size", f"{tag}: {label} 데이터가 없어 날씨 비교에서 제외했습니다.", "weather", cid))
                elif not x["enough"]:
                    out.append(_c("warn", "sample_size", f"{tag}: {label} 비교 일수(우천 {x['rain_days']}일·비우천 {x['dry_days']}일)가 "
                                  f"기준({config.MIN_DAYS_PER_GROUP}일) 미만이라 참고용입니다.", "weather", cid))
                else:
                    out.append(_c("ok", "sample_size", f"{tag}: {label} 우천 {x['rain_days']}일·비우천 {x['dry_days']}일 비교 — 충분합니다.",
                                  "weather", cid))
    return out


def check_missing(results: dict, cands: dict) -> list[dict]:
    out = []
    s = results.get("season_stability")
    if s:
        for cid, r in s["candidates"].items():
            tag = cands[cid]["tag"]
            miss = [m for m in r["card"]["missing_months"] if m not in r["masked_months"]]
            if miss:
                out.append(_c("warn", "missing", f"{tag}: 카드 데이터 {len(miss)}개월 결측({', '.join(miss[:4])}) — 보정하지 않고 제외했습니다.",
                              "season", cid))
            pos = r.get("pos")
            if pos and not pos.get("suppressed") and pos["missing_months"]:
                out.append(_c("warn", "missing", f"{tag}: 외식업 포스 {len(pos['missing_months'])}개월 결측"
                              f"({', '.join(pos['missing_months'][:4])}) — 보정하지 않고 제외했습니다.", "season", cid))
    w = results.get("weather_sensitivity")
    if w:
        for cid, r in w["candidates"].items():
            tag = cands[cid]["tag"]
            vp = r.get("visit_pop") or {}
            if vp.get("missing_days"):
                out.append(_c("warn", "missing", f"{tag}: 방문인구 {vp['missing_days']}일 결측 — 해당 일은 비교에서 제외했습니다.", "weather", cid))
            rm = max(vp.get("rain_missing_days", 0), (r.get("bus") or {}).get("rain_missing_days", 0))
            if rm:
                out.append(_c("warn", "missing", f"{tag}: 관측소 강수량 {rm}일 결측 — 해당 일은 비교에서 제외했습니다.", "weather", cid))
    return out


def check_period_bias(results: dict, cands: dict, matched: bool) -> tuple[list[dict], bool]:
    """연도 효과 점검. 연도별 성수기 규모가 기준 이상 다르면 동일 연도(시즌연도) 재분석 요청."""
    out, need = [], False
    s = results.get("season_stability")
    if not s:
        return out, need
    for cid, r in s["candidates"].items():
        tag = cands[cid]["tag"]
        py = r["card"]["peak_by_year"]
        if len(py) >= 2:
            vals = list(py.values())
            change = max(vals) / min(vals) - 1 if min(vals) else 0
            if change > config.YEAR_EFFECT_THRESHOLD:
                if matched:
                    out.append(_c("ok", "period_bias", f"{tag}: 연도별 성수기 규모 차이({change:.0%})가 있어 같은 시즌연도"
                                  f"(여름과 그 직후 겨울)끼리 비교했습니다.", "season", cid))
                else:
                    need = True
                    out.append(_c("warn", "period_bias", f"{tag}: 연도별 성수기 규모가 {change:.0%} 달라, 서로 다른 연도가 섞인 비교는 "
                                  "연도 효과가 섞일 수 있습니다 → 같은 시즌연도끼리 다시 비교합니다.", "season", cid))
        ry = r["card"]["ratio_by_season_year"]
        if len(ry) >= 2:
            v = list(ry.values())
            if max(v) - min(v) > 0.10:
                out.append(_c("warn", "period_bias", f"{tag}: 해마다 시즌 안정성 차이가 10%p 이상입니다 — 특정 시기의 영향일 수 있습니다.",
                              "season", cid))
    if matched and s.get("season_years_used") is not None and not s["season_years_used"]:
        out.append(_c("fail", "period_bias", "같은 시즌연도의 성수기·비수기가 모두 포함된 기간이 없습니다.", "season"))
    return out, need


def check_grid_boundary(results: dict, cands: dict, nav_cands: list[dict]) -> list[dict]:
    out = []
    s = results.get("season_stability")
    for c in nav_cands:
        if c["near_boundary"]:
            out.append(_c("info", "grid_boundary", f"{c['tag']}: 후보지가 격자 경계에서 {c['edge_distance_m']:.0f}m 거리에 있어 "
                          "인접 격자(3×3)의 값도 함께 표시합니다.", "season", c["id"]))
        if s and c["id"] in s["candidates"]:
            r = s["candidates"][c["id"]]
            a, b = r["card"]["ratio"], r["card_3x3"]["ratio"]
            if a is not None and b is not None and abs(a - b) > 0.10:
                out.append(_c("warn", "grid_boundary", f"{c['tag']}: 후보지 격자({a:.0%})와 주변 3×3 격자({b:.0%})의 시즌 안정성이 "
                              "10%p 이상 달라, 바로 옆 블록과 상권 성격이 다를 수 있습니다.", "season", c["id"]))
    return out


# ---- 수치 대조 -------------------------------------------------------------------
NUM_RE = re.compile(r"(?<![A-Za-z_])\d[\d,]*(?:\.\d+)?")


def numbers_in(text: str) -> list[str]:
    return [n.replace(",", "") for n in NUM_RE.findall(text)]


def verify_numbers(text: str, allowed: set[str]) -> list[str]:
    """text 의 모든 수치가 코드 산출값(allowed)에 있는지 대조. 대조되지 않는 수치 목록을 반환."""
    bad = []
    for n in numbers_in(text):
        norm = n.rstrip("0").rstrip(".") if "." in n else n
        if n not in allowed and norm not in allowed:
            bad.append(n)
    return bad
