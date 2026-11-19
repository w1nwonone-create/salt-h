"""Agent 오케스트레이션 — Planner → Navigator → Analyst → Critic ⇄(재분석 최대 2회) → Reporter.

LangGraph 상태 그래프로 실행하며, LangGraph 가 설치되지 않은 환경에서도 같은 순서로 동작하는
순차 실행기로 자동 대체됩니다.
"""
from __future__ import annotations

import json
import traceback
from typing import Any, TypedDict

import config
from agent import analyst, critic, navigator, planner, reporter
from agent.context import STAGES, RunContext
from tools import db


class AgentState(TypedDict, total=False):
    request: dict
    plan: dict
    nav: dict
    analysis: dict
    critic: dict
    report: dict
    round: int
    status: str        # needs_user | done | error
    error: str


def _nodes(ctx: RunContext):
    def n_planner(s: AgentState) -> dict:
        ctx.emit("planner", STAGES["planner"])
        p = planner.plan(ctx, s["request"])
        ctx.save_json("plan.json", p)
        if p["clarification"]:
            ctx.emit("planner", "확인이 필요합니다: " + p["clarification"]["question"])
            return {"plan": p, "status": "needs_user"}
        ctx.emit("planner", f"분석 계획: 후보지 {len(p['candidates'])}곳 · {p['industry']['label'] if p['industry'] else ''} · "
                 f"지표 {', '.join(p['metrics']) or '자유 질문'}")
        return {"plan": p}

    def n_navigator(s: AgentState) -> dict:
        ctx.emit("navigator", STAGES["navigator"])
        nav = navigator.navigate(ctx, s["plan"])
        ctx.save_json("navigation.json", nav)
        return {"nav": nav}

    def n_analyst(s: AgentState) -> dict:
        ctx.emit("analyst", STAGES["analyst"] if not s.get("critic") else "재분석하고 있습니다")
        opts = (s.get("critic") or {}).get("reanalysis_request") or {}
        prev = s.get("analysis")
        merged = {**(prev or {}).get("options", {}), **opts}
        a = analyst.analyze(ctx, s["plan"], s["nav"], merged, previous=prev if opts else None)
        ctx.save_json("results.json", {"params": a["params"], "options": a["options"], "results": a["results"], "runs": a["runs"]})
        return {"analysis": a}

    def n_critic(s: AgentState) -> dict:
        ctx.emit("critic", STAGES["critic"])
        r = s.get("round", 0)
        c = critic.critique(ctx, s["plan"], s["nav"], s["analysis"], r)
        ctx.save_json(f"critic_round{r}.json", c)
        return {"critic": c, "round": r + 1}

    def n_reporter(s: AgentState) -> dict:
        ctx.emit("reporter", STAGES["reporter"])
        rep = reporter.build(ctx, s["plan"], s["nav"], s["analysis"], s["critic"])
        return {"report": rep, "status": "done"}

    return n_planner, n_navigator, n_analyst, n_critic, n_reporter


def _after_planner(s: AgentState) -> str:
    return "end" if s.get("status") == "needs_user" else "navigator"


def _after_critic(s: AgentState) -> str:
    return "analyst" if s["critic"]["verdict"] == "reanalyze" and s.get("round", 0) <= config.MAX_REANALYSIS else "reporter"


def build_graph(ctx: RunContext):
    from langgraph.graph import END, START, StateGraph

    n_planner, n_navigator, n_analyst, n_critic, n_reporter = _nodes(ctx)
    g = StateGraph(AgentState)
    g.add_node("planner", n_planner)
    g.add_node("navigator", n_navigator)
    g.add_node("analyst", n_analyst)
    g.add_node("critic", n_critic)
    g.add_node("reporter", n_reporter)
    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", _after_planner, {"navigator": "navigator", "end": END})
    g.add_edge("navigator", "analyst")
    g.add_edge("analyst", "critic")
    g.add_conditional_edges("critic", _after_critic, {"analyst": "analyst", "reporter": "reporter"})
    g.add_edge("reporter", END)
    return g.compile()


