"""⑤ Reporter — 검증된 결과를 비전문가도 바로 판단에 쓸 수 있는 리포트로 전달합니다.

* 모든 문장의 수치는 코드 산출값에서 직접 만들어집니다(결정적 문장).
* LLM 이 연결되어 있으면 문장을 더 자연스럽게 다듬되, LLM 문장 속 수치가 코드 산출값과
  하나라도 대조되지 않으면 LLM 문장을 버리고 결정적 문장을 사용합니다(verify_numbers).
* 리포트는 "어디가 더 낫다"가 아니라 "어떤 조건에서 어떤 차이가 있다"를 전달합니다.
"""
from __future__ import annotations

import datetime as dt
import json

import config
from agent.context import RunContext
from agent.llm import load_prompt
from tools import charts
from tools.catalog import load_catalog
from tools.checks import numbers_in, verify_numbers
from tools.report import render_report

SLOTS = ["오전", "점심", "오후", "저녁", "밤"]
WEEK = ["월", "화", "수", "목", "금", "토", "일", "공휴일"]


def pct(v) -> str:
    return "–" if v is None else f"{round(v * 100)}%"


def man(v) -> str:
    return "–" if v is None else f"{round(v / 10_000):,}만원"


def months_label(ms: list[int]) -> str:
    ms = list(ms)
    if ms == [11, 12, 1, 2]:
        return "11~2월"
    if ms == [7, 8]:
        return "7~8월"
    return "·".join(f"{m}월" for m in ms)


def ym_label(ym: str) -> str:
    return f"{ym[:4]}년 {int(ym[4:])}월"


def season_word(r):
    if r is None:
        return ""
    return "시기별 차이가 작은 편" if r >= .7 else ("중간 정도" if r >= .5 else "시기별로 차이가 큰 편")


def _cmp(vals: dict, unit_gap: float = .05) -> tuple[str | None, str | None, bool]:
    """vals: {tag: v}. (최대 tag, 최소 tag, 차이가 작은가)"""
    v = {k: x for k, x in vals.items() if x is not None}
    if len(v) < 2:
        return None, None, True
    hi, lo = max(v, key=v.get), min(v, key=v.get)
    return hi, lo, (v[hi] - v[lo]) < unit_gap


