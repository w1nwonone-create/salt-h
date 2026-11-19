"""Jeju-AgenticX — Streamlit UI (localhost:8501)

화면 흐름: ① 시작(질문·후보지·업종) → ② 위치 확인 → ③ 진행 → ④ 리포트 → ⑤ 상세 보기(접힘)
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

import config
from agent import planner
from agent.context import RunContext
from agent.graph import run_agent
from agent.llm import LLM
from agent.navigator import link_location
from tools import db, geo
from tools.report import export_pdf

st.set_page_config(page_title="Jeju-AgenticX 상권 체력 분석", page_icon="🍊", layout="wide")

st.markdown("""
<style>
  html, body, [class*="css"] { font-size: 17px; }
  .big-q textarea, .big-q input { font-size: 20px !important; }
  .stButton > button { font-size: 17px; padding: .55rem 1rem; border-radius: 10px; }
  .step { display:inline-block; padding:4px 12px; border-radius:999px; background:#e2e8f0; margin-right:6px; font-size:14px; }
  .step.on { background:#0f766e; color:#fff; }
  .cand-chip { border:1px solid #cbd5e1; border-radius:10px; padding:8px 12px; margin:4px 0; }
</style>
""", unsafe_allow_html=True)

EXAMPLES = [
    ("후보지 비교하기", "후보지 비교하기"),
    ("이 자리는 비수기에도 괜찮을까요?", "이 자리는 비수기에도 괜찮을까요?"),
    ("몇 시에 손님이 많을까요?", "이 자리는 몇 시에 손님이 많을까요?"),
    ("비 오는 날엔 얼마나 줄어요?", "비 오는 날에는 손님이 얼마나 줄어드나요?"),
]
MODES = {"자동 (Key 있으면 외부 LLM → 로컬 모델 → 규칙)": "auto", "외부 LLM": "anthropic",
         "오프라인 (로컬 모델)": "ollama", "규칙 기반 (LLM 없이)": "rules"}

ss = st.session_state
ss.setdefault("step", "start")
ss.setdefault("question", "")
ss.setdefault("cands", [])
ss.setdefault("industry", None)
ss.setdefault("answers", {})
ss.setdefault("clar", None)
ss.setdefault("result", None)
ss.setdefault("llm_mode", "auto")


# ---------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def ref_tables(db_mtime: float):
    stations = db.duckdb_query("SELECT * FROM bus_station").to_dict("records")
    wst = db.duckdb_query("SELECT * FROM weather_station").to_dict("records")
    meta = dict(db.duckdb_query("SELECT key, value FROM _meta").values.tolist())
    period = db.duckdb_query("SELECT MIN(base_year_month) a, MAX(base_year_month) b FROM card_grid_500m").iloc[0].tolist()
    return stations, wst, meta, period


def db_ready() -> bool:
    return Path(config.DB_PATH).exists()


def steps(active: str):
    names = [("start", "① 질문·후보지"), ("confirm", "② 위치 확인"), ("run", "③ 분석 진행"), ("report", "④ 리포트")]
    st.markdown(" ".join(f'<span class="step {"on" if k == active else ""}">{v}</span>' for k, v in names),
                unsafe_allow_html=True)


def add_candidate(label: str, lat: float, lon: float, place_id: str | None = None):
    if len(ss.cands) >= 3:
        st.warning("후보지는 최대 3곳까지 비교할 수 있습니다.")
        return
    ss.cands.append({"label": label, "lat": lat, "lon": lon, "place_id": place_id})


def request() -> dict:
    return {"question": ss.question, "candidates": ss.cands, "industry": ss.industry, "answers": ss.answers}


def preview_plan() -> dict:
    """분석 전 계획만 미리 세워 확인할 것(후보지·업종·조건)이 있는지 봅니다."""
    tmp = Path(tempfile.mkdtemp(prefix="jax_plan_"))
    ctx = RunContext.create(ss.question or "후보지 비교", ss.llm_mode, runs_dir=tmp)
    return planner.plan(ctx, request())


# ---- 사이드바 -------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 🍊 Jeju-AgenticX")
    st.caption("제주에서 창업을 준비하는 도민과 상담사를 위한 상권 체력 분석 AI Agent")
    label = st.selectbox("분석 엔진", list(MODES), index=list(MODES.values()).index(ss.llm_mode))
    ss.llm_mode = MODES[label]
    st.caption("현재: " + LLM(ss.llm_mode).label)
    if db_ready():
        stations, wstations, meta, period = ref_tables(Path(config.DB_PATH).stat().st_mtime)
        kind = "예시 데이터(명세서 동일 구조)" if meta.get("kind") == "sample" else "센터 실데이터"
        st.caption(f"데이터: {kind} · 카드 {period[0][:4]}.{period[0][4:]}~{period[1][:4]}.{period[1][4:]}")
    st.divider()
    st.caption("수치는 모두 실행된 분석 코드가 계산합니다. AI 는 숫자를 만들어내지 않습니다. "
               "결정을 대신하지 않고, 결정에 필요한 근거를 정리해 드립니다.")
    if st.button("처음부터 다시"):
        for k in ("step", "question", "cands", "industry", "answers", "clar", "result"):
            ss.pop(k, None)
        st.rerun()

if not db_ready():
    st.error("분석 데이터베이스가 없습니다. 먼저 `python scripts/build_sample_data.py` 를 실행해 주세요.")
    st.stop()

inds = geo.load_reference()["industries"]

# ---- ① 시작 화면 ------------------------------------------------------------------------
if ss.step == "start":
    steps("start")
    st.markdown("## 무엇이 궁금하신가요?")
    st.markdown('<div class="big-q">', unsafe_allow_html=True)
    ss.question = st.text_area("평소 말씀하시듯 적어 주세요", value=ss.question, height=90,
                               placeholder="예) 애월 해안도로와 한림 협재 쪽 중에서, 카페를 하기에 비수기에 덜 흔들리는 곳은 어디일까요?")
    st.markdown("</div>", unsafe_allow_html=True)
    cols = st.columns(2) + st.columns(2)
    for col, (lab, q) in zip(cols, EXAMPLES):
        if col.button(lab, use_container_width=True):
            ss.question = q
            ss.answers = {}
            st.rerun()

    left, right = st.columns([3, 2])
    with left:
        st.markdown("#### 후보지 지정 (최대 3곳)")
        tab_map, tab_list = st.tabs(["🗺️ 지도에서 누르기", "📋 법정동·정류소에서 고르기"])
        with tab_map:
            try:
                import folium
                from streamlit_folium import st_folium

                m = folium.Map(location=[33.40, 126.55], zoom_start=10, tiles="OpenStreetMap")
                for i, c in enumerate(ss.cands):
                    folium.Marker([c["lat"], c["lon"]], tooltip=f"{'ABC'[i]} {c['label']}",
                                  icon=folium.Icon(color=["blue", "orange", "green"][i])).add_to(m)
                out = st_folium(m, height=420, use_container_width=True, returned_objects=["last_clicked"])
                clicked = (out or {}).get("last_clicked")
                if clicked:
                    b = geo.point_to_bjd(clicked["lat"], clicked["lng"])
                    st.caption(f"누른 위치: {clicked['lat']:.5f}, {clicked['lng']:.5f} · 가까운 법정동 {b['bjd_nm']}")
                    nm = st.text_input("후보지 이름", value=f"{b['bjd_nm']} 매물")
                    if st.button("이 위치를 후보지로 추가", type="primary"):
                        add_candidate(nm, clicked["lat"], clicked["lng"])
                        st.rerun()
            except ImportError:
                st.info("지도 모듈이 없어 목록 선택으로 대신합니다. (pip install folium streamlit-folium)")
            st.caption("지도가 보이지 않으면(인터넷 미연결) 옆 탭의 목록에서 고르실 수 있습니다.")
        with tab_list:
            opts = {f"{p.name} — {p.bjd_nm}": ("place", p) for p in geo.places()}
            for s in stations:
                opts[f"정류소: {s['bus_station_nm']}"] = ("stop", s)
            pick = st.selectbox("법정동 또는 인근 정류소", ["선택하세요"] + list(opts))
            if pick != "선택하세요" and st.button("후보지로 추가", key="add_list"):
                kind_, obj = opts[pick]
                if kind_ == "place":
                    add_candidate(obj.name, obj.lat, obj.lon, obj.id)
                else:
                    add_candidate(f"{obj['bus_station_nm']} 정류소 인근", float(obj["latitude"]), float(obj["longitude"]))
                st.rerun()
    with right:
        st.markdown("#### 선택한 후보지")
        if not ss.cands:
            st.caption("아직 없습니다. 질문에 장소 이름(예: 협재, 함덕)을 적으셔도 찾아 드립니다.")
        for i, c in enumerate(list(ss.cands)):
            a, b_ = st.columns([5, 1])
            a.markdown(f'<div class="cand-chip"><b>{"ABC"[i]}</b> {c["label"]}</div>', unsafe_allow_html=True)
            if b_.button("✕", key=f"rm{i}"):
                ss.cands.pop(i)
                st.rerun()
        st.markdown("#### 업종")
        ind_opts = ["질문에서 알아서 찾기"] + [v["label"] for v in inds.values()]
        cur = inds[ss.industry]["label"] if ss.industry else "질문에서 알아서 찾기"
        sel = st.selectbox("업종", ind_opts, index=ind_opts.index(cur), label_visibility="collapsed")
        ss.industry = next((k for k, v in inds.items() if v["label"] == sel), None)

    # 함께 묻고 정리하기 (Planner 의 ask_user)
    if ss.clar:
        st.info("🤖 " + ss.clar["question"])
        if ss.clar["options"]:
            oc = st.columns(min(4, len(ss.clar["options"])))
            for i, o in enumerate(ss.clar["options"]):
                if oc[i % len(oc)].button(o["label"], key=f"opt{i}", use_container_width=True):
                    if ss.clar["type"] == "industry":
                        ss.industry = o["value"]
                    else:
                        ss.answers[ss.clar["type"]] = o["value"]
                    ss.clar = None
                    p = preview_plan()
                    if p["clarification"]:
                        ss.clar = p["clarification"]
                    else:
                        ss.cands = p["candidates"]
                        ss.step = "confirm"
                    st.rerun()

    if st.button("분석 시작 ▶", type="primary", use_container_width=True):
        p = preview_plan()
        ss.cands = p["candidates"] or ss.cands
        if p["industry"]:
            ss.industry = p["industry"]["key"]
        if p["clarification"]:
            ss.clar = p["clarification"]
        else:
            ss.clar = None
            ss.step = "confirm"
        st.rerun()

# ---- ② 위치 확인 ------------------------------------------------------------------------
elif ss.step == "confirm":
    steps("confirm")
    st.markdown("## 위치가 맞는지 확인해 주세요")
    linked = [link_location(c, stations, wstations) for c in ss.cands]
    try:
        import folium
        from streamlit_folium import st_folium

        m = folium.Map(location=[linked[0]["lat"], linked[0]["lon"]], zoom_start=13 if len(linked) == 1 else 11)
        colors = ["#2563eb", "#ea580c", "#059669"]
        for i, c in enumerate(linked):
            for g in c["grids_3x3"]:
                folium.Polygon(geo.grid_bounds(g), color=colors[i], weight=1, fill=False, dash_array="4").add_to(m)
            folium.Polygon(geo.grid_bounds(c["grid"]), color=colors[i], weight=3, fill=True, fill_opacity=.15,
                           tooltip=f"분석 격자 {c['grid']}").add_to(m)
            folium.Marker([c["lat"], c["lon"]], tooltip=f"{'ABC'[i]} {c['label']}",
                          icon=folium.Icon(color=["blue", "orange", "green"][i])).add_to(m)
            for s in c["stops"]:
                folium.CircleMarker([s["lat"], s["lon"]], radius=5, color=colors[i], fill=True,
                                    tooltip=f"정류소 {s['name']} ({s['distance_m']}m)").add_to(m)
        st_folium(m, height=440, use_container_width=True, returned_objects=[])
    except ImportError:
        pass
    cols = st.columns(len(linked))
    for i, (col, c) in enumerate(zip(cols, linked)):
        with col:
            st.markdown(f"**{'ABC'[i]} {c['label']}**")
            st.caption(f"법정동 {c['bjd_nm']} · 행정동 {c['emd']}")
            st.caption(f"분석 격자 {c['grid']}" + (" (격자 경계 근처 — 인접 격자도 함께 봅니다)" if c["near_boundary"] else ""))
            st.caption(f"반경 {c['stop_radius_m']}m 정류소: " + (", ".join(s["name"] for s in c["stops"]) or "없음"))
            st.caption(f"가까운 기상 관측소: {c['station']['name']} ({c['station']['distance_m'] / 1000:.1f}km)")
    a, b = st.columns(2)
    if a.button("◀ 다시 고르기", use_container_width=True):
        ss.step = "start"
        st.rerun()
    if b.button("위치가 맞습니다 · 분석 시작 ▶", type="primary", use_container_width=True):
        ss.step = "run"
        st.rerun()

# ---- ③ 진행 화면 ------------------------------------------------------------------------
elif ss.step == "run":
    steps("run")
    st.markdown("## 분석하고 있습니다")
    box = st.status("데이터를 찾고 있습니다 → 분석하고 있습니다 → 결과를 검증하고 있습니다", expanded=True)
    ds_area = st.empty()

    def on_event(ev):
        box.write(f"**{ev['message']}**" if ev["stage"] in ("planner", "navigator", "analyst", "critic", "reporter")
                  and ev["message"].endswith("니다") else ev["message"])
        if ev.get("datasets"):
            ds_area.info("이번 분석에 활용하는 데이터: " + ", ".join(ev["datasets"]))

    state, ctx = run_agent(request(), llm_mode=ss.llm_mode, on_event=on_event)
    ss.result = {"state": state, "run_dir": str(ctx.run_dir), "events": ctx.events}
    if state.get("status") == "done":
        box.update(label="분석을 마쳤습니다", state="complete", expanded=False)
        ss.step = "report"
        st.rerun()
    elif state.get("status") == "needs_user":
        ss.clar = state["plan"]["clarification"]
        ss.step = "start"
        st.rerun()
    else:
        box.update(label="분석 중 문제가 생겼습니다", state="error")
        st.error(state.get("error", "알 수 없는 오류"))
        if st.button("처음으로"):
            ss.step = "start"
            st.rerun()

# ---- ④ 리포트 / ⑤ 상세 보기 -----------------------------------------------------------------
elif ss.step == "report":
    steps("report")
    res = ss.result
    rep = res["state"]["report"]
    run_dir = Path(res["run_dir"])
    a, b, c = st.columns(3)
    a.download_button("리포트 저장 (HTML)", rep["html"].encode("utf-8"), file_name=f"jeju-agenticx_{run_dir.name}.html",
                      mime="text/html", use_container_width=True)
    if b.button("PDF 만들기", use_container_width=True):
        pdf = export_pdf(run_dir / "report.html")
        if pdf:
            ss.pdf = str(pdf)
        else:
            st.info("이 PC 에는 PDF 변환기가 없습니다. 아래 리포트의 ‘PDF로 저장 / 인쇄’ 버튼을 눌러 PDF 로 저장해 주세요.")
    if ss.get("pdf") and Path(ss.pdf).exists():
        b.download_button("PDF 내려받기", Path(ss.pdf).read_bytes(), file_name=Path(ss.pdf).name, mime="application/pdf")
    if c.button("새 질문하기", use_container_width=True):
        for k in ("step", "question", "cands", "industry", "answers", "clar", "result", "pdf"):
            ss.pop(k, None)
        st.rerun()

    components.html(rep["html"], height=2400, scrolling=True)

    with st.expander("⑤ 상세 보기 — Agent 가 생성·실행한 분석 코드와 실행 기록 (상담사·센터 담당자 검토용)"):
        st.caption(f"실행 폴더: {run_dir}  ·  재현: `python -m tools.replay {run_dir}`")
        t1, t2, t3, t4 = st.tabs(["실행 기록", "분석 계획·위치 연결", "분석 코드", "검증"])
        with t1:
            for ev in res["events"]:
                st.text(f"{ev['time'][11:]} [{ev['stage']}] {ev['message']}")
        with t2:
            for f in ("plan.json", "navigation.json"):
                if (run_dir / f).exists():
                    st.markdown(f"**{f}**")
                    st.json(json.loads((run_dir / f).read_text(encoding="utf-8")), expanded=False)
        with t3:
            for f in sorted((run_dir / "code").glob("*.py")):
                with st.expander(f.name):
                    st.code(f.read_text(encoding="utf-8"), language="python")
        with t4:
            for f in sorted(run_dir.glob("critic_round*.json")):
                st.markdown(f"**{f.name}**")
                st.json(json.loads(f.read_text(encoding="utf-8")), expanded=False)
