"""예시 데이터 생성 + DuckDB(jeju.duckdb) 구축.

반출 제한 데이터(카드·외식업 포스·유동인구)는 센터 밖에서 원본을 확보할 수 없으므로,
제주데이터허브 「데이터 명세서」와 동일한 컬럼 구조의 **예시 데이터**를 생성합니다.
반출 가능 데이터(버스·날씨·정류소·관측소)는 ``data/raw/<테이블명>.csv`` 가 있으면
그 실데이터를 우선 적재하고, 없으면 예시 데이터를 생성합니다.

    python scripts/build_sample_data.py            # 기본 (seed=20261119)
    python scripts/build_sample_data.py --seed 7

예시 데이터의 수치는 실제 상권 실적이 아니며, Agent 전체 흐름의 동작 검증용입니다.
"""
from __future__ import annotations

import argparse
import calendar
import datetime as dt
import math
import sys
from pathlib import Path
from statistics import NormalDist

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import duckdb  # noqa: E402

import config  # noqa: E402
from tools import geo  # noqa: E402

MONTH_START = dt.date(2024, 11, 1)
MONTH_END = dt.date(2026, 10, 1)
DAY_START = dt.date(2024, 11, 1)
DAY_END = dt.date(2026, 10, 31)
FLOAT_START = dt.date(2025, 5, 1)  # 내국인 유동인구(읍면동)_v02 제공 시작

# 관광 수요 월별 지수(7~8월=1.0) / 도민 소비 월별 지수
TOUR_IDX = {1: .27, 2: .30, 3: .45, 4: .60, 5: .65, 6: .62, 7: 1.0, 8: 1.0, 9: .62, 10: .66, 11: .32, 12: .28}
RES_IDX = {1: .95, 2: .95, 3: 1.0, 4: 1.0, 5: 1.02, 6: 1.0, 7: 1.03, 8: 1.03, 9: 1.0, 10: 1.0, 11: .98, 12: 1.02}
RAIN_P = {1: .45, 2: .40, 3: .35, 4: .33, 5: .33, 6: .45, 7: .50, 8: .45, 9: .40, 10: .25, 11: .33, 12: .42}
TEMP = {1: 6, 2: 7, 3: 10, 4: 14, 5: 18, 6: 21, 7: 26, 8: 27, 9: 24, 10: 19, 11: 13, 12: 8}

# 업종: (도민 가중, 관광 가중, 평균 객단가)
BIZ = {
    "I56220": (1.00, 1.00, 9_000), "I56111": (1.60, 1.10, 24_000), "I56113": (0.90, 0.90, 48_000),
    "I56114": (0.50, 1.20, 52_000), "I56123": (0.40, 0.50, 33_000), "I56191": (0.45, 0.35, 12_000),
    "I56192": (0.35, 0.25, 21_000), "I56193": (0.60, 0.15, 26_000), "I56194": (0.45, 0.25, 11_000),
    "I56213": (0.35, 0.20, 38_000), "I56219": (0.50, 0.30, 45_000), "G47122": (1.20, 0.80, 8_500),
}
BIZ_POS = {"I56220": "커피전문점", "I56111": "한식", "I56113": "한식", "I56114": "해산물", "I56123": "양식",
           "I56192": "양식", "I56191": "제과·제빵", "I56193": "치킨", "I56194": "분식", "I56213": "주점",
           "I56219": "주점"}

TIMES = ["오전", "점심", "오후", "저녁", "밤"]
TIME_PROFILE = {
    ("tour", "res"): [.12, .25, .38, .20, .05], ("tour", "tour"): [.15, .25, .40, .16, .04],
    ("downtown", "res"): [.10, .30, .25, .27, .08], ("downtown", "tour"): [.10, .28, .30, .25, .07],
    ("campus", "res"): [.12, .28, .30, .22, .08], ("campus", "tour"): [.12, .28, .32, .22, .06],
}
BIZ_TIME = {
    "I56213": [.01, .04, .10, .45, .40], "I56219": [.01, .04, .08, .45, .42], "I56193": [.02, .10, .15, .43, .30],
    "I56111": [.08, .38, .14, .35, .05], "I56113": [.03, .25, .12, .50, .10], "I56114": [.05, .35, .15, .40, .05],
    "I56123": [.08, .40, .20, .28, .04], "I56192": [.05, .30, .20, .35, .10], "I56194": [.15, .40, .25, .15, .05],
    "G47122": [.18, .17, .20, .22, .23],
}
WEEK = ["월", "화", "수", "목", "금", "토", "일", "공휴일"]