def build(ctx: RunContext, plan: dict, nav: dict, analysis: dict, critic: dict) -> dict:
    res = analysis["results"]
    cands = nav["candidates"]
    tags = {c["id"]: c["tag"] for c in cands}
    name = {c["id"]: f"{c['tag']} {c['label']}" for c in cands}
    biz = plan["industry"]["label"] if plan.get("industry") else ""
    peak_l, off_l = months_label(plan["peak_months"]), months_label(plan["off_months"])
    multi = len(cands) >= 2

    summary, consult, rows, figs, evidence = [], [], [], [], []

    if critic["verdict"] == "fail":
        return _unanswerable(ctx, plan, nav, critic)

    s = res.get("season_stability")
    t = res.get("tourism_dependency")
    w = res.get("weekday_stability")
    wx = res.get("weather_sensitivity")
    tp = res.get("time_pattern")

    # ---- 규모 · 시즌 ------------------------------------------------------------
    if s:
        sc = s["candidates"]
        scale = {c: sc[c]["card"]["avg_monthly_recent12"] for c in sc}
        rows.append({"label": "월평균 카드 소비 (후보지 격자, 최근 12개월)", "values": {c: man(v) for c, v in scale.items()}})
        rows.append({"label": "└ 주변 3×3 격자 합계", "values": {c: man(sc[c]["card_3x3"]["avg_monthly_recent12"]) for c in sc},
                     "sub": True})
        if any("pos" in sc[c] for c in sc):
            rows.append({"label": "외식업 포스 표본 점포 수 (월평균)",
                         "values": {c: ("–" if "pos" not in sc[c] else f"{sc[c]['pos']['store_cnt_avg']:.0f}곳") for c in sc}})
        ratio = {c: sc[c]["card"]["ratio"] for c in sc}
        rows.append({"label": f"시즌 안정성 (비수기 {off_l} ÷ 성수기 {peak_l})", "key": "season",
                     "values": {c: (f"{pct(v)} · {season_word(v)}" if v is not None else "–") for c, v in ratio.items()}})
        rows.append({"label": "└ 주변 3×3 격자", "values": {c: pct(sc[c]["card_3x3"]["ratio"]) for c in sc}, "sub": True})
        if any(sc[c].get("pos") and sc[c]["pos"].get("ratio") is not None for c in sc):
            rows.append({"label": "└ 외식업 포스 매출 기준", "values": {c: pct((sc[c].get("pos") or {}).get("ratio")) for c in sc},
                         "sub": True})

        if multi:
            peaks = {tags[c]: sc[c]["card"]["peak_mean"] for c in sc}
            hi, lo, close = _cmp({k: v for k, v in peaks.items()}, unit_gap=0)
            pv = [v for v in peaks.values() if v]
            similar_peak = pv and (max(pv) / min(pv) - 1) < .15
            summary.append(
                f"성수기({peak_l})에는 후보지 격자의 {biz} 월평균 카드 소비가 "
                + ", ".join(f"{name[c]} {man(sc[c]['card']['peak_mean'])}" for c in sc)
                + ("으로 비슷한 수준입니다." if similar_peak else "입니다."))
            hi, lo, close = _cmp({tags[c]: v for c, v in ratio.items()})
            line = (f"비수기({off_l})에는 " + ", ".join(f"{name[c]}가 성수기의 {pct(ratio[c])}" for c in sc) + " 수준을 유지해, ")
            line += ("두 곳의 변화 폭이 비슷했습니다." if close and len(sc) == 2 else
                     "후보지 간 변화 폭이 비슷했습니다." if close else f"{hi} 후보지의 변화 폭이 가장 작았습니다." if len(sc) > 2
                     else f"{hi} 후보지의 변화 폭이 더 작았습니다.")
            summary.append(line)
        else:
            c = next(iter(sc))
            summary.append(f"후보지 격자의 {biz} 카드 소비는 성수기({peak_l}) 월평균 {man(sc[c]['card']['peak_mean'])}, "
                           f"비수기({off_l}) 월평균 {man(sc[c]['card']['off_mean'])}으로, 비수기에 성수기의 {pct(ratio[c])} 수준"
                           f"({season_word(ratio[c])})입니다.")
        if any(v is not None and v < .5 for v in ratio.values()):
            consult.append("비수기 평일의 매출 수준을 기준으로 임대료와 인건비 등 고정비를 감당할 수 있는지 함께 검토해 보시기를 권합니다.")

        xl = [f"{m['ym'][2:4]}.{m['ym'][4:]}" for m in sc[next(iter(sc))]["monthly"]]
        months = [int(m["ym"][4:]) for m in sc[next(iter(sc))]["monthly"]]
        figs.append({"title": f"월별 {biz} 카드 소비 추이 (후보지 격자, 만원)", "svg": charts.line_chart(
            xl, [(name[c], [None if m["card_amt"] is None else m["card_amt"] / 1e4 for m in sc[c]["monthly"]]) for c in sc],
            "월별 카드 소비 추이",
            shade=[i for i, m in enumerate(months) if m in plan["peak_months"]],
            shade2=[i for i, m in enumerate(months) if m in plan["off_months"]],
            note=f"노란 배경: 성수기({peak_l}) · 파란 배경: 비수기({off_l}) · 끊긴 구간: 결측 또는 최소 집계 기준 미달")})
        sy = s.get("season_years_used")
        period = f"{ym_label(s['months'][0])} ~ {ym_label(s['months'][1])}"
        evidence.append({"item": "시즌 안정성·소비 규모", "data": "카드 이용 현황(500m격자), 외식업 포스 이용 현황(500m격자)",
                         "period": period + (f" 중 같은 시즌연도({', '.join(map(str, sy))}년 여름과 그 직후 겨울)" if sy else ""),
                         "basis": "; ".join(f"{tags[c]} 성수기 {sc[c]['card']['peak_months_n']}개월·비수기 {sc[c]['card']['off_months_n']}개월"
                                            for c in sc)})

    # ---- 관광 의존도 ------------------------------------------------------------
    if t:
        tb = t["by_bjd"]
        ts = {c["id"]: tb.get(c["bjd"], {}).get("tourist_share") for c in cands}
        to = {c["id"]: tb.get(c["bjd"], {}).get("tourist_share_off") for c in cands}
        rows.append({"label": "관광 의존도 (관광객 소비 비중, 법정동)", "key": "tourism", "values": {c: pct(v) for c, v in ts.items()}})
        rows.append({"label": f"└ 비수기({off_l})", "values": {c: pct(v) for c, v in to.items()}, "sub": True})
        if multi:
            hi, lo, close = _cmp({tags[c]: 1 - v for c, v in ts.items() if v is not None})
            summary.append("관광객 소비 비중은 " + ", ".join(f"{tags[c]} {pct(ts[c])}" for c in ts)
                           + (f"로, 도민 소비 비중은 {hi} 후보지가 더 높았습니다." if not close else "로 비슷했습니다."))
        else:
            c = cands[0]["id"]
            summary.append(f"관광객 소비 비중은 {pct(ts[c])}이며, 비수기에는 {pct(to[c])}입니다.")
        evidence.append({"item": "관광 의존도", "data": "카드 이용 현황(요일별)_v02 — 관광구분(개별·단체관광객·도민)",
                         "period": f"{ym_label(t['months'][0])} ~ {ym_label(t['months'][1])}", "basis": "법정동 단위 이용 금액 비중"})

    # ---- 평일 안정성 ------------------------------------------------------------
    if w:
        wb = w["by_bjd"]
        wr = {c["id"]: wb.get(c["bjd"], {}).get("ratio") for c in cands}
        ow = {c["id"]: wb.get(c["bjd"], {}).get("off_weekday_vs_peak_weekend") for c in cands}
        rows.append({"label": "평일 안정성 (평일 하루 ÷ 주말·공휴일 하루)", "key": "weekday", "values": {c: pct(v) for c, v in wr.items()}})
        rows.append({"label": "└ 비수기 평일 하루 ÷ 성수기 주말 하루", "values": {c: pct(v) for c, v in ow.items()}, "sub": True})
        summary.append("평일 하루 소비는 주말·공휴일 하루의 " + ", ".join(f"{tags[c]} {pct(wr[c])}" for c in wr)
                       + " 수준이며, 가장 한산한 비수기 평일 하루는 가장 붐비는 성수기 주말 하루의 "
                       + ", ".join(f"{tags[c]} {pct(ow[c])}" for c in ow) + "입니다.")
        figs.append({"title": f"요일별 하루 평균 {biz} 카드 소비 (법정동, 만원)", "svg": charts.grouped_bars(
            WEEK, [(name[c["id"]], [None if (v := wb.get(c["bjd"], {}).get("by_week_per_day", {}).get(d)) is None else v / 1e4
                                     for d in WEEK]) for c in cands],
            "요일별 하루 평균 소비", fmt=lambda v: f"{v:,.0f}", note="월 단위 요일별 합계 ÷ 해당 요일 일수")})
        evidence.append({"item": "평일 안정성", "data": "카드 이용 현황(요일별)_v02",
                         "period": f"{ym_label(w['months'][0])} ~ {ym_label(w['months'][1])}",
                         "basis": "; ".join(f"{c['tag']} 평일 {wb.get(c['bjd'], {}).get('weekday_days', 0)}일·주말/공휴일 "
                                            f"{wb.get(c['bjd'], {}).get('weekend_days', 0)}일" for c in cands)})

    # ---- 날씨 민감도 ------------------------------------------------------------
    if wx:
        xc = wx["candidates"]
        vp = {c: (xc[c].get("visit_pop") or {}).get("effect") for c in xc}
        bs = {c: (xc[c].get("bus") or {}).get("effect") for c in xc}
        rel = critic["reliability"].get("weather", {})

        def chg(v):
            return "–" if v is None else (f"{round(-v * 100)}% 감소" if v < 0 else f"{round(v * 100)}% 증가")

        rows.append({"label": f"날씨 민감도 (비 오는 날 방문 인구 변화, 행정동)", "key": "weather", "values": {c: chg(v) for c, v in vp.items()}})
        rows.append({"label": "└ 인근 정류소 버스 이용 변화", "values": {c: chg(v) for c, v in bs.items()}, "sub": True})
        d_rain = {c: (xc[c].get("visit_pop") or {}).get("rain_days") for c in xc}
        d_dry = {c: (xc[c].get("visit_pop") or {}).get("dry_days") for c in xc}
        hi, lo, close = _cmp({tags[c]: v for c, v in vp.items()})
        rel_txt = next(iter(rel.values()), "") if len(set(rel.values())) == 1 else ""
        days_txt = ", ".join(f"{tags[c]} 우천 {d_rain[c]}일·비우천 {d_dry[c]}일" for c in xc if d_rain[c] is not None)
        if multi:
            summary.append(f"비 오는 날(일강수량 {config.RAIN_MM:g}mm 이상) 방문 인구는 같은 달·같은 요일유형의 비 오지 않은 날보다 "
                           + ", ".join(f"{tags[c]} {chg(vp[c])}" for c in vp)
                           + ("로, 큰 차이가 없었습니다." if close else f"로, {lo} 후보지 쪽 감소 폭이 더 컸습니다.")
                           + (f" ({days_txt} — {rel_txt})" if days_txt else ""))
        else:
            c = next(iter(vp))
            summary.append(f"비 오는 날(일강수량 {config.RAIN_MM:g}mm 이상) 방문 인구는 {chg(vp[c])}했습니다."
                           + (f" ({days_txt} — {rel_txt})" if days_txt else ""))
        figs.append({"title": "비 오는 날 감소율 (같은 달·같은 요일유형 비교)", "svg": charts.grouped_bars(
            ["방문 인구(행정동)", "버스 이용(인근 정류소)"],
            [(name[c], [None if vp[c] is None else max(0.0, -vp[c]), None if bs[c] is None else max(0.0, -bs[c])]) for c in xc],
            "비 오는 날 감소율", note="막대가 길수록 비 오는 날 사람이 더 많이 줄어듭니다")})
        p0 = min((x.get("visit_pop") or {}).get("date_from", "9999") for x in xc.values())
        p1 = max((x.get("visit_pop") or {}).get("date_to", "0000") for x in xc.values())
        evidence.append({"item": "날씨 민감도", "data": "내국인 유동인구(읍면동)_v02, 버스 정류소별 이용 현황, 일일 날씨 정보",
                         "period": f"방문인구 {p0} ~ {p1}, 버스 {wx['period'][0]} ~ {wx['period'][1]}",
                         "basis": days_txt + " · 같은 달·같은 요일유형(평일/주말·공휴일) 안에서 비교"})

    # ---- 시간대 ----------------------------------------------------------------
    if tp:
        tb2 = tp["by_bjd"]
        pk = {c["id"]: tb2.get(c["bjd"], {}) for c in cands}
        rows.append({"label": "핵심 시간대 (카드 소비 비중 최대)", "key": "time",
                     "values": {c: (f"{v['peak_slot']} {pct(v['shares'][v['peak_slot']])}" if v.get("peak_slot") else "–")
                                for c, v in pk.items()}})
        summary.append("카드 소비가 가장 많은 시간대는 " + ", ".join(
            f"{tags[c]} {v['peak_slot']}({pct(v['shares'][v['peak_slot']])})" for c, v in pk.items() if v.get("peak_slot")) + "입니다.")
        figs.append({"title": "시간대별 카드 소비 비중 (법정동)", "svg": charts.grouped_bars(
            SLOTS, [(name[c["id"]], [pk[c["id"]].get("shares", {}).get(s_) for s_ in SLOTS]) for c in cands], "시간대별 소비 비중",
            note="오전·점심·오후·저녁·밤 구분은 데이터 명세 기준")})
        evidence.append({"item": "시간대 패턴", "data": "카드 이용 현황(시간대)_v02", "period": "월 단위 비교 기간과 동일", "basis": "법정동 단위"})

    # ---- 한눈에 보기 차트 -----------------------------------------------------------
    cats, series = [], {c["id"]: [] for c in cands}
    if s:
        cats.append("시즌 안정성")
        for c in cands:
            series[c["id"]].append(s["candidates"][c["id"]]["card"]["ratio"])
    if t:
        cats.append("도민 소비 비중")
        for c in cands:
            v = t["by_bjd"].get(c["bjd"], {}).get("tourist_share")
            series[c["id"]].append(None if v is None else 1 - v)
    if w:
        cats.append("평일 안정성")
        for c in cands:
            series[c["id"]].append(w["by_bjd"].get(c["bjd"], {}).get("ratio"))
    if wx:
        cats.append("우천일 방문 유지율")
        for c in cands:
            v = (wx["candidates"][c["id"]].get("visit_pop") or {}).get("effect")
            series[c["id"]].append(None if v is None else 1 + v)
    if len(cats) >= 2:
        figs.insert(0, {"title": "상권 체력 한눈에 보기", "svg": charts.grouped_bars(
            cats, [(name[c["id"]], series[c["id"]]) for c in cands], "상권 체력 한눈에 보기", vmax=1.2,
            note="모든 막대는 높을수록 해당 조건에서 덜 흔들린다는 뜻입니다(100% = 변화 없음)")})

    # ---- 자유 질문 결과 --------------------------------------------------------------
    custom = res.get("custom")
    if custom:
        evidence.append({"item": "자유 질문 분석", "data": "Agent 가 작성한 분석 코드(상세 보기 참고)", "period": "", "basis": ""})

    consult.append("이 분석에는 임대료, 주변 경쟁 점포 현황, 주차 여건이 포함되어 있지 않습니다.")
    for n in plan.get("notes", []):
        consult.insert(0, n)

    # ---- LLM 다듬기 + 수치 대조 -------------------------------------------------------
    allowed = set()
    for txt in summary + [v for r in rows for v in r["values"].values()] + [json.dumps(evidence, ensure_ascii=False)]:
        allowed |= set(numbers_in(txt))
    allowed |= {str(x) for x in plan["peak_months"] + plan["off_months"]} | {"1", "2", "3", "500", "10", "12", "24", "3×3"}
    polished, verify_log = None, None
    if ctx.llm.available:
        polished, verify_log = _polish(ctx, summary, consult, allowed, plan)
    final_summary = polished["summary"] if polished else summary
    final_consult = polished.get("consult", consult) if polished else consult
    if verify_log:
        ctx.emit("reporter", verify_log)

    ds = nav["datasets"]
    report = {
        "title": "상권 체력 비교 리포트" if multi else "상권 체력 진단 리포트",
        "question": plan["question"],
        "industry": biz,
        "created": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "llm": ctx.llm.label,
        "candidates": [{"tag": c["tag"], "id": c["id"], "label": c["label"], "grid": c["grid"], "bjd_nm": c["bjd_nm"],
                        "emd": c["emd"], "stops": [s_["name"] for s_ in c["stops"]], "station": c["station"]["name"],
                        "station_km": round(c["station"]["distance_m"] / 1000, 1)} for c in cands],
        "summary": final_summary,
        "summary_source": "llm_verified" if polished else "deterministic",
        "consult": final_consult,
        "rows": rows,
        "figures": figs,
        "evidence": evidence,
        "datasets": [{"name": d["name"], "grain": d["grain"], "export": d["export"],
                      "period": (d["period"] or {}).get("from", "") + " ~ " + (d["period"] or {}).get("to", "")} for d in ds],
        "limitations": critic["limitations"],
        "dynamic_limitations": critic["dynamic_limitations"],
        "checks": critic["checks"],
        "custom": custom,
        "sources": load_catalog()["sources_footer"],
        "verify_log": verify_log,
        "run_dir": ctx.run_dir.name,
    }
    bad = verify_numbers(" ".join(report["summary"] + report["consult"]), allowed)
    if bad:  # 결정적 문장에서도 대조 실패 시 리포트 생성 중단(계획서 6.1)
        raise RuntimeError(f"리포트 수치 대조 실패: {bad}")
    html = render_report(report)
    (ctx.run_dir / "report.html").write_text(html, encoding="utf-8")
    ctx.save_json("report.json", {k: v for k, v in report.items() if k != "figures"})
    ctx.emit("reporter", "리포트를 만들었습니다.", file="report.html")
    report["html"] = html
    return report


