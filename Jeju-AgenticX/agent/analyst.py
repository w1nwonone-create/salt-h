"""③ Analyst — 분석 코드를 생성해 샌드박스에서 실행하고, 오류가 나면 스스로 고칩니다.

* 표준 지표: 검증된 템플릿(analysis_templates/)에 분석 계획·위치 연결 결과를 채워 코드를 생성
* 자유 질문: LLM 이 스키마(컬럼 구조)만 보고 코드를 작성 → 실행 → 오류 시 최대 3회 수정
생성·실행된 코드는 모두 runs/<실행>/code/ 에 단독 재실행 가능한 형태로 저장됩니다.
"""
from __future__ import annotations

import json

import config
from agent.context import RunContext
from agent.llm import extract_code, load_prompt
from tools.catalog import load_catalog, schema_text
from tools.sandbox import run_python, validate

METRIC_TEMPLATE = {m: spec["template"] for m, spec in load_catalog()["metrics"].items()}


def build_params(plan: dict, nav: dict, options: dict) -> dict:
    ind = plan["industry"]
    return {
        "candidates": [{"id": c["id"], "label": c["label"], "grid": c["grid"], "grids_3x3": c["grids_3x3"],
                        "bjd": c["bjd"], "emd": c["emd"], "stops": [s["id"] for s in c["stops"]],
                        "station": c["station"]["code"]} for c in nav["candidates"]],
        "biz_cd": ind["biz_cd"] if ind else [],
        "pos_names": ind["pos"] if ind else [],
        "months": nav["months"],
        "peak_months": plan["peak_months"], "off_months": plan["off_months"],
        "matched_years": bool(options.get("matched_years")),
        "min_use_cnt": config.MIN_USE_CNT, "min_pos_stores": config.MIN_POS_STORES,
        "rain_mm": plan["rain_mm"], "min_days": config.MIN_DAYS_PER_GROUP,
        "date_from": nav.get("date_from"), "date_to": nav.get("date_to"),
    }


def render_code(template: str, params: dict, note: str = "") -> str:
    body = (config.TEMPLATE_DIR / f"{template}.py").read_text(encoding="utf-8")
    header = (
        f"# Jeju-AgenticX 생성 분석 코드 — {template}{(' / ' + note) if note else ''}\n"
        "# 재실행: python -m tools.replay <실행 폴더>\n"
        "import json\n"
        f"PARAMS = json.loads({json.dumps(json.dumps(params, ensure_ascii=False), ensure_ascii=False)})\n\n"
    )
    return header + body


def _save(ctx: RunContext, name: str, code: str) -> str:
    path = ctx.run_dir / "code" / f"{name}.py"
    path.write_text(code, encoding="utf-8")
    return str(path.relative_to(ctx.run_dir))


def _repair(ctx: RunContext, code: str, error: str, goal: str) -> str | None:
    if not ctx.llm.available:
        return None
    user = (f"## 목표\n{goal}\n\n## 사용 가능한 테이블\n{schema_text(list(load_catalog()['datasets']))}\n\n"
            f"## 실행한 코드\n```python\n{code}\n```\n\n## 오류\n```\n{error[-2000:]}\n```")
    try:
        return extract_code(ctx.llm.chat(load_prompt("analyst_fix"), user, purpose="analyst.fix", max_tokens=4000))
    except Exception:  # noqa: BLE001
        return None


def execute(ctx: RunContext, name: str, code: str, goal: str) -> dict:
    """실행 + 자가 수정 루프 (최대 MAX_CODE_FIX 회)."""
    attempts = []
    for i in range(config.MAX_CODE_FIX + 1):
        fname = name if i == 0 else f"{name}_fix{i}"
        rel = _save(ctx, fname, code)
        rr = run_python(code, params={}, db_path=ctx.db_path, workdir=ctx.run_dir)
        attempts.append({"file": rel, "ok": rr.ok, "seconds": round(rr.seconds, 2), "error": rr.error[-800:]})
        if rr.ok:
            ctx.emit("analyst", f"{name} 실행 완료 ({rr.seconds:.1f}초)", file=rel)
            return {"ok": True, "result": rr.result, "code_file": rel, "attempts": attempts}
        ctx.emit("analyst", f"{name} 실행 오류 — {'코드를 수정합니다' if i < config.MAX_CODE_FIX and ctx.llm.available else '중단'}",
                 error=rr.error[-300:])
        if i == config.MAX_CODE_FIX:
            break
        fixed = _repair(ctx, code, rr.error, goal)
        if not fixed:
            break
        code = fixed
    return {"ok": False, "result": None, "code_file": attempts[-1]["file"], "attempts": attempts,
            "error": attempts[-1]["error"]}


def analyze(ctx: RunContext, plan: dict, nav: dict, options: dict | None = None, previous: dict | None = None) -> dict:
    options = options or {}
    rerun = set(options.get("rerun", []))
    results = dict((previous or {}).get("results", {}))
    runs = dict((previous or {}).get("runs", {}))
    params = build_params(plan, nav, options)

    templates = []
    for m in nav["metrics"]:
        t = METRIC_TEMPLATE[m]
        if t not in templates:
            templates.append(t)
    for t in templates:
        if previous and t in results and t not in rerun:
            continue
        note = "동일 연도 비교(재분석)" if (t in rerun and params["matched_years"]) else ""
        name = f"{len(runs) + 1:02d}_{t}"
        out = execute(ctx, name, render_code(t, params, note), goal=f"{t} 지표 산출")
        runs[t] = {k: v for k, v in out.items() if k != "result"}
        if out["ok"]:
            results[t] = out["result"]
        else:
            results.pop(t, None)

    if plan.get("custom_request") and "custom" not in results:
        out = _custom(ctx, plan, nav)
        runs["custom"] = {k: v for k, v in out.items() if k not in ("result",)}
        if out["ok"]:
            results["custom"] = out["result"]

    return {"params": params, "results": results, "runs": runs, "options": options}


def _custom(ctx: RunContext, plan: dict, nav: dict) -> dict:
    """템플릿이 없는 질문: LLM 이 코드 작성 → 샌드박스 실행 → 오류 시 자가 수정."""
    if not ctx.llm.available:
        return {"ok": False, "error": "LLM 미연결 — 자유 질문 분석 불가", "attempts": []}
    keys = [d["key"] for d in nav["datasets"]] or list(load_catalog()["datasets"])
    cands = [{k: c[k] for k in ("tag", "label", "grid", "bjd", "emd")} | {"stops": [s["id"] for s in c["stops"]],
             "station": c["station"]["code"]} for c in nav["candidates"]]
    user = (f"## 분석 요청\n{plan['custom_request']}\n\n## 후보지(위치 연결 결과)\n{json.dumps(cands, ensure_ascii=False)}\n\n"
            f"## 업종\n{json.dumps(plan.get('industry'), ensure_ascii=False)}\n\n## 분석 기간(월)\n{nav['months'][:1]} ~ {nav['months'][-1:]}\n\n"
            f"## 사용 가능한 테이블(컬럼 구조만)\n{schema_text(keys)}")
    try:
        code = extract_code(ctx.llm.chat(load_prompt("analyst_codegen"), user, purpose="analyst.codegen", max_tokens=4000))
        validate(code)
    except Exception as e:  # noqa: BLE001
        code = f"# 생성 실패: {e}\nRESULT = None\n"
    return execute(ctx, f"{90:02d}_custom", code, goal=plan["custom_request"])