# 공휴일(대체공휴일 포함, 예시 데이터 기준)
HOLIDAYS = [
    "2024-12-25",
    "2025-01-01", "2025-01-27", "2025-01-28", "2025-01-29", "2025-01-30", "2025-03-01", "2025-03-03",
    "2025-05-05", "2025-05-06", "2025-06-03", "2025-06-06", "2025-08-15", "2025-10-03", "2025-10-05",
    "2025-10-06", "2025-10-07", "2025-10-08", "2025-10-09", "2025-12-25",
    "2026-01-01", "2026-02-16", "2026-02-17", "2026-02-18", "2026-03-01", "2026-03-02", "2026-05-05",
    "2026-05-24", "2026-05-25", "2026-06-03", "2026-06-06", "2026-08-15", "2026-08-17", "2026-09-24",
    "2026-09-25", "2026-09-26", "2026-10-03", "2026-10-05", "2026-10-09",
]
HOL = {dt.date.fromisoformat(d) for d in HOLIDAYS}


def months() -> list[dt.date]:
    out, d = [], MONTH_START
    while d <= MONTH_END:
        out.append(d)
        d = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return out


def days(start: dt.date, end: dt.date) -> list[dt.date]:
    return [start + dt.timedelta(i) for i in range((end - start).days + 1)]


def week_cat(d: dt.date) -> str:
    return "공휴일" if d in HOL else WEEK[d.weekday()]


def day_counts(year: int, month: int) -> dict[str, int]:
    n = calendar.monthrange(year, month)[1]
    c = {w: 0 for w in WEEK}
    for i in range(1, n + 1):
        c[week_cat(dt.date(year, month, i))] += 1
    return c


def is_weekend(d: dt.date) -> bool:
    return d.weekday() >= 5 or d in HOL


