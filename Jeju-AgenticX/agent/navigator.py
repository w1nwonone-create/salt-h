"""② Navigator — 위치를 데이터 단위로 연결하고, 필요한 데이터만 정확히 선택합니다.

Tools: point_to_grid, point_to_bjd, nearby_stops, nearest_station, catalog_search, schema_peek
"""
from __future__ import annotations

from agent.context import RunContext
from agent.llm import load_prompt
from tools import db, geo
from tools.catalog import catalog_search, load_catalog, schema_peek


def _ym_list(last_ym: str, n: int, first_ym: str) -> list[str]:
    y, m = int(last_ym[:4]), int(last_ym[4:])
    out = []
    for _ in range(n):
        ym = f"{y}{m:02d}"
        if ym < first_ym:
            break
        out.append(ym)
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return sorted(out)


def link_location(c: dict, stations: list[dict], wstations: list[dict]) -> dict:
    g = geo.point_to_grid(c["lat"], c["lon"])
    if c.get("place_id"):
        p = geo.place_by_id(c["place_id"])
        b = {"bjd": p.bjd, "bjd_nm": p.bjd_nm, "emd": p.emd, "sgg": p.sgg, "place_id": p.id,
             "distance_m": round(geo.haversine_m(c["lat"], c["lon"], p.lat, p.lon)), "method": "selected",
             "far_from_reference": False}
    else:
        b = geo.point_to_bjd(c["lat"], c["lon"])
    stops = geo.nearby_stops(c["lat"], c["lon"], stations)
    ws = geo.nearest_station(c["lat"], c["lon"], wstations)
    return {
        **c,
        "grid": g["grid"], "grids_3x3": g["grids_3x3"], "edge_distance_m": g["edge_distance_m"],
        "near_boundary": g["near_boundary"], "boundary_neighbors": g["boundary_neighbors"],
        "bjd": b["bjd"], "bjd_nm": b["bjd_nm"], "emd": b["emd"], "sgg": b["sgg"],
        "bjd_method": b["method"], "bjd_distance_m": b["distance_m"], "far_from_reference": b["far_from_reference"],
        "stops": [{"id": s["bus_station_id"], "name": s["bus_station_nm"], "distance_m": s["distance_m"],
                   "lat": float(s["latitude"]), "lon": float(s["longitude"])} for s in stops["stops"]],
        "stop_radius_m": stops["radius_m"], "stop_radius_expanded": stops["expanded"],
        "station": {"code": ws["observatory_code"], "name": ws["observatory_nm"], "distance_m": ws["distance_m"]},
    }


