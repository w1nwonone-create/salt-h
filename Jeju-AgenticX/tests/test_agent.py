import json

from agent import analyst, planner, reporter
from agent.context import RunContext
from agent.graph import run_agent
from tests.conftest import FakeLLM
from tools.checks import verify_numbers

Q = "애월 해안도로와 한림 협재 쪽 중에서, 카페를 하기에 비수기에 덜 흔들리는 곳은 어디일까요?"


def test_rules_end_to_end(tmp_path):
    state, ctx = run_agent({"question": Q}, llm_mode="rules", runs_dir=tmp_path, run_name="t")
    assert state["status"] == "done"
    rep = state["report"]
    assert any("56%" in s and "41%" in s for s in rep["summary"])
    for f in ("plan.json", "navigation.json", "results.json", "report.html", "data_version.json", "log.jsonl"):
        assert (ctx.run_dir / f).exists()


def test_clarification_when_conditions_missing(tmp_path):
    req = {"question": "후보지 비교하기", "candidates": [{"place_id": "aewol"}, {"place_id": "hyeopjae"}], "industry": "cafe"}
    state, _ = run_agent(req, llm_mode="rules", runs_dir=tmp_path, run_name="c")
    assert state["status"] == "needs_user"
    assert state["plan"]["clarification"]["type"] == "conditions"
    req["answers"] = {"conditions": "all"}
    state, _ = run_agent(req, llm_mode="rules", runs_dir=tmp_path, run_name="c2")
    assert state["status"] == "done"
    assert state["plan"]["metrics"] == ["scale", "season", "tourism", "weekday", "weather"]


def test_year_effect_triggers_reanalysis(tmp_path):
    state, ctx = run_agent({"question": "월정리 카페는 겨울에 얼마나 줄어드나요?"}, llm_mode="rules", runs_dir=tmp_path, run_name="y")
    assert state["status"] == "done" and state["round"] == 2
    assert state["analysis"]["results"]["season_stability"]["matched_years"] is True
    assert (ctx.run_dir / "critic_round0.json").exists()
    first = json.loads((ctx.run_dir / "critic_round0.json").read_text(encoding="utf-8"))
    assert first["verdict"] == "reanalyze"


def test_out_of_scope_note(tmp_path):
    ctx = RunContext.create("x", "rules", runs_dir=tmp_path)
    p = planner.plan(ctx, {"question": "협재 카페 매출 예측해 주세요. 비수기엔 어때요?"})
    assert any("매출 예측" in n for n in p["notes"])


def test_llm_plan_hallucination_ignored(tmp_path):
    ctx = RunContext.create("x", "rules", runs_dir=tmp_path)
    ctx.llm = FakeLLM({"planner": '{"places": ["nowhere"], "industry": "spaceship", "metrics": ["season", "magic"]}'})
    p = planner.plan(ctx, {"question": "함덕에서 카페 하면?"})
    assert p["industry"]["key"] == "cafe" and p["metrics"] == ["scale", "season"]
    assert [c["place_id"] for c in p["candidates"]] == ["hamdeok"]


def test_reporter_rejects_llm_numbers(tmp_path):
    state, ctx = run_agent({"question": Q}, llm_mode="rules", runs_dir=tmp_path, run_name="r")
    bad = '{"summary": ["비수기에 A는 성수기의 61% 수준입니다."], "consult": []}'
    ctx.llm = FakeLLM({"reporter.polish": bad})
    rep = reporter.build(ctx, state["plan"], state["nav"], state["analysis"], state["critic"])
    assert rep["summary_source"] == "deterministic" and "61" in rep["verify_log"]
    good = json.dumps({"summary": ["비수기(11~2월)에 A는 성수기의 56%, B는 41% 수준입니다."], "consult": []}, ensure_ascii=False)
    ctx.llm = FakeLLM({"reporter.polish": good})
    rep = reporter.build(ctx, state["plan"], state["nav"], state["analysis"], state["critic"])
    assert rep["summary_source"] == "llm_verified"


def test_reporter_rejects_recommendation(tmp_path):
    state, ctx = run_agent({"question": Q}, llm_mode="rules", runs_dir=tmp_path, run_name="r2")
    ctx.llm = FakeLLM({"reporter.polish": '{"summary": ["A를 추천합니다."], "consult": []}'})
    rep = reporter.build(ctx, state["plan"], state["nav"], state["analysis"], state["critic"])
    assert rep["summary_source"] == "deterministic"


def test_analyst_self_repair(tmp_path):
    ctx = RunContext.create("x", "rules", runs_dir=tmp_path)
    fixed = "```python\nRESULT = {'n': int(con.execute('SELECT COUNT(*) FROM weather_station').fetchone()[0])}\n```"
    ctx.llm = FakeLLM({"analyst.fix": fixed})
    out = analyst.execute(ctx, "01_broken", "RESULT = {'n': con.execute('SELECT COUNT(*) FROM no_such_table').fetchone()[0]}", "관측소 수")
    assert out["ok"] and out["result"] == {"n": 4} and len(out["attempts"]) == 2


def test_verify_numbers():
    assert verify_numbers("A 56%, B 1,705만원", {"56", "1705"}) == []
    assert verify_numbers("A 57%", {"56"}) == ["57"]
