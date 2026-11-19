"""④ Critic — 부정확하거나 과장된 결론이 사용자에게 전달되지 않도록 점검합니다.

Tools: check_sample_size, check_missing, check_period_bias (+ 격자 경계 점검)
판정: pass | reanalyze(재분석 요청, 최대 2회) | fail(전달할 결과 없음)
"""
from __future__ import annotations

import config
from agent.context import RunContext
from tools import checks

STATIC_LIMITS = {
    "always": [
        "카드 데이터는 업종·지역 단위 집계이므로 개별 점포의 매출을 예측하지 않으며, 후보지 상권의 경향과 변동 폭을 보여줍니다.",
        "임대료, 경쟁 점포 현황, 주차·가시성 등 입지 판단의 다른 요소는 분석에 포함되지 않습니다.",
        "분석 결과는 상관관계에 기반한 경향이며, 인과관계를 의미하지 않습니다.",
    ],
    "season": [
        "카드 데이터는 단일 카드사(비씨카드) 기준이며, 외식업 포스 데이터의 점포 수는 전체 점포가 아닌 표본 점포 수입니다.",
        "500m 격자는 실제 상권의 경계와 다를 수 있습니다.",
    ],
    "weekday": ["요일·시간대 카드 데이터는 법정동 단위로 제공되어, 같은 법정동 안의 두 후보지는 요일·시간대 패턴을 구분하지 못합니다."],
    "tourism": ["관광 의존도는 법정동 단위 요일별 카드 데이터의 관광구분(개별·단체관광객·도민)으로 산출합니다."],
    "weather": [
        "카드·외식업 매출은 월 단위로 제공되어 특정 날짜의 날씨와 직접 연결할 수 없습니다. 날씨 민감도는 일 단위 방문 인구·버스 이용의 "
        "변화이며, 소비의 변화가 아닙니다.",
        "버스 승하차는 유동인구의 대리 지표로, 실제 방문객 수와 차이가 있을 수 있습니다.",
    ],
}


def critique(ctx: RunContext, plan: dict, nav: dict, analysis: dict, round_: int) -> dict:
    results = analysis["results"]
    cmap = {c["id"]: c for c in nav["candidates"]}
    matched = bool(analysis["options"].get("matched_years"))
    found = []

    for t, run in analysis["runs"].items():
        if not run.get("ok"):
            found.append({"status": "fail", "check": "execution", "metric": t, "candidate": "",
                          "message": f"{t} 분석이 실행되지 못했습니다: {str(run.get('error', ''))[:160]}"})

    found += checks.check_sample_size(results, cmap)
    found += checks.check_missing(results, cmap)
    bias, need_matched = checks.check_period_bias(results, cmap, matched)
    found += bias
    found += checks.check_grid_boundary(results, cmap, nav["candidates"])

    for grp in nav.get("same_bjd", []):
        found.append({"status": "warn", "check": "unit", "metric": "weekday", "candidate": "",
                      "message": f"{'·'.join(grp)} 후보지가 같은 법정동이라 요일·시간대·관광 의존도는 구분되지 않습니다."})
    for grp in nav.get("same_emd", []):
        if "weather" in nav["metrics"]:
            found.append({"status": "warn", "check": "unit", "metric": "weather", "candidate": "",
                          "message": f"{'·'.join(grp)} 후보지가 같은 행정동이라 방문인구 기준 날씨 민감도는 같습니다(버스 지표로 보완)."})
    for grp in nav.get("same_grid", []):
        found.append({"status": "warn", "check": "unit", "metric": "season", "candidate": "",
                      "message": f"{'·'.join(grp)} 후보지가 같은 500m 격자에 있어 격자 지표는 구분되지 않습니다."})
    if "weather" in nav["metrics"]:
        for c in nav["candidates"]:
            if c["station"]["distance_m"] > 10_000:
                found.append({"status": "warn", "check": "unit", "metric": "weather", "candidate": c["id"],
                              "message": f"{c['tag']}: 가장 가까운 기상 관측소({c['station']['name']})가 "
                                         f"{c['station']['distance_m'] / 1000:.0f}km 떨어져 있어, 후보지의 국지적인 비는 다를 수 있습니다."})
    for w in nav.get("warnings", []):
        found.append({"status": "info", "check": "navigator", "metric": "", "candidate": "", "message": w})

    # 신뢰도 표시(누구나 이해할 수 있는 표현)
    reliability = {}
    w = results.get("weather_sensitivity")
    if w:
        for cid, r in w["candidates"].items():
            vp = r.get("visit_pop") or r.get("bus")
            reliability.setdefault("weather", {})[cid] = (
                "비교한 날이 충분해 믿을 만한 결과입니다" if vp and vp["enough"] else "비교한 날이 적어 참고용으로만 봐 주세요")
    s = results.get("season_stability")
    if s:
        for cid, r in s["candidates"].items():
            ok = r["card"]["peak_months_n"] >= 2 and r["card"]["off_months_n"] >= 2
            reliability.setdefault("season", {})[cid] = (
                "비교한 달이 충분합니다" if ok else "비교한 달이 적어 참고용입니다")

    # 판정
    verdict, request = "pass", None
    usable = [k for k in results if k != "custom"] or (["custom"] if "custom" in results else [])
    if need_matched and round_ < config.MAX_REANALYSIS:
        verdict = "reanalyze"
        request = {"matched_years": True, "rerun": ["season_stability"],
                   "reason": "연도 효과 — 같은 시즌연도끼리 다시 비교"}
    elif not usable:
        verdict = "fail"

    always = STATIC_LIMITS["always"]
    limits = always[:1]
    for m in ("season", "tourism", "weekday", "weather"):
        if m in nav["metrics"]:
            limits += STATIC_LIMITS[m]
    limits = list(dict.fromkeys(limits + always[1:]))
    dyn = [f["message"] for f in found if f["status"] in ("warn", "fail")]

    out = {"round": round_, "verdict": verdict, "reanalysis_request": request, "checks": found,
           "reliability": reliability, "limitations": limits, "dynamic_limitations": dyn}
    n_warn = sum(f["status"] == "warn" for f in found)
    ctx.emit("critic", {"pass": f"검증 통과 (주의 {n_warn}건은 한계로 표시)",
                        "reanalyze": f"재분석 요청: {request['reason'] if request else ''}",
                        "fail": "전달할 수 있는 결과가 없습니다"}[verdict], verdict=verdict)
    return out
