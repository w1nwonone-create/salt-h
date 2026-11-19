"""① Planner — 사용자의 질문을 실행 가능한 분석 계획(JSON)으로 구체화합니다.

규칙 기반 해석을 먼저 수행하고, LLM 이 연결되어 있으면 LLM 해석으로 빈 곳을 채웁니다.
LLM 이 제안한 값은 카탈로그·장소 목록에 있는 값만 받아들입니다(환각 방지).
업종·조건·후보지가 불분명하면 ``ask_user`` 로 선택지를 제시합니다.
"""
from __future__ import annotations

import re

import config
from agent.context import RunContext
from agent.llm import load_prompt
from tools import geo
from tools.catalog import load_catalog

ALL_CONDITIONS = ["season", "tourism", "weekday", "weather"]
CONDITION_OPTIONS = [
    {"label": "비수기", "value": "season"},
    {"label": "평일", "value": "weekday"},
    {"label": "비 오는 날", "value": "weather"},
    {"label": "모두 비교해 주세요", "value": "all"},
]
COMPARE_WORDS = ["비교", "어디", "어느", "중에서", "둘 중", "중 어디", "나을", "괜찮", "체력", "진단"]
UNSUPPORTED = [  # 수행하지 않는 범위(계획서 3.4)
    (r"(매출|수익).{0,6}(예측|얼마.{0,4}벌|나올)", "개별 점포의 매출 예측"),
    (r"(계약|여기로|어디로).{0,6}(해야|할까요|하세요|정해)", "특정 후보지에 대한 계약 권유"),
    (r"(임대료|월세|권리금|보증금)", "임대료 분석"),
    (r"(경쟁\s*점포|경쟁점|가게\s*수|점포\s*수.*몇)", "경쟁 점포 현황"),
]


def ask_user(question: str, options: list[dict], kind: str) -> dict:
    """Tool: 사용자에게 선택지를 제시합니다(UI 가 버튼으로 표시)."""
    return {"type": kind, "question": question, "options": options}


# ---------------------------------------------------------------------------------
def _match_places(text: str) -> list[geo.Place]:
    hits = []
    for p in geo.places():
        names = sorted({p.name, *p.aliases}, key=len, reverse=True)
        pos = [text.find(n) for n in names if n and text.find(n) >= 0]
        if pos:
            hits.append((min(pos), p))
    hits.sort(key=lambda x: x[0])
    out, seen = [], set()
    for _, p in hits:
        if p.id not in seen:
            out.append(p)
            seen.add(p.id)
    return out[:3]


def _match_industry(text: str) -> str | None:
    inds = geo.load_reference()["industries"]
    best = None
    for key, spec in inds.items():
        for kw in spec["keywords"]:
            i = text.find(kw)
            if i >= 0 and (best is None or i < best[0]):
                best = (i, key)
    return best[1] if best else None


def _match_metrics(text: str) -> list[str]:
    metrics = load_catalog()["metrics"]
    found = []
    for key, spec in metrics.items():
        if key == "scale":
            continue
        if any(kw in text for kw in spec["question_keywords"]):
            found.append(key)
    if re.search(r"비\s*(가|오|올|온|와|내|많)", text):
        found.append("weather")
    if "겨울" in text and "평일" in text:
        found += ["season", "weekday"]
    if re.search(r"(관광객|외지인).{0,6}(빠지|줄|없)", text):
        found.append("tourism")
    return list(dict.fromkeys(found))


def _period_months(text: str) -> int:
    m = re.search(r"최근\s*(\d+)\s*(년|개월)", text)
    if m:
        n = int(m.group(1)) * (12 if m.group(2) == "년" else 1)
        return max(6, min(config.ANALYSIS_MONTHS, n))
    if "1년" in text or "올해" in text:
        return 12
    return config.ANALYSIS_MONTHS


def _industry_spec(key: str) -> dict:
    spec = geo.load_reference()["industries"][key]
    return {"key": key, "label": spec["label"], "biz_cd": spec["biz_cd"], "pos": spec.get("pos", [])}


def _llm_plan(ctx: RunContext, question: str, answers: dict) -> dict | None:
    if not ctx.llm.available:
        return None
    cat = load_catalog()
    places_txt = "\n".join(f"- {p.id}: {p.name} (별칭: {', '.join(p.aliases)})" for p in geo.places())
    inds_txt = "\n".join(f"- {k}: {v['label']}" for k, v in geo.load_reference()["industries"].items())
    met_txt = "\n".join(f"- {k}: {v['label']}" for k, v in cat["metrics"].items())
    user = (f"## 사용자 질문\n{question}\n\n## 이미 받은 답변\n{answers}\n\n## 장소 목록\n{places_txt}\n\n"
            f"## 업종 목록\n{inds_txt}\n\n## 지표 목록\n{met_txt}")
    try:
        return ctx.llm.json(load_prompt("planner"), user, purpose="planner")
    except Exception as e:  # noqa: BLE001
        ctx.emit("planner", "LLM 해석에 실패해 규칙 기반 해석을 사용합니다.", error=str(e))
        return None


