"""기준 질문 세트의 '정답'을 Agent 코드와 독립적으로 계산합니다.

Agent 의 분석 템플릿(analysis_templates/)을 쓰지 않고, 테이블 전체를 pandas 로 읽어
지표 정의(README §지표 정의)대로 별도 구현한 코드로 계산합니다. 두 구현이 같은 값을 내면
Agent 의 데이터 선택과 수치 계산이 정확하다고 판단합니다.

    python eval/build_reference.py   →  eval/golden_questions.json
"""
from __future__ import annotations

import calendar
import datetime as dt
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import config  # noqa: E402
from tools import db, geo  # noqa: E402

QUESTIONS = [
    ("애월 해안도로와 한림 협재 쪽 중에서, 카페를 하기에 비수기에 덜 흔들리는 곳은 어디일까요?", ["aewol", "hyeopjae"], "cafe", ["season"]),
    ("함덕이랑 월정리 카페, 겨울 평일에도 손님이 있을까요?", ["hamdeok", "woljeong"], "cafe", ["season", "weekday"]),
    ("중문에서 횟집을 하면 관광객 의존도가 얼마나 될까요?", ["jungmun"], "seafood", ["tourism"]),
    ("연동이랑 노형동 중에 한식당 평일 장사는 어디가 꾸준해요?", ["yeondong", "nohyeong"], "korean", ["weekday"]),
    ("성산에서 해산물 식당을 하면 비 오는 날 손님이 얼마나 줄어요?", ["seongsan"], "seafood", ["weather"]),
    ("서귀포 올레시장 근처 분식집은 몇 시에 손님이 많을까요?", ["seogwi"], "snack", ["time"]),
    ("세화에서 카페를 하면 비수기에도 괜찮을까요?", ["sehwa"], "cafe", ["season"]),
    ("표선이랑 모슬포 치킨집, 비 오면 어떤가요?", ["pyoseon", "moseulpo"], "chicken", ["weather"]),
    ("아라동 카페는 주말이랑 평일 차이가 큰가요?", ["ara"], "cafe", ["weekday"]),
    ("원도심 동문시장 근처 주점은 몇 시가 제일 바쁜가요?", ["ildo"], "pub", ["time"]),
    ("이호테우 카페랑 함덕 카페, 관광객 비중을 비교해 주세요", ["dodu", "hamdeok"], "cafe", ["tourism"]),
    ("협재에서 베이커리를 하면 비수기와 성수기 차이가 어느 정도인가요?", ["hyeopjae"], "bakery", ["season"]),
    ("노형 편의점은 평일이랑 주말 매출 차이가 있나요?", ["nohyeong"], "convenience", ["weekday"]),
    ("애월에서 한식당을 하면 비 오는 날 손님이 줄까요?", ["aewol"], "korean", ["weather"]),
    ("월정리 카페는 겨울에 얼마나 줄어드나요?", ["woljeong"], "cafe", ["season"]),
    ("중문이랑 서귀포 시내 양식당, 관광객 비중은 어떤가요?", ["jungmun", "seogwi"], "western", ["tourism"]),
    ("연동 치킨집은 몇 시에 손님이 많아요?", ["yeondong"], "chicken", ["time"]),
    ("함덕 해산물 식당, 비수기와 비 오는 날에는 어떤가요?", ["hamdeok"], "seafood", ["season", "weather"]),
    ("모슬포 횟집은 관광객 빠지는 겨울에도 괜찮을까요?", ["moseulpo"], "seafood", ["season", "tourism"]),
    ("아라동 분식집, 비 오는 날이랑 평일에는 어떤가요?", ["ara"], "snack", ["weather", "weekday"]),
]

METRIC_DATASETS = {
    "scale": {"card_grid_500m", "pos_grid_500m"}, "season": {"card_grid_500m", "pos_grid_500m"},
    "tourism": {"card_weekday_v02"}, "weekday": {"card_weekday_v02"}, "time": {"card_time_v02"},
    "weather": {"floating_pop_emd_v02", "bus_usage", "bus_station", "weather_daily", "weather_station"},
}


def load(table: str) -> pd.DataFrame:
    return db.duckdb_query(f"SELECT * FROM {table}")


def last_months(card: pd.DataFrame, n: int) -> list[str]:
    return sorted(card["base_year_month"].unique())[-n:]


def ref_season(card, grid, biz, months):
    d = card[(card.grid_500m == grid) & card.biz_cd.isin(biz) & card.base_year_month.isin(months)]
    m = d.groupby("base_year_month").agg(amt=("use_amt", "sum"), cnt=("use_cnt", "sum"))
    m = m[m.cnt >= config.MIN_USE_CNT]["amt"]
    mon = pd.Series(m.index.str[4:].astype(int), index=m.index)
    peak = m[mon.isin(config.PEAK_MONTHS)]
    py = peak.groupby(peak.index.str[:4]).mean()
    matched = len(py) >= 2 and py.max() / py.min() - 1 > config.YEAR_EFFECT_THRESHOLD
    if matched:  # 같은 시즌연도: 여름(y) + 그해 11·12월 + 다음해 1·2월이 모두 기간 안에 있는 y
        ys = []
        for y in sorted({int(x[:4]) for x in months}):
            need = [f"{y}07", f"{y}08", f"{y}11", f"{y}12", f"{y + 1}01", f"{y + 1}02"]
            if all(x in months for x in need):
                ys.append(y)
        keep_peak = [f"{y}{mm:02d}" for y in ys for mm in config.PEAK_MONTHS]
        keep_off = [f"{y}11" for y in ys] + [f"{y}12" for y in ys] + [f"{y + 1}01" for y in ys] + [f"{y + 1}02" for y in ys]
        p = m[m.index.isin(keep_peak)].mean()
        o = m[m.index.isin(keep_off)].mean()
    else:
        p = m[mon.isin(config.PEAK_MONTHS)].mean()
        o = m[mon.isin(config.OFF_MONTHS)].mean()
    return float(o / p), bool(matched)


