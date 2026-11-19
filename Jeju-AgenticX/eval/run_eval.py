"""기준 질문 세트로 Agent 를 평가합니다 (규칙 기반 모드 — 결과가 결정적).

측정 항목
  - 계획 정확도: 후보지·업종·지표를 질문에서 정확히 읽었는가
  - 데이터 선택 정확도: Navigator 가 고른 데이터셋이 기대 데이터셋과 정확히 같은가
  - 수치 정확도: Agent 산출값이 독립 구현(build_reference.py)과 허용 오차 이내로 같은가

    python eval/run_eval.py [--llm rules]   →  eval/results.json, eval/results.md
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.graph import run_agent  # noqa: E402


def agent_values(state: dict) -> dict:
    nav, res = state["nav"], state["analysis"]["results"]
    out = {}
    for c in nav["candidates"]:
        t = c["tag"]
        if "season_stability" in res:
            r = res["season_stability"]
            out[f"{t}.season"] = r["candidates"][c["id"]]["card"]["ratio"]
            out[f"{t}.season_matched"] = r["matched_years"]
        if "tourism_dependency" in res:
            out[f"{t}.tourism"] = res["tourism_dependency"]["by_bjd"][c["bjd"]]["tourist_share"]
        if "weekday_stability" in res:
            out[f"{t}.weekday"] = res["weekday_stability"]["by_bjd"][c["bjd"]]["ratio"]
        if "weather_sensitivity" in res:
            out[f"{t}.weather"] = (res["weather_sensitivity"]["candidates"][c["id"]]["visit_pop"] or {}).get("effect")
        if "time_pattern" in res:
            tp = res["time_pattern"]["by_bjd"][c["bjd"]]
            out[f"{t}.time_slot"] = tp["peak_slot"]
            out[f"{t}.time_share"] = tp["shares"][tp["peak_slot"]]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--llm", default="rules")
    args = ap.parse_args()
    gold = json.loads((ROOT / "eval" / "golden_questions.json").read_text(encoding="utf-8"))
    tol = gold["tolerance"]
    tmp = Path(tempfile.mkdtemp(prefix="jax_eval_"))
    rows, tot = [], {"plan": 0, "data": 0, "num_ok": 0, "num_n": 0, "done": 0}
    for q in gold["questions"]:
        exp = q["expected"]
        state, ctx = run_agent({"question": q["question"]}, llm_mode=args.llm, runs_dir=tmp, run_name=q["id"])
        plan = state.get("plan", {})
        got_places = [c.get("place_id") for c in plan.get("candidates", [])]
        plan_ok = (got_places == exp["places"] and (plan.get("industry") or {}).get("key") == exp["industry"]
                   and plan.get("metrics") == exp["metrics"])
        done = state.get("status") == "done"
        data_ok = done and sorted(d["key"] for d in state["nav"]["datasets"]) == exp["datasets"]
        vals = agent_values(state) if done else {}
        num_ok = num_n = 0
        diffs = {}
        for k, v in exp["values"].items():
            num_n += 1
            a = vals.get(k)
            if isinstance(v, (bool, str)) or a is None:
                ok = a == v
            else:
                ok = abs(a - v) <= tol
            num_ok += ok
            diffs[k] = {"expected": v, "agent": a, "ok": ok}
        tot["plan"] += plan_ok
        tot["data"] += bool(data_ok)
        tot["num_ok"] += num_ok
        tot["num_n"] += num_n
        tot["done"] += done
        rows.append({"id": q["id"], "question": q["question"], "status": state.get("status"), "plan_ok": plan_ok,
                     "data_ok": bool(data_ok), "values": diffs,
                     "got": {"places": got_places, "industry": (plan.get("industry") or {}).get("key"), "metrics": plan.get("metrics")}})
        print(f"{q['id']} plan={'O' if plan_ok else 'X'} data={'O' if data_ok else 'X'} num={num_ok}/{num_n}  {q['question'][:40]}")
    n = len(gold["questions"])
    summary = {"questions": n, "completed": tot["done"], "plan_accuracy": tot["plan"] / n,
               "data_selection_accuracy": tot["data"] / n, "numeric_accuracy": tot["num_ok"] / max(1, tot["num_n"]),
               "numeric_checks": tot["num_n"], "tolerance": tol, "llm_mode": args.llm}
    (ROOT / "eval" / "results.json").write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=1),
                                                encoding="utf-8")
    md = ["# 기준 질문 세트 평가 결과", "",
          f"- 질문 수: {n} (분석 완료 {tot['done']})",
          f"- 계획 정확도(후보지·업종·지표): **{summary['plan_accuracy']:.0%}**",
          f"- 데이터 선택 정확도: **{summary['data_selection_accuracy']:.0%}**",
          f"- 수치 정확도(허용 오차 ±{tol}): **{summary['numeric_accuracy']:.0%}** ({tot['num_ok']}/{tot['num_n']})",
          f"- 분석 엔진: {args.llm}", "", "| ID | 질문 | 계획 | 데이터 | 수치 |", "|---|---|---|---|---|"]
    for r in rows:
        ok = sum(v["ok"] for v in r["values"].values())
        md.append(f"| {r['id']} | {r['question']} | {'O' if r['plan_ok'] else 'X'} | {'O' if r['data_ok'] else 'X'} | {ok}/{len(r['values'])} |")
    (ROOT / "eval" / "results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