# ---------------------------------------------------------------------------------
def build(seed: int) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)
    ref = geo.load_reference()
    places = ref["places"]
    mlist = months()

    # ---- 격자 구성: 후보 중심 격자 + 3×3 -----------------------------------------
    grid_w = {}  # place_id -> {grid: (w_res, w_tour)}
    for p in places:
        g = geo.point_to_grid(p.lat, p.lon)
        nb = [x for x in g["grids_3x3"] if x != g["grid"]]
        wr = rng.dirichlet(np.ones(8) * 2) * 0.45
        wt = rng.dirichlet(np.ones(8) * 2) * 0.45
        grid_w[p.id] = {g["grid"]: (0.55, 0.55), **{x: (wr[i], wt[i]) for i, x in enumerate(nb)}}

    # ---- 카드 이용 현황(500m격자) + 외식업 포스 -------------------------------------
    card_rows, pos_rows = [], []
    place_month = {}  # (pid, ym, biz) -> (res_amt, tour_amt) 법정동 단위
    for p in places:
        pr = p.profile
        for mi, m in enumerate(mlist):
            ym = m.strftime("%Y%m")
            growth = (1 + pr["growth"]) ** (mi / 12)
            for biz, (rw, tw, ticket) in BIZ.items():
                res = pr["resident"] * rw * RES_IDX[m.month] * growth * 1e6
                tour = pr["tourist"] * tw * TOUR_IDX[m.month] * growth * 1e6
                place_month[(p.id, ym, biz)] = (res * 1.15 * rng.lognormal(0, .03), tour * 1.15 * rng.lognormal(0, .03))
                pos_acc = {}
                for gid, (w_r, w_t) in grid_w[p.id].items():
                    amt = (res * w_r + tour * w_t) * rng.lognormal(0, .06)
                    if amt < 1:
                        continue
                    for ut, share in (("개인", .93), ("법인", .07)):
                        a = amt * share * rng.lognormal(0, .02)
                        card_rows.append((ym, gid, p.bjd, biz, ut, max(0, round(a / ticket)), round(a)))
                    if biz in BIZ_POS:
                        k = (gid, BIZ_POS[biz])
                        pos_acc.setdefault(k, [0.0, 0.0])
                        pos_acc[k][0] += amt
                        pos_acc[k][1] += (pr["resident"] * w_r * rw + pr["tourist"] * w_t * tw)
                for (gid, pnm), (amt, size) in pos_acc.items():
                    stores = max(1, round(size * 0.36))
                    sale = amt * 2.3 * rng.lognormal(0, .05)
                    pos_rows.append((ym, gid, pnm, round(sale), int(stores), round(sale / 15_000)))

    biz_nm = {"I56111": "한식 일반 음식점업", "I56113": "한식 육류 요리 전문점", "I56114": "한식 해산물 요리 전문점",
              "I56123": "서양식 음식점업", "I56191": "제과점업", "I56192": "피자·햄버거·샌드위치 및 유사 음식점업",
              "I56193": "치킨 전문점", "I56194": "분식 및 김밥 전문점", "I56213": "생맥주 전문점",
              "I56219": "기타 주점업", "I56220": "비알콜 음료점업", "G47122": "체인화 편의점"}
    card = pd.DataFrame(card_rows, columns=["base_year_month", "grid_500m", "bjd", "biz_cd", "user_type", "use_cnt", "use_amt"])
    card.insert(4, "biz_nm", card["biz_cd"].map(biz_nm))
    pos = pd.DataFrame(pos_rows, columns=["base_year_month", "grid_500", "biz_small_nm", "sale_amt", "store_cnt", "use_cnt"])
    # 결측 시연: 일부 격자·월 POS 누락
    for pid, ym in (("hyeopjae", "202512"), ("woljeong", "202601")):
        g = geo.point_to_grid(geo.place_by_id(pid).lat, geo.place_by_id(pid).lon)["grid"]
        pos = pos[~((pos.grid_500 == g) & (pos.base_year_month == ym))]

    # ---- 카드 요일별 / 시간대 v02 -----------------------------------------------------
    wk_rows, tm_rows = [], []
    pmap = {p.id: p for p in places}
    for (pid, ym, biz), (res, tour) in place_month.items():
        p = pmap[pid]
        pr = p.profile
        y, mo = int(ym[:4]), int(ym[4:])
        cnt = day_counts(y, mo)
        ticket = BIZ[biz][2]
        parts = {"도민": res, "개별관광객": tour * (1 - pr["group_share"]), "단체관광객": tour * pr["group_share"]}
        for tt, amt in parts.items():
            kind = "res" if tt == "도민" else "tour"
            wk = pr["wkd_res"] if kind == "res" else pr["wkd_tour"]
            w = {"월": 1, "화": .98, "수": 1, "목": 1.02, "금": 1.07, "토": wk, "일": wk * .96,
                 "공휴일": wk * (1.0 if kind == "res" else 1.1)}
            den = sum(cnt[c] * w[c] for c in WEEK)
            for c in WEEK:
                if cnt[c] == 0:
                    continue
                a = amt * cnt[c] * w[c] / den * rng.lognormal(0, .04)
                wk_rows.append((ym, p.bjd, biz, tt, c, round(a / ticket), round(a)))
            prof = BIZ_TIME.get(biz) or TIME_PROFILE[(pr["time"], kind)]
            for tname, s in zip(TIMES, prof):
                a = amt * s * rng.lognormal(0, .05)
                tm_rows.append((ym, p.bjd, biz, tt, tname, round(a / ticket), round(a)))
    weekday = pd.DataFrame(wk_rows, columns=["base_year_month", "bjd", "biz_cd", "tour_type", "week", "use_cnt", "use_amt"])
    timedf = pd.DataFrame(tm_rows, columns=["base_year_month", "bjd", "biz_cd", "tour_type", "time", "use_cnt", "use_amt"])

    # ---- 날씨 --------------------------------------------------------------------------
    stations = ref["stations"]
    wst = pd.DataFrame([{"observatory_code": s["code"], "observatory_nm": s["name"],
                         "latitude": s["lat"], "longitude": s["lon"]} for s in stations])
    dlist = days(DAY_START, DAY_END)
    nd = NormalDist()
    common = rng.normal(size=len(dlist))
    w_rows = []
    for s in stations:
        e = rng.normal(size=len(dlist))
        for i, d in enumerate(dlist):
            z = .85 * common[i] + math.sqrt(1 - .85**2) * e[i]
            rainy = z > nd.inv_cdf(1 - RAIN_P[d.month])
            mm = round(float(rng.gamma(.8, 12) + 1.0), 1) if rainy else (0.0 if rng.random() < .8 else round(float(rng.uniform(0, .9)), 1))
            temp = round(TEMP[d.month] + rng.normal(0, 2) - (1.2 if rainy else 0), 1)
            wind = round(float(np.clip(rng.gamma(4, 1.4) + (2 if d.month in (12, 1, 2) else 0), 1, 25)), 1)
            w_rows.append((d, s["code"], mm, temp, wind))
    weather = pd.DataFrame(w_rows, columns=["base_date", "observatory_code", "daily_rainfall", "average_temperature", "maximum_wind_speed"])
    miss = (weather.observatory_code == "188") & weather.base_date.between(dt.date(2025, 8, 3), dt.date(2025, 8, 6))
    weather.loc[miss, "daily_rainfall"] = np.nan
    rain_map = {(r.base_date, r.observatory_code): r.daily_rainfall for r in weather.itertuples()}

    def station_of(p):
        return geo.nearest_station(p.lat, p.lon)["observatory_code"]

    # ---- 내국인 유동인구(읍면동)_v02 -------------------------------------------------------
    hour_share = np.array([.2, .1, .1, .1, .2, .5, 1.2, 2.2, 3.5, 5.0, 6.5, 7.2, 7.6, 7.8, 7.8, 7.5, 7.0, 6.5,
                           5.6, 4.6, 3.6, 2.6, 1.6, .8])
    hour_share = hour_share / hour_share.sum()
    emds = {}
    for p in places:
        emds.setdefault(p.emd, []).append(p)
    fp_rows = []
    for emd, plist in emds.items():
        R = sum(p.profile["resident"] for p in plist)
        T = sum(p.profile["tourist"] for p in plist)
        pr = plist[0].profile
        st = station_of(plist[0])
        for d in days(FLOAT_START, DAY_END):
            if emd == "구좌읍" and dt.date(2025, 9, 10) <= d <= dt.date(2025, 9, 14):
                continue  # 결측 시연
            mm = rain_map.get((d, st))
            rain = 0 if (mm is None or (isinstance(mm, float) and math.isnan(mm))) else mm
            intensity = (.7 + .3 * min(1, rain / 20)) if rain >= config.RAIN_MM else 0
            we = is_weekend(d)
            res = R * 600 * RES_IDX[d.month] * (pr["wkd_res"] if we else 1) * (1 - pr["rain_res"] * intensity)
            tour = T * 900 * TOUR_IDX[d.month] * (pr["wkd_tour"] if we else 1) * (1 - pr["rain_tour"] * intensity)
            for resd, tot in (("제주", res), ("그외", tour)):
                tot *= rng.lognormal(0, .07)
                vals = tot * hour_share * rng.lognormal(0, .05, 24)
                for h in range(24):
                    fp_rows.append((d, h, emd, resd, round(float(vals[h]), 1)))
    fpop = pd.DataFrame(fp_rows, columns=["base_date", "time", "emd_nm", "resd", "visit_pop_cnt"])

    # ---- 버스 정류소 / 이용 현황 ---------------------------------------------------------
    st_rows, sid = [], 406_000_100
    stop_meta = []
    for p in places:
        for k, nm in enumerate(p.stops):
            dist = 110 + k * 120 + rng.uniform(0, 60)
            ang = rng.uniform(0, 2 * math.pi)
            lat = p.lat + dist * math.cos(ang) / 111_000
            lon = p.lon + dist * math.sin(ang) / (111_000 * math.cos(math.radians(p.lat)))
            sid += int(rng.integers(3, 40))
            st_rows.append((str(sid), nm, round(lon, 6), round(lat, 6)))
            stop_meta.append((str(sid), p, rng.uniform(.5, 1.4)))
    bstation = pd.DataFrame(st_rows, columns=["bus_station_id", "bus_station_nm", "longitude", "latitude"])
    hours = np.arange(5, 24)
    bh = np.array([.6, 2.5, 5.5, 7, 6, 5.5, 6, 6.5, 6.5, 6.8, 7, 7.5, 8, 7, 5, 3.8, 2.8, 1.8, .9])
    bh = bh / bh.sum()
    dall = days(DAY_START, DAY_END)
    b_frames = []
    for sid_, p, w in stop_meta:
        pr = p.profile
        st = station_of(p)
        rain = np.array([0 if (v := rain_map.get((d, st))) is None or (isinstance(v, float) and math.isnan(v)) else v for d in dall])
        rainy = rain >= config.RAIN_MM
        we = np.array([is_weekend(d) for d in dall])
        mo = np.array([d.month for d in dall])
        res = pr["resident"] * 14 * w * np.vectorize(RES_IDX.get)(mo) * np.where(we, .8, 1) * np.where(rainy, 1.04, 1)
        tour = pr["tourist"] * 12 * w * np.vectorize(TOUR_IDX.get)(mo) * np.where(we, pr["wkd_tour"], 1) * np.where(rainy, 1 - pr["rain_tour"] * .8, 1)
        daily = (res + tour) * rng.lognormal(0, .09, len(dall))
        for typ, share in (("승차", .5), ("하차", .5)):
            mat = daily[:, None] * share * bh[None, :] * rng.lognormal(0, .12, (len(dall), len(hours)))
            cnt = rng.poisson(mat)
            dd, hh = np.meshgrid(np.arange(len(dall)), hours, indexing="ij")
            b_frames.append(pd.DataFrame({"base_date": np.array(dall)[dd.ravel()], "base_hour": hh.ravel(),
                                          "bus_station_id": sid_, "get_on_off_type": typ, "user_count": cnt.ravel()}))
    bus = pd.concat(b_frames, ignore_index=True)
    bus = bus[bus.user_count > 0]

    ref_bjd = pd.DataFrame([{"bjd": p.bjd, "bjd_nm": p.bjd_nm, "emd_nm": p.emd, "sgg_nm": p.sgg,
                             "latitude": p.lat, "longitude": p.lon} for p in places])
    holidays = pd.DataFrame({"holiday": pd.to_datetime(HOLIDAYS).date})
    return {
        "card_grid_500m": card, "pos_grid_500m": pos, "card_weekday_v02": weekday, "card_time_v02": timedf,
        "floating_pop_emd_v02": fpop, "bus_usage": bus, "bus_station": bstation, "weather_daily": weather,
        "weather_station": wst, "ref_bjd": ref_bjd, "ref_holiday": holidays,
    }