def ref_tourism(wk, bjd, biz, months):
    d = wk[(wk.bjd == bjd) & wk.biz_cd.isin(biz) & wk.base_year_month.isin(months)]
    s = d.groupby("tour_type")["use_amt"].sum()
    return float(s.drop("도민", errors="ignore").sum() / s.sum())


def ref_weekday(wk, bjd, biz, months, hol):
    d = wk[(wk.bjd == bjd) & wk.biz_cd.isin(biz) & wk.base_year_month.isin(months)]
    names = ["월", "화", "수", "목", "금", "토", "일"]
    n_wd = n_we = 0
    for ym in months:
        y, mo = int(ym[:4]), int(ym[4:])
        for i in range(1, calendar.monthrange(y, mo)[1] + 1):
            day = dt.date(y, mo, i)
            if day in hol or day.weekday() >= 5:
                n_we += 1
            else:
                n_wd += 1
    a_wd = d[d.week.isin(names[:5])]["use_amt"].sum()
    a_we = d[d.week.isin(["토", "일", "공휴일"])]["use_amt"].sum()
    return float((a_wd / n_wd) / (a_we / n_we))


def ref_weather(fp, wd, emd, station, hol, d_from, d_to):
    v = fp[fp.emd_nm == emd].groupby("base_date")["visit_pop_cnt"].sum().rename("v").reset_index()
    r = wd[wd.observatory_code == station][["base_date", "daily_rainfall"]]
    x = v.merge(r, on="base_date").dropna()
    x = x[(x.base_date >= d_from) & (x.base_date <= d_to)]
    x["rain"] = x.daily_rainfall >= config.RAIN_MM
    x["we"] = x.base_date.map(lambda d: d.weekday() >= 5 or d in hol)
    x["ym"] = x.base_date.map(lambda d: (d.year, d.month))
    g = x.groupby(["ym", "we", "rain"])["v"].agg(["mean", "size"]).unstack("rain")
    g = g.dropna()
    eff = g[("mean", True)] / g[("mean", False)] - 1
    w = g[("size", True)]
    return float((eff * w).sum() / w.sum())


def ref_time(tm, bjd, biz, months):
    d = tm[(tm.bjd == bjd) & tm.biz_cd.isin(biz) & tm.base_year_month.isin(months)]
    s = d.groupby("time")["use_amt"].sum()
    return str(s.idxmax()), float(s.max() / s.sum())


def main() -> None:
    card, wk, tm = load("card_grid_500m"), load("card_weekday_v02"), load("card_time_v02")
    fp, wd = load("floating_pop_emd_v02"), load("weather_daily")
    for t in (fp, wd):
        t["base_date"] = pd.to_datetime(t["base_date"]).dt.date
    hol = set(pd.to_datetime(load("ref_holiday")["holiday"]).dt.date)
    wst = load("weather_station").to_dict("records")
    months = last_months(card, config.ANALYSIS_MONTHS)
    d_from = dt.date(int(months[0][:4]), int(months[0][4:]), 1)
    d_to = min(wd.base_date.max(), fp.base_date.max())
    inds = geo.load_reference()["industries"]

    out = []
    for i, (q, places, ind, metrics) in enumerate(QUESTIONS, 1):
        biz = inds[ind]["biz_cd"]
        exp_metrics = ["scale"] + [m for m in ["season", "tourism", "weekday", "weather", "time"] if m in metrics]
        datasets = sorted(set().union(*(METRIC_DATASETS[m] for m in exp_metrics)))
        values = {}
        for tag, pid in zip("ABC", places):
            p = geo.place_by_id(pid)
            g = geo.point_to_grid(p.lat, p.lon)["grid"]
            if "season" in metrics:
                values[f"{tag}.season"], values[f"{tag}.season_matched"] = ref_season(card, g, biz, months)
            if "tourism" in metrics:
                values[f"{tag}.tourism"] = ref_tourism(wk, p.bjd, biz, months)
            if "weekday" in metrics:
                values[f"{tag}.weekday"] = ref_weekday(wk, p.bjd, biz, months, hol)
            if "weather" in metrics:
                st = geo.nearest_station(p.lat, p.lon, wst)["observatory_code"]
                values[f"{tag}.weather"] = ref_weather(fp, wd, p.emd, st, hol, d_from, d_to)
            if "time" in metrics:
                values[f"{tag}.time_slot"], values[f"{tag}.time_share"] = ref_time(tm, p.bjd, biz, months)
        out.append({"id": f"Q{i:02d}", "question": q, "expected": {
            "places": places, "industry": ind, "metrics": exp_metrics, "datasets": datasets, "values": values}})
        print(f"Q{i:02d}", {k: (round(v, 4) if isinstance(v, float) else v) for k, v in values.items()})
    path = ROOT / "eval" / "golden_questions.json"
    path.write_text(json.dumps({"tolerance": 0.001, "analysis_months": months, "questions": out},
                               ensure_ascii=False, indent=1), encoding="utf-8")
    print("→", path)


if __name__ == "__main__":
    main()
