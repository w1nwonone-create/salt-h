# 평일 안정성 — 카드 이용 현황(요일별)_v02
# 월 단위 요일별 합계를 그 달의 해당 요일 일수로 나눠 '하루 평균'으로 비교합니다.
import calendar
import datetime as dt

P = PARAMS
PEAK, OFF = set(P["peak_months"]), set(P["off_months"])
WEEK = ["월", "화", "수", "목", "금", "토", "일", "공휴일"]
WEEKDAY, WEEKEND = ["월", "화", "수", "목", "금"], ["토", "일", "공휴일"]
hol = {r[0] for r in con.execute("SELECT holiday FROM ref_holiday").fetchall()}


def day_counts(ym):
    y, m = int(ym[:4]), int(ym[4:])
    c = {w: 0 for w in WEEK}
    for i in range(1, calendar.monthrange(y, m)[1] + 1):
        d = dt.date(y, m, i)
        c["공휴일" if d in hol else WEEK[d.weekday()]] += 1
    return c


bjds = sorted({c["bjd"] for c in P["candidates"]})
df = con.execute(
    """
    SELECT bjd, base_year_month AS ym, week, SUM(use_amt) AS amt, SUM(use_cnt) AS cnt
    FROM card_weekday_v02
    WHERE list_contains($bjd, bjd) AND list_contains($biz, biz_cd) AND list_contains($months, base_year_month)
    GROUP BY 1, 2, 3
    """,
    {"bjd": bjds, "biz": list(P["biz_cd"]), "months": list(P["months"])},
).df()

counts = {ym: day_counts(ym) for ym in P["months"]}


def per_day(d, cats):
    amt = float(d[d["week"].isin(cats)]["amt"].sum())
    n = sum(counts[ym][w] for ym in d["ym"].unique() for w in cats)
    return (amt / n if n else None), n


out = {}
for b in bjds:
    d = df[df["bjd"] == b]
    m = d["ym"].str[4:].astype(int)
    wd, n_wd = per_day(d, WEEKDAY)
    we, n_we = per_day(d, WEEKEND)
    off_wd, n_off_wd = per_day(d[m.isin(OFF)], WEEKDAY)
    peak_we, n_peak_we = per_day(d[m.isin(PEAK)], WEEKEND)
    off_we, _ = per_day(d[m.isin(OFF)], WEEKEND)
    by_week = {w: per_day(d, [w])[0] for w in WEEK}
    out[b] = {
        "weekday_per_day": wd, "weekend_per_day": we, "weekday_days": n_wd, "weekend_days": n_we,
        "ratio": (wd / we) if (wd is not None and we) else None,
        "off_weekday_per_day": off_wd, "peak_weekend_per_day": peak_we, "off_weekday_days": n_off_wd,
        "off_weekday_vs_peak_weekend": (off_wd / peak_we) if (off_wd is not None and peak_we) else None,
        "off_ratio": (off_wd / off_we) if (off_wd is not None and off_we) else None,
        "by_week_per_day": by_week,
        "months_n": int(d["ym"].nunique()),
        "total_cnt": int(d["cnt"].sum()),
    }
RESULT = {"metric": "weekday", "by_bjd": out, "months": [P["months"][0], P["months"][-1]]}
