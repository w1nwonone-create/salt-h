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