# ---------------------------------------------------------------------------------
def plan(ctx: RunContext, request: dict) -> dict:
    """request = {question, candidates?:[{label, lat, lon, place_id?}], industry?, answers?:{}}"""
    q = (request.get("question") or "").strip()
    answers = dict(request.get("answers") or {})
    notes, source = [], "rules"

    # 1) 후보지 ---------------------------------------------------------------
    cands = []
    for c in request.get("candidates") or []:
        p = geo.place_by_id(c.get("place_id")) if c.get("place_id") else None
        cands.append({"label": c.get("label") or (p.name if p else "후보지"),
                      "lat": float(c.get("lat", p.lat if p else 0)), "lon": float(c.get("lon", p.lon if p else 0)),
                      "place_id": c.get("place_id")})
    if not cands:
        cands = [{"label": p.name, "lat": p.lat, "lon": p.lon, "place_id": p.id} for p in _match_places(q)]

    # 2) 업종 · 지표 ------------------------------------------------------------
    industry = request.get("industry") or answers.get("industry") or _match_industry(q)
    metrics = _match_metrics(q)
    custom = None

    llm = _llm_plan(ctx, q, answers)
    if llm:
        source = "llm+rules"
        inds = geo.load_reference()["industries"]
        if not industry and llm.get("industry") in inds:
            industry = llm["industry"]
        valid = [m for m in llm.get("metrics", []) if m in load_catalog()["metrics"] and m != "scale"]
        metrics = list(dict.fromkeys(metrics + valid))
        if not cands:
            for pid in llm.get("places", [])[:3]:
                p = geo.place_by_id(pid)
                if p:
                    cands.append({"label": p.name, "lat": p.lat, "lon": p.lon, "place_id": p.id})
        if llm.get("custom_request") and not metrics:
            custom = str(llm["custom_request"])[:500]

    cond = answers.get("conditions")
    if cond:
        metrics = list(dict.fromkeys(metrics + (ALL_CONDITIONS if cond == "all" else [cond])))

    # 3) 범위 밖 질문 -------------------------------------------------------------
    out_of_scope = [label for pat, label in UNSUPPORTED if re.search(pat, q)]
    if out_of_scope:
        notes.append("이 질문의 일부(" + ", ".join(out_of_scope) + ")는 데이터로 답할 수 없는 범위라 제외하고, "
                     "상권의 경향과 변동 폭만 분석합니다.")

    # 4) 확인이 필요한 항목 -----------------------------------------------------------
    clarification = None
    is_compare = any(w in q for w in COMPARE_WORDS) or len(cands) >= 2 or not q
    if not cands:
        clarification = ask_user("분석할 후보지를 지도에서 누르거나 목록에서 골라 주세요. (최대 3곳)", [], "location")
    elif not industry:
        opts = [{"label": v["label"], "value": k} for k, v in geo.load_reference()["industries"].items()]
        clarification = ask_user("어떤 업종을 생각하고 계신가요?", opts, "industry")
    elif not metrics and not custom:
        if is_compare or not ctx.llm.available:
            clarification = ask_user(
                "어떤 상황이 가장 마음에 걸리시나요? 비수기, 평일, 비 오는 날 중에서 고르시거나, 모두 비교해 드릴 수도 있습니다.",
                CONDITION_OPTIONS, "conditions")
    if len(cands) > 3:
        notes.append("후보지는 최대 3곳까지 비교합니다. 앞의 3곳만 분석합니다.")
        cands = cands[:3]

    metric_list = []
    if metrics:
        metric_list = ["scale"] + [m for m in ["season", "tourism", "weekday", "weather", "time"] if m in metrics]
    ind = _industry_spec(industry) if industry else None

    plan_ = {
        "question": q,
        "candidates": cands,
        "industry": ind,
        "metrics": metric_list,
        "custom_request": custom,
        "period": {"months": _period_months(q)},
        "peak_months": config.PEAK_MONTHS,
        "off_months": config.OFF_MONTHS,
        "rain_mm": config.RAIN_MM,
        "clarification": clarification,
        "answers": answers,
        "notes": notes,
        "source": source,
        "llm": ctx.llm.label,
    }
    return plan_
