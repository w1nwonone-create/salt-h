# Jeju-AgenticX 생성 분석 코드 — weather_sensitivity
# 재실행: python -m tools.replay <실행 폴더>
import json
PARAMS = json.loads("{\"candidates\": [{\"id\": \"c1\", \"label\": \"애월 해안도로(한담·애월리)\", \"grid\": \"G500_1779_2994\", \"grids_3x3\": [\"G500_1778_2993\", \"G500_1779_2993\", \"G500_1780_2993\", \"G500_1778_2994\", \"G500_1779_2994\", \"G500_1780_2994\", \"G500_1778_2995\", \"G500_1779_2995\", \"G500_1780_2995\"], \"bjd\": \"5011025321\", \"emd\": \"애월읍\", \"stops\": [\"406000107\", \"406000110\", \"406000133\"], \"station\": \"184\"}, {\"id\": \"c2\", \"label\": \"한림 협재(협재해수욕장)\", \"grid\": \"G500_1765_2979\", \"grids_3x3\": [\"G500_1764_2978\", \"G500_1765_2978\", \"G500_1766_2978\", \"G500_1764_2979\", \"G500_1765_2979\", \"G500_1766_2979\", \"G500_1764_2980\", \"G500_1765_2980\", \"G500_1766_2980\"], \"bjd\": \"5011025029\", \"emd\": \"한림읍\", \"stops\": [\"406000164\", \"406000169\", \"406000189\"], \"station\": \"185\"}], \"biz_cd\": [\"I56220\"], \"pos_names\": [\"커피전문점\"], \"months\": [\"202411\", \"202412\", \"202501\", \"202502\", \"202503\", \"202504\", \"202505\", \"202506\", \"202507\", \"202508\", \"202509\", \"202510\", \"202511\", \"202512\", \"202601\", \"202602\", \"202603\", \"202604\", \"202605\", \"202606\", \"202607\", \"202608\", \"202609\", \"202610\"], \"peak_months\": [7, 8], \"off_months\": [11, 12, 1, 2], \"matched_years\": false, \"min_use_cnt\": 5, \"min_pos_stores\": 3, \"rain_mm\": 1.0, \"min_days\": 10, \"date_from\": \"2024-11-01\", \"date_to\": \"2026-10-31\"}")

# 날씨 민감도 — 내국인 유동인구(읍면동)_v02 방문인구 · 버스 정류소별 이용 현황 × 일일 날씨 정보
# 같은 달·같은 요일유형(평일/주말·공휴일) 안에서 우천일과 비우천일을 비교한 뒤 가중평균합니다
# (계절·요일 차이가 날씨 효과로 잘못 잡히는 것을 막기 위한 층화 비교).
import datetime as dt

import pandas as pd

P = PARAMS
RAIN = float(P.get("rain_mm", 1.0))
MIN_DAYS = int(P.get("min_days", 10))
hol = {r[0] for r in con.execute("SELECT holiday FROM ref_holiday").fetchall()}
start, end = P["date_from"], P["date_to"]


def stratified(daily, rain):
    """daily: DataFrame[d, v]; rain: DataFrame[d, r]"""
    df = daily.merge(rain, on="d", how="left")
    n_rain_missing = int(df["r"].isna().sum())
    df = df.dropna(subset=["r"]).copy()
    if df.empty:
        return None
    df["rainy"] = df["r"] >= RAIN
    df["dtype"] = df["d"].map(lambda x: "주말·공휴일" if (x.weekday() >= 5 or x in hol) else "평일")
    df["ym"] = df["d"].map(lambda x: f"{x.year}{x.month:02d}")
    num = den = 0.0
    strata = 0
    by_dtype = {}
    for (ym, t), g in df.groupby(["ym", "dtype"]):
        r, s = g[g["rainy"]], g[~g["rainy"]]
        if len(r) == 0 or len(s) == 0:
            continue
        eff = r["v"].mean() / s["v"].mean() - 1
        w = len(r)
        num += eff * w
        den += w
        strata += 1
        a = by_dtype.setdefault(t, [0.0, 0.0])
        a[0] += eff * w
        a[1] += w
    naive = df[df["rainy"]]["v"].mean() / df[~df["rainy"]]["v"].mean() - 1 if df["rainy"].any() and (~df["rainy"]).any() else None
    n_rain, n_dry = int(df["rainy"].sum()), int((~df["rainy"]).sum())
    return {
        "effect": (num / den) if den else None,
        "effect_naive": None if naive is None else float(naive),
        "by_daytype": {k: v[0] / v[1] for k, v in by_dtype.items() if v[1]},
        "rain_days": n_rain, "dry_days": n_dry, "strata": strata,
        "enough": n_rain >= MIN_DAYS and n_dry >= MIN_DAYS,
        "rain_missing_days": n_rain_missing,
        "date_from": str(df["d"].min()), "date_to": str(df["d"].max()),
        "rain_mean": float(df[df["rainy"]]["v"].mean()) if n_rain else None,
        "dry_mean": float(df[~df["rainy"]]["v"].mean()) if n_dry else None,
    }


out = {}
for c in P["candidates"]:
    rain = con.execute(
        "SELECT base_date AS d, daily_rainfall AS r FROM weather_daily WHERE observatory_code = $st AND base_date BETWEEN $a AND $b",
        {"st": c["station"], "a": start, "b": end},
    ).df()
    rain["d"] = pd.to_datetime(rain["d"]).dt.date
    res = {"station": c["station"], "emd": c["emd"]}

    pop = con.execute(
        """SELECT base_date AS d, resd, SUM(visit_pop_cnt) AS v FROM floating_pop_emd_v02
           WHERE emd_nm = $emd AND base_date BETWEEN $a AND $b GROUP BY 1, 2""",
        {"emd": c["emd"], "a": start, "b": end},
    ).df()
    if len(pop):
        pop["d"] = pd.to_datetime(pop["d"]).dt.date
        tot = pop.groupby("d", as_index=False)["v"].sum()
        first, last = min(tot["d"]), max(tot["d"])
        expected = (last - first).days + 1
        res["visit_pop"] = stratified(tot, rain)
        if res["visit_pop"]:
            res["visit_pop"]["missing_days"] = expected - len(tot)
            res["visit_pop"]["by_resd"] = {
                k: (stratified(pop[pop["resd"] == k][["d", "v"]], rain) or {}).get("effect") for k in ("제주", "그외")
            }
    else:
        res["visit_pop"] = None

    if c.get("stops"):
        bus = con.execute(
            """SELECT base_date AS d, SUM(user_count) AS v FROM bus_usage
               WHERE list_contains($stops, bus_station_id) AND base_date BETWEEN $a AND $b GROUP BY 1""",
            {"stops": list(c["stops"]), "a": start, "b": end},
        ).df()
        bus["d"] = pd.to_datetime(bus["d"]).dt.date
        res["bus"] = stratified(bus, rain) if len(bus) else None
        if res["bus"]:
            res["bus"]["stops_n"] = len(c["stops"])
    else:
        res["bus"] = None
    out[c["id"]] = res

RESULT = {"metric": "weather", "rain_mm": RAIN, "candidates": out, "period": [start, end]}