def _run_sequential(ctx: RunContext, state: AgentState) -> AgentState:
    n_planner, n_navigator, n_analyst, n_critic, n_reporter = _nodes(ctx)
    state.update(n_planner(state))
    if _after_planner(state) == "end":
        return state
    state.update(n_navigator(state))
    state.update(n_analyst(state))
    state.update(n_critic(state))
    while _after_critic(state) == "analyst":
        state.update(n_analyst(state))
        state.update(n_critic(state))
    state.update(n_reporter(state))
    return state


def run_agent(request: dict, llm_mode: str | None = None, on_event=None, db_path=None, runs_dir=None,
              run_name: str | None = None) -> tuple[AgentState, RunContext]:
    """request = {question, candidates?:[{label, lat, lon, place_id?}], industry?, answers?}"""
    ctx = RunContext.create(request.get("question") or "후보지 비교", llm_mode, on_event, db_path, runs_dir, run_name)
    ctx.save_json("request.json", request)
    try:
        ctx.save_json("data_version.json", db.data_version(ctx.db_path))
    except FileNotFoundError as e:
        ctx.emit("navigator", str(e))
        return {"request": request, "status": "error", "error": str(e)}, ctx
    ctx.emit("planner", f"분석 엔진: {ctx.llm.label}")
    state: AgentState = {"request": request, "round": 0}
    try:
        try:
            graph = build_graph(ctx)
            engine = "langgraph"
        except ImportError:
            graph, engine = None, "sequential"
        ctx.emit("planner", f"오케스트레이션: {engine}")
        if graph is not None:
            state = graph.invoke(state, {"recursion_limit": 25})
        else:
            state = _run_sequential(ctx, state)
    except Exception as e:  # noqa: BLE001
        state = {**state, "status": "error", "error": f"{type(e).__name__}: {e}"}
        (ctx.run_dir / "error.txt").write_text(traceback.format_exc(), encoding="utf-8")
        ctx.emit("error", f"분석 중 오류가 발생했습니다: {e}")
    summary = {"status": state.get("status"), "rounds": state.get("round"), "events": len(ctx.events)}
    (ctx.run_dir / "status.json").write_text(json.dumps(summary, ensure_ascii=False), encoding="utf-8")
    return state, ctx


def main() -> None:  # CLI: python -m agent.graph "질문" --place aewol --place hyeopjae --industry cafe --all
    import argparse

    ap = argparse.ArgumentParser(description="Jeju-AgenticX CLI")
    ap.add_argument("question")
    ap.add_argument("--place", action="append", default=[], help="places.yaml 의 장소 id (최대 3)")
    ap.add_argument("--industry")
    ap.add_argument("--conditions", choices=["season", "weekday", "weather", "tourism", "all"])
    ap.add_argument("--llm", default=None, help="auto|anthropic|ollama|rules")
    ap.add_argument("--name", default=None, help="실행 폴더 이름")
    a = ap.parse_args()
    from tools import geo

    cands = []
    for pid in a.place:
        p = geo.place_by_id(pid)
        if not p:
            raise SystemExit(f"알 수 없는 장소 id: {pid}")
        cands.append({"label": p.name, "lat": p.lat, "lon": p.lon, "place_id": p.id})
    req: dict[str, Any] = {"question": a.question, "candidates": cands, "industry": a.industry,
                           "answers": {"conditions": a.conditions} if a.conditions else {}}
    state, ctx = run_agent(req, llm_mode=a.llm, on_event=lambda e: print(f"[{e['stage']}] {e['message']}"), run_name=a.name)
    print("\n상태:", state.get("status"), "| 실행 폴더:", ctx.run_dir)
    if state.get("status") == "needs_user":
        cl = state["plan"]["clarification"]
        print("Agent 질문:", cl["question"], [o["label"] for o in cl["options"]])
    elif state.get("report"):
        print("\n".join("• " + s for s in state["report"]["summary"]))


if __name__ == "__main__":
    main()