def _polish(ctx: RunContext, summary: list[str], consult: list[str], allowed: set[str], plan: dict):
    user = json.dumps({"question": plan["question"], "summary": summary, "consult": consult}, ensure_ascii=False, indent=1)
    try:
        out = ctx.llm.json(load_prompt("reporter"), user, purpose="reporter.polish")
        sm = [str(x) for x in out.get("summary", [])][:8]
        cs = [str(x) for x in out.get("consult", [])][:6] or consult
    except Exception as e:  # noqa: BLE001
        return None, f"LLM 문장 다듬기 실패 — 결정적 문장 사용 ({type(e).__name__})"
    if not sm:
        return None, "LLM 응답이 비어 결정적 문장 사용"
    bad = verify_numbers(" ".join(sm + cs), allowed)
    if bad:
        return None, f"LLM 문장에서 코드 산출값과 대조되지 않는 수치({', '.join(bad[:5])})가 발견되어 제외하고 결정적 문장을 사용했습니다."
    if any(w in " ".join(sm) for w in ("추천", "계약하세요", "하는 것이 좋", "더 낫", "선택하세요")):
        return None, "LLM 문장에 단정적 추천 표현이 있어 제외하고 결정적 문장을 사용했습니다."
    return {"summary": sm, "consult": cs}, "LLM 문장 수치 대조 통과"


