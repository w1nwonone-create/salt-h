# Jeju-AgenticX 생성 분석 코드 — tourism_dependency
# 재실행: python -m tools.replay <실행 폴더>
import json
PARAMS = json.loads("{\"candidates\": [{\"id\": \"c1\", \"label\": \"애월 해안도로(한담·애월리)\", \"grid\": \"G500_1779_2994\", \"grids_3x3\": [\"G500_1778_2993\", \"G500_1779_2993\", \"G500_1780_2993\", \"G500_1778_2994\", \"G500_1779_2994\", \"G500_1780_2994\", \"G500_1778_2995\", \"G500_1779_2995\", \"G500_1780_2995\"], \"bjd\": \"5011025321\", \"emd\": \"애월읍\", \"stops\": [\"406000107\", \"406000110\", \"406000133\"], \"station\": \"184\"}, {\"id\": \"c2\", \"label\": \"한림 협재(협재해수욕장)\", \"grid\": \"G500_1765_2979\", \"grids_3x3\": [\"G500_1764_2978\", \"G500_1765_2978\", \"G500_1766_2978\", \"G500_1764_2979\", \"G500_1765_2979\", \"G500_1766_2979\", \"G500_1764_2980\", \"G500_1765_2980\", \"G500_1766_2980\"], \"bjd\": \"5011025029\", \"emd\": \"한림읍\", \"stops\": [\"406000164\", \"406000169\", \"406000189\"], \"station\": \"185\"}], \"biz_cd\": [\"I56220\"], \"pos_names\": [\"커피전문점\"], \"months\": [\"202411\", \"202412\", \"202501\", \"202502\", \"202503\", \"202504\", \"202505\", \"202506\", \"202507\", \"202508\", \"202509\", \"202510\", \"202511\", \"202512\", \"202601\", \"202602\", \"202603\", \"202604\", \"202605\", \"202606\", \"202607\", \"202608\", \"202609\", \"202610\"], \"peak_months\": [7, 8], \"off_months\": [11, 12, 1, 2], \"matched_years\": false, \"min_use_cnt\": 5, \"min_pos_stores\": 3, \"rain_mm\": 1.0, \"min_days\": 10, \"date_from\": \"2024-11-01\", \"date_to\": \"2026-10-31\"}")

# 관광 의존도 — 카드 이용 현황(요일별)_v02 의 관광구분(개별·단체관광객·도민)
P = PARAMS
PEAK, OFF = set(P["peak_months"]), set(P["off_months"])
bjds = sorted({c["bjd"] for c in P["candidates"]})

df = con.execute(
    """
    SELECT bjd, base_year_month AS ym, tour_type, SUM(use_amt) AS amt, SUM(use_cnt) AS cnt
    FROM card_weekday_v02
    WHERE list_contains($bjd, bjd) AND list_contains($biz, biz_cd) AND list_contains($months, base_year_month)
    GROUP BY 1, 2, 3
    """,
    {"bjd": bjds, "biz": list(P["biz_cd"]), "months": list(P["months"])},
).df()
df["m"] = df["ym"].str[4:].astype(int)


def shares(d):
    tot = float(d["amt"].sum())
    if tot <= 0 or int(d["cnt"].sum()) < P.get("min_use_cnt", 5):
        return None
    by = d.groupby("tour_type")["amt"].sum()
    s = {k: float(by.get(k, 0.0)) / tot for k in ("도민", "개별관광객", "단체관광객")}
    s["관광객"] = s["개별관광객"] + s["단체관광객"]
    return s


out = {}
for b in bjds:
    d = df[df["bjd"] == b]
    all_s = shares(d)
    out[b] = {
        "shares": all_s,
        "tourist_share": all_s["관광객"] if all_s else None,
        "tourist_share_peak": (shares(d[d["m"].isin(PEAK)]) or {}).get("관광객"),
        "tourist_share_off": (shares(d[d["m"].isin(OFF)]) or {}).get("관광객"),
        "months_n": int(d["ym"].nunique()),
        "total_amt": float(d["amt"].sum()),
    }
RESULT = {"metric": "tourism", "by_bjd": out, "months": [P["months"][0], P["months"][-1]]}
