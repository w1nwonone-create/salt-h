import math

from tools import geo


def test_utmk_roundtrip():
    for lat, lon in [(33.4627, 126.3115), (33.25, 126.56), (33.55, 126.86)]:
        x, y = geo.to_utmk(lat, lon)
        la, lo = geo.from_utmk(x, y)
        assert math.isclose(la, lat, abs_tol=1e-7) and math.isclose(lo, lon, abs_tol=1e-7)


def test_utmk_reference_point():
    # 원점(38N, 127.5E)은 (1,000,000, 2,000,000)
    x, y = geo.to_utmk(38.0, 127.5)
    assert abs(x - 1_000_000) < 1e-6 and abs(y - 2_000_000) < 1e-6


def test_grid_and_neighbors():
    g = geo.point_to_grid(33.4627, 126.3115)
    assert g["grid"].startswith("G500_") and len(g["grids_3x3"]) == 9 and g["grid"] in g["grids_3x3"]
    assert 0 <= g["edge_distance_m"] <= 250


def test_point_to_bjd_and_station():
    b = geo.point_to_bjd(33.394, 126.240)
    assert b["bjd_nm"] == "한림읍 협재리"
    assert geo.nearest_station(33.394, 126.240)["observatory_nm"] == "고산"