def navigate(ctx: RunContext, plan: dict) -> dict:
    warnings, unavailable = [], {}

    # 1) 위치 연결 ----------------------------------------------------------------
    stations = db.duckdb_query("SELECT * FROM bus_station", db_path=ctx.db_path).to_dict("records")
    wstations = db.duckdb_query("SELECT * FROM weather_station", db_path=ctx.db_path).to_dict("records")
    letters = "ABC"
    cands = []
    for i, c in enumerate(plan["candidates"]):
        linked = link_location(c, stations, wstations)
        linked["id"] = f"c{i + 1}"
        linked["tag"] = letters[i]
        cands.append(linked)
        ctx.emit("navigator", f"{letters[i]} {linked['label']} → 격자 {linked['grid']} · {linked['bjd_nm']} · "
                 f"정류소 {len(linked['stops'])}곳 · 관측소 {linked['station']['name']}")
        if linked["far_from_reference"]:
            warnings.append(f"{linked['label']}: 기준 법정동 중심에서 {linked['bjd_distance_m']:,}m 떨어져 있어 "
                            "법정동 연결이 부정확할 수 있습니다.")

    def _same(key):
        seen = {}
        for c in cands:
            seen.setdefault(c[key], []).append(c["tag"])
        return [v for v in seen.values() if len(v) > 1]

    same_grid, same_bjd, same_emd = _same("grid"), _same("bjd"), _same("emd")

    # 2) 데이터 선택 ----------------------------------------------------------------
    metrics = plan["metrics"]
    found = catalog_search(plan["question"], metrics=metrics)
    selected = [d for d in found if d["for_metrics"]]
    if plan.get("custom_request"):
        selected = _llm_select(ctx, plan) or found[:4]
    peeks = {}
    for d in selected:
        pk = schema_peek(d["key"], include_samples=False, db_path=ctx.db_path)
        peeks[d["key"]] = pk
        if not pk["exists"] or pk["missing_columns"]:
            for m in d["for_metrics"]:
                unavailable[m] = f"{d['name']} 데이터가 없거나 명세와 컬럼이 다릅니다({', '.join(pk['missing_columns'][:3])})."
    metrics_ok = [m for m in metrics if m not in unavailable]

    # 3) 분석 기간 ----------------------------------------------------------------
    months, date_from, date_to = [], None, None
    if "card_grid_500m" in peeks and peeks["card_grid_500m"].get("period"):
        per = peeks["card_grid_500m"]["period"]
        months = _ym_list(per["to"], plan["period"]["months"], per["from"])
    else:
        rng = db.duckdb_query("SELECT MIN(base_year_month) a, MAX(base_year_month) b FROM card_weekday_v02",
                              db_path=ctx.db_path).iloc[0]
        months = _ym_list(str(rng.b), plan["period"]["months"], str(rng.a))
    if "weather" in metrics_ok:
        fp = peeks.get("floating_pop_emd_v02", {}).get("period") or {}
        wd = peeks.get("weather_daily", {}).get("period") or {}
        bus = peeks.get("bus_usage", {}).get("period") or {}
        ends = [x for x in (wd.get("to"), bus.get("to"), fp.get("to")) if x]
        date_to = min(ends) if ends else None
        if date_to and months:
            date_from = max(f"{months[0][:4]}-{months[0][4:]}-01", wd.get("from", "0000"))
        avail = load_catalog()["datasets"]["floating_pop_emd_v02"].get("available_from")
        if avail:
            warnings.append(f"내국인 유동인구(읍면동)_v02 는 {avail[:4]}년 {int(avail[5:7])}월부터 제공되어, "
                            "방문인구 기준 날씨 비교 기간은 그 이후로 한정됩니다.")

    nav = {
        "candidates": cands,
        "datasets": [{"key": d["key"], "name": d["name"], "grain": d["grain"], "export": d["export"],
                      "for_metrics": d["for_metrics"], "period": peeks.get(d["key"], {}).get("period"),
                      "rows": peeks.get(d["key"], {}).get("rows")} for d in selected],
        "metrics": metrics_ok,
        "unavailable": unavailable,
        "months": months,
        "date_from": date_from, "date_to": date_to,
        "same_grid": same_grid, "same_bjd": same_bjd, "same_emd": same_emd,
        "warnings": warnings,
    }
    ctx.emit("navigator", "활용 데이터: " + ", ".join(d["name"] for d in nav["datasets"]),
             datasets=[d["name"] for d in nav["datasets"]])
    return nav


def _llm_select(ctx: RunContext, plan: dict) -> list[dict] | None:
    """자유 질문용: LLM 이 카탈로그에서 데이터셋을 고릅니다(목록 밖 값은 무시)."""
    if not ctx.llm.available:
        return None
    cat = load_catalog()["datasets"]
    listing = "\n".join(f"- {k}: {v['name']} ({v['grain']}) 태그: {', '.join(v.get('tags', []))}" for k, v in cat.items())
    try:
        res = ctx.llm.json(load_prompt("navigator"), f"## 질문\n{plan['custom_request']}\n\n## 데이터 목록\n{listing}",
                           purpose="navigator.select")
    except Exception:  # noqa: BLE001
        return None
    keys = [k for k in res.get("datasets", []) if k in cat]
    return [{"key": k, "name": cat[k]["name"], "grain": cat[k]["grain"], "export": cat[k]["export"],
             "for_metrics": ["custom"], "score": 1} for k in keys] or None
