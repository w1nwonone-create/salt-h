# 시간대 패턴 — 카드 이용 현황(시간대)_v02 (법정동 단위)
P = PARAMS
TIMES = ["오전", "점심", "오후", "저녁", "밤"]
bjds = sorted({c["bjd"] for c in P["candidates"]})
df = con.execute(
    """
    SELECT bjd, time, CASE WHEN tour_type = '도민' THEN '도민' ELSE '관광객' END AS grp, SUM(use_amt) AS amt
    FROM card_time_v02
    WHERE list_contains($bjd, bjd) AND list_contains($biz, biz_cd) AND list_contains($months, base_year_month)
    GROUP BY 1, 2, 3
    """,
    {"bjd": bjds, "biz": list(P["biz_cd"]), "months": list(P["months"])},
).df()
out = {}
for b in bjds:
    d = df[df["bjd"] == b]
    tot = float(d["amt"].sum())
    by = d.groupby("time")["amt"].sum()
    shares = {t: (float(by.get(t, 0.0)) / tot if tot else None) for t in TIMES}
    grp = {}
    for g, gd in d.groupby("grp"):
        gt = float(gd["amt"].sum())
        gb = gd.groupby("time")["amt"].sum()
        grp[g] = {t: float(gb.get(t, 0.0)) / gt for t in TIMES} if gt else None
    peak = max(shares, key=lambda t: shares[t] or 0) if tot else None
    out[b] = {"shares": shares, "by_group": grp, "peak_slot": peak}
RESULT = {"metric": "time", "by_bjd": out}