REAL_OK = {"bus_usage", "bus_station", "weather_daily", "weather_station"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=20261119)
    ap.add_argument("--db", default=str(config.DB_PATH))
    args = ap.parse_args()

    tables = build(args.seed)
    sources = {}
    for name in REAL_OK:
        csv = config.RAW_DIR / f"{name}.csv"
        if csv.exists():
            tables[name] = pd.read_csv(csv, dtype={"bus_station_id": str, "observatory_code": str})
            sources[name] = f"real:{csv.name}"
    db = Path(args.db)
    db.parent.mkdir(parents=True, exist_ok=True)
    if db.exists():
        db.unlink()
    con = duckdb.connect(str(db))
    for name, df in tables.items():
        con.register("_df", df)
        con.execute(f"CREATE TABLE {name} AS SELECT * FROM _df")
        con.unregister("_df")
        print(f"  {name:<22} {len(df):>9,} rows  ({sources.get(name, 'sample')})")
    meta = pd.DataFrame([{"key": "built_at", "value": dt.datetime.now().isoformat(timespec="seconds")},
                         {"key": "seed", "value": str(args.seed)},
                         {"key": "kind", "value": "sample"},
                         *({"key": f"source.{k}", "value": v} for k, v in sources.items())])
    con.register("_m", meta)
    con.execute("CREATE TABLE _meta AS SELECT * FROM _m")
    con.close()
    print(f"→ {db}  ({db.stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
