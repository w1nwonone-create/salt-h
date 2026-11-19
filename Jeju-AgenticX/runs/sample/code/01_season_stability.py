# Jeju-AgenticX 생성 분석 코드 — season_stability
# 재실행: python -m tools.replay <실행 폴더>
import json
PARAMS = json.loads("{\"candidates\": [{\"id\": \"c1\", \"label\": \"애월 해안도로(한담·애월리)\", \"grid\": \"G500_1779_2994\", \"grids_3x3\": [\"G500_1778_2993\", \"G500_1779_2993\", \"G500_1780_2993\", \"G500_1778_2994\", \"G500_1779_2994\", \"G500_1780_2994\", \"G500_1778_2995\", \"G500_1779_2995\", \"G500_1780_2995\"], \"bjd\": \"5011025321\", \"emd\": \"애월읍\", \"stops\": [\"406000107\", \"406000110\", \"406000133\"], \"station\": \"184\"}, {\"id\": \"c2\", \"label\": \"한림 협재(협재해수욕장)\", \"grid\": \"G500_1765_2979\", \"grids_3x3\": [\"G500_1764_2978\", \"G500_1765_2978\", \"G500_1766_2978\", \"G500_1764_2979\", \"G500_1765_2979\", \"G500_1766_2979\", \"G500_1764_2980\", \"G500_1765_2980\", \"G500_1766_2980\"], \"bjd\": \"5011025029\", \"emd\": \"한림읍\", \"stops\": [\"406000164\", \"406000169\", \"406000189\"], \"station\": \"185\"}], \"biz_cd\": [\"I56220\"], \"pos_names\": [\"커피전문점\"], \"months\": [\"202411\", \"202412\", \"202501\", \"202502\", \"202503\", \"202504\", \"202505\", \"202506\", \"202507\", \"202508\", \"202509\", \"202510\", \"202511\", \"202512\", \"202601\", \"202602\", \"202603\", \"202604\", \"202605\", \"202606\", \"202607\", \"202608\", \"202609\", \"202610\"], \"peak_months\": [7, 8], \"off_months\": [11, 12, 1, 2], \"matched_years\": false, \"min_use_cnt\": 5, \"min_pos_stores\": 3, \"rain_mm\": 1.0, \"min_days\": 10, \"date_from\": \"2024-11-01\", \"date_to\": \"2026-10-31\"}")

# 시즌 안정성 · 소비 규모 — 카드 이용 현황(500m격자), 외식업 포스 이용 현황(500m격자)
# 지표: 비수기 월평균 / 성수기 월평균 (같은 격자, 같은 업종)
import math

P = PARAMS
MONTHS = list(P["months"])
PEAK = set(P["peak_months"])
OFF = set(P["off_months"])
MIN_CNT = P.get("min_use_cnt", 5)
MIN_STORES = P.get("min_pos_stores", 3)
MATCHED = bool(P.get("matched_years", False))


def month_of(ym):
    return int(ym[4:])


def season_year(ym):
    """비수기(11~2월)는 직전 여름과 같은 '시즌연도'로 묶습니다. 예) 2025-12, 2026-01 → 2025."""
    y, m = int(ym[:4]), int(ym[4:])
    return y - 1 if (m in OFF and m < min(PEAK)) else y


def complete_season_years():
    have = set(MONTHS)
    out = []
    for sy in sorted({season_year(ym) for ym in MONTHS}):
        peak = [f"{sy}{m:02d}" for m in sorted(PEAK)]
        off = [f"{sy + (1 if m < min(PEAK) else 0)}{m:02d}" for m in sorted(OFF)]
        if all(x in have for x in peak + off):
            out.append(sy)
    return out


USE_SY = complete_season_years() if MATCHED else None