def _unanswerable(ctx: RunContext, plan: dict, nav: dict, critic: dict) -> dict:
    alts = ["두 후보지의 비수기와 성수기 소비 차이를 비교해 주세요.", "이 자리는 평일에도 손님이 꾸준한가요?",
            "비 오는 날 이 동네 방문 인구는 얼마나 줄어드나요?", "몇 시에 손님이 많을까요?"]
    reasons = [c["message"] for c in critic["checks"] if c["status"] == "fail"] or list(nav.get("unavailable", {}).values())
    report = {
        "title": "답하기 어려운 질문입니다", "question": plan["question"], "industry": (plan.get("industry") or {}).get("label", ""),
        "created": dt.datetime.now().strftime("%Y-%m-%d %H:%M"), "llm": ctx.llm.label, "candidates": [],
        "summary": ["가진 데이터로는 이 질문에 믿을 만한 답을 드리기 어렵습니다. 무리하게 답하지 않겠습니다."] + reasons[:3],
        "summary_source": "deterministic", "consult": ["대신 이렇게 물어보실 수 있습니다: " + " / ".join(alts)],
        "rows": [], "figures": [], "evidence": [], "datasets": [], "limitations": critic["limitations"],
        "dynamic_limitations": [], "checks": critic["checks"], "custom": None,
        "sources": load_catalog()["sources_footer"], "verify_log": None, "unanswerable": True, "alternatives": alts,
        "run_dir": ctx.run_dir.name,
    }
    html = render_report(report)
    (ctx.run_dir / "report.html").write_text(html, encoding="utf-8")
    ctx.save_json("report.json", report)
    report["html"] = html
    return report
