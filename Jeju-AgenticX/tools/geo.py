"""위치 연결 Tool — point_to_grid · point_to_bjd · nearby_stops · nearest_station.

좌표계: WGS84(위경도) → UTM-K(EPSG:5179, GRS80 횡메르카토르) 투영 후 500m 단위로 절사해
격자 ID 를 만듭니다. 외부 GIS 라이브러리 없이 동작하도록 투영식을 직접 구현했습니다
(Snyder, *Map Projections — A Working Manual*, 1987, 식 8-9~8-10).

격자 ID 형식: ``G500_{X//500}_{Y//500}``. 센터 실데이터의 격자 ID 체계가 다르면
``grid_id()`` 한 곳만 바꾸면 됩니다.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from functools import lru_cache

import yaml

import config

# ---- UTM-K (EPSG:5179) ---------------------------------------------------------
_A = 6378137.0
_F = 1 / 298.257222101
_E2 = _F * (2 - _F)
_EP2 = _E2 / (1 - _E2)
_K0 = 0.9996
_LAT0 = math.radians(38.0)
_LON0 = math.radians(127.5)
_FE, _FN = 1_000_000.0, 2_000_000.0
GRID = 500


def _meridian_arc(phi: float) -> float:
    e2, e4, e6 = _E2, _E2**2, _E2**3
    return _A * (
        (1 - e2 / 4 - 3 * e4 / 64 - 5 * e6 / 256) * phi
        - (3 * e2 / 8 + 3 * e4 / 32 + 45 * e6 / 1024) * math.sin(2 * phi)
        + (15 * e4 / 256 + 45 * e6 / 1024) * math.sin(4 * phi)
        - (35 * e6 / 3072) * math.sin(6 * phi)
    )


_M0 = _meridian_arc(_LAT0)


def to_utmk(lat: float, lon: float) -> tuple[float, float]:
    """위경도(도) → UTM-K (x, y) 미터."""
    phi, lam = math.radians(lat), math.radians(lon)
    sin_p, cos_p, tan_p = math.sin(phi), math.cos(phi), math.tan(phi)
    n = _A / math.sqrt(1 - _E2 * sin_p**2)
    t = tan_p**2
    c = _EP2 * cos_p**2
    a = (lam - _LON0) * cos_p
    m = _meridian_arc(phi)
    x = _FE + _K0 * n * (a + (1 - t + c) * a**3 / 6 + (5 - 18 * t + t**2 + 72 * c - 58 * _EP2) * a**5 / 120)
    y = _FN + _K0 * (
        m - _M0
        + n * tan_p * (a**2 / 2 + (5 - t + 9 * c + 4 * c**2) * a**4 / 24
                       + (61 - 58 * t + t**2 + 600 * c - 330 * _EP2) * a**6 / 720)
    )
    return x, y


def from_utmk(x: float, y: float) -> tuple[float, float]:
    """UTM-K → 위경도. 순방향 식을 뉴턴법으로 역산(제주 범위에서 1e-9도 이내)."""
    lat, lon = 33.4, 126.5
    for _ in range(8):
        fx, fy = to_utmk(lat, lon)
        dx, dy = x - fx, y - fy
        if abs(dx) < 1e-4 and abs(dy) < 1e-4:
            break
        h = 1e-5
        x1, y1 = to_utmk(lat + h, lon)
        x2, y2 = to_utmk(lat, lon + h)
        j11, j12 = (x1 - fx) / h, (x2 - fx) / h
        j21, j22 = (y1 - fy) / h, (y2 - fy) / h
        det = j11 * j22 - j12 * j21
        lat += (j22 * dx - j12 * dy) / det
        lon += (-j21 * dx + j11 * dy) / det
    return lat, lon


def grid_id(ix: int, iy: int) -> str:
    return f"G500_{ix}_{iy}"


def parse_grid_id(gid: str) -> tuple[int, int]:
    _, ix, iy = gid.split("_")
    return int(ix), int(iy)


def grid_bounds(gid: str) -> list[tuple[float, float]]:
    """격자의 네 꼭짓점(위도, 경도) — 지도 표시용."""
    ix, iy = parse_grid_id(gid)
    corners = [(ix, iy), (ix + 1, iy), (ix + 1, iy + 1), (ix, iy + 1)]
    return [from_utmk(cx * GRID, cy * GRID) for cx, cy in corners]


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6_371_008.8
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


# ---- Tools ---------------------------------------------------------------------
def point_to_grid(lat: float, lon: float) -> dict:
    """좌표 → 포함 500m 격자 + 3×3 인접 격자 + 경계 근접 여부."""
    x, y = to_utmk(lat, lon)
    ix, iy = int(x // GRID), int(y // GRID)
    ox, oy = x - ix * GRID, y - iy * GRID
    edge = min(ox, GRID - ox, oy, GRID - oy)
    neighbors = [grid_id(ix + dx, iy + dy) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    near = []
    if ox < config.GRID_BOUNDARY_M:
        near.append(grid_id(ix - 1, iy))
    if GRID - ox < config.GRID_BOUNDARY_M:
        near.append(grid_id(ix + 1, iy))
    if oy < config.GRID_BOUNDARY_M:
        near.append(grid_id(ix, iy - 1))
    if GRID - oy < config.GRID_BOUNDARY_M:
        near.append(grid_id(ix, iy + 1))
    return {
        "grid": grid_id(ix, iy),
        "grids_3x3": neighbors,
        "edge_distance_m": round(edge, 1),
        "near_boundary": bool(near),
        "boundary_neighbors": near,
    }


@dataclass(frozen=True)
class Place:
    id: str
    name: str
    aliases: tuple
    sgg: str
    emd: str
    bjd: str
    bjd_nm: str
    lat: float
    lon: float
    stops: tuple
    profile: dict


@lru_cache(maxsize=1)
def load_reference() -> dict:
    with open(config.PLACES_PATH, encoding="utf-8") as f:
        ref = yaml.safe_load(f)
    places = [
        Place(p["id"], p["name"], tuple(p.get("aliases", [])), p["sgg"], p["emd"], str(p["bjd"]),
              p["bjd_nm"], float(p["lat"]), float(p["lon"]), tuple(p.get("stops", [])), p.get("profile", {}))
        for p in ref["places"]
    ]
    return {"places": places, "stations": ref["weather_stations"], "industries": ref["industries"]}


def places() -> list[Place]:
    return load_reference()["places"]


def place_by_id(pid: str) -> Place | None:
    return next((p for p in places() if p.id == pid), None)


def point_to_bjd(lat: float, lon: float) -> dict:
    """좌표 → 가장 가까운 기준 법정동(중심점 기준 근사).

    실데이터 환경에서는 법정동 경계(SHP)를 geopandas 로 공간조인하는 방식으로
    교체할 수 있습니다. 근사 방식임을 결과에 함께 표시합니다.
    """
    best = min(places(), key=lambda p: haversine_m(lat, lon, p.lat, p.lon))
    d = haversine_m(lat, lon, best.lat, best.lon)
    return {"bjd": best.bjd, "bjd_nm": best.bjd_nm, "emd": best.emd, "sgg": best.sgg,
            "place_id": best.id, "distance_m": round(d), "method": "nearest_centroid",
            "far_from_reference": d > 3000}


def nearby_stops(lat: float, lon: float, stations: list[dict], radius_m: float | None = None,
                 min_count: int = 2) -> dict:
    """반경 내 버스 정류소. 2곳 미만이면 반경을 2배까지 넓혀 다시 찾습니다."""
    radius = radius_m or config.STOP_RADIUS_M
    for r in (radius, radius * 2):
        hits = []
        for s in stations:
            d = haversine_m(lat, lon, float(s["latitude"]), float(s["longitude"]))
            if d <= r:
                hits.append({**s, "distance_m": round(d)})
        if len(hits) >= min_count:
            break
    hits.sort(key=lambda s: s["distance_m"])
    return {"radius_m": r, "stops": hits, "expanded": r != radius}


def nearest_station(lat: float, lon: float, stations: list[dict] | None = None) -> dict:
    stations = stations or [
        {"observatory_code": s["code"], "observatory_nm": s["name"], "latitude": s["lat"], "longitude": s["lon"]}
        for s in load_reference()["stations"]
    ]
    best = min(stations, key=lambda s: haversine_m(lat, lon, float(s["latitude"]), float(s["longitude"])))
    d = haversine_m(lat, lon, float(best["latitude"]), float(best["longitude"]))
    return {**best, "distance_m": round(d)}