def clean(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else x


def summarize(series, kind):
    """series: {ym: value or None}"""
    peak = [(ym, v) for ym, v in series.items() if month_of(ym) in PEAK and (USE_SY is None or season_year(ym) in USE_SY)]
    off = [(ym, v) for ym, v in series.items() if month_of(ym) in OFF and (USE_SY is None or season_year(ym) in USE_SY)]
    pv = [v for _, v in peak if v is not None]
    ov = [v for _, v in off if v is not None]
    peak_mean = sum(pv) / len(pv) if pv else None
    off_mean = sum(ov) / len(ov) if ov else None
    by_peak_year, by_off_sy = {}, {}
    for ym, v in series.items():
        if v is None:
            continue
        if month_of(ym) in PEAK:
            by_peak_year.setdefault(str(season_year(ym)), []).append(v)
        elif month_of(ym) in OFF:
            by_off_sy.setdefault(str(season_year(ym)), []).append(v)
    by_peak_year = {k: sum(v) / len(v) for k, v in by_peak_year.items()}
    by_off_sy = {k: sum(v) / len(v) for k, v in by_off_sy.items()}
    ratio_sy = {k: by_off_sy[k] / by_peak_year[k] for k in by_peak_year if k in by_off_sy and by_peak_year[k]}
    recent = [v for ym, v in sorted(series.items())[-12:] if v is not None]
    return {
        "kind": kind,
        "peak_mean": peak_mean, "off_mean": off_mean,
        "ratio": (off_mean / peak_mean) if (peak_mean and off_mean is not None) else None,
        "peak_months_n": len(pv), "off_months_n": len(ov),
        "peak_months_used": [ym for ym, v in peak if v is not None],
        "off_months_used": [ym for ym, v in off if v is not None],
        "peak_by_year": by_peak_year, "off_by_season_year": by_off_sy, "ratio_by_season_year": ratio_sy,
        "avg_monthly_recent12": (sum(recent) / len(recent)) if recent else None,
        "missing_months": [ym for ym in MONTHS if ym not in series or series[ym] is None],
    }


all_grids = sorted({g for c in P["candidates"] for g in [c["grid"], *c["grids_3x3"]]})
card = con.execute(
    """
    SELECT base_year_month AS ym, grid_500m AS grid, SUM(use_amt) AS amt, SUM(use_cnt) AS cnt
    FROM card_grid_500m
    WHERE list_contains($grids, grid_500m) AND list_contains($biz, biz_cd) AND list_contains($months, base_year_month)
    GROUP BY 1, 2
    """,
    {"grids": all_grids, "biz": list(P["biz_cd"]), "months": MONTHS},
).df()

pos = None
if P.get("pos_names"):
    pos = con.execute(
        """
        SELECT base_year_month AS ym, grid_500 AS grid, SUM(sale_amt) AS amt, SUM(store_cnt) AS stores
        FROM pos_grid_500m
        WHERE list_contains($grids, grid_500) AND list_contains($names, biz_small_nm) AND list_contains($months, base_year_month)
        GROUP BY 1, 2
        """,
        {"grids": all_grids, "names": list(P["pos_names"]), "months": MONTHS},
    ).df()

out = {}
for c in P["candidates"]:
    main = card[card["grid"] == c["grid"]]
    masked = sorted(main.loc[main["cnt"] < MIN_CNT, "ym"].tolist())
    s_main = {r.ym: (float(r.amt) if r.cnt >= MIN_CNT else None) for r in main.itertuples()}
    s_main = {ym: s_main.get(ym) for ym in MONTHS}
    sub = card[card["grid"].isin(c["grids_3x3"])].groupby("ym", as_index=False)[["amt", "cnt"]].sum()
    s_3 = {r.ym: (float(r.amt) if r.cnt >= MIN_CNT else None) for r in sub.itertuples()}
    s_3 = {ym: s_3.get(ym) for ym in MONTHS}
    res = {
        "card": summarize(s_main, "card_main"),
        "card_3x3": summarize(s_3, "card_3x3"),
        "monthly": [{"ym": ym, "card_amt": clean(s_main[ym]), "card_amt_3x3": clean(s_3[ym])} for ym in MONTHS],
        "masked_months": masked,
    }
    res["card"]["total_cnt"] = int(main["cnt"].sum())
    if pos is not None:
        pm = pos[pos["grid"] == c["grid"]]
        stores = float(pm["stores"].mean()) if len(pm) else 0.0
        s_pos = {r.ym: float(r.amt) for r in pm.itertuples()}
        s_pos = {ym: s_pos.get(ym) for ym in MONTHS}
        ps = summarize(s_pos, "pos_main")
        ps["store_cnt_avg"] = stores
        ps["suppressed"] = stores < MIN_STORES
        if ps["suppressed"]:
            for k in ("peak_mean", "off_mean", "ratio", "avg_monthly_recent12"):
                ps[k] = None
            ps["peak_by_year"], ps["off_by_season_year"], ps["ratio_by_season_year"] = {}, {}, {}
        else:
            for row in res["monthly"]:
                row["pos_amt"] = clean(s_pos[row["ym"]])
        res["pos"] = ps
    out[c["id"]] = res

RESULT = {
    "metric": "season",
    "matched_years": MATCHED,
    "season_years_used": USE_SY,
    "months": [MONTHS[0], MONTHS[-1]],
    "peak_months": sorted(PEAK), "off_months": sorted(OFF),
    "candidates": out,
}
