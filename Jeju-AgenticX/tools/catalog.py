"""catalog_search · schema_peek — 데이터 명세 검색 Tool."""
from __future__ import annotations

from functools import lru_cache

import yaml

import config
from tools import db


@lru_cache(maxsize=1)
def load_catalog() -> dict:
    with open(config.CATALOG_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f)


def catalog_search(query: str = "", metrics: list[str] | None = None, top_k: int = 5) -> list[dict]:
    """질문(자연어) 또는 지표 목록으로 필요한 데이터셋을 찾습니다.

    - metrics 가 주어지면 지표 → 데이터셋 매핑을 그대로 사용(결정적).
    - query 만 있으면 태그·이름·컬럼 설명과의 키워드 겹침으로 순위를 매깁니다.
    """
    cat = load_catalog()
    out: dict[str, dict] = {}
    for m in metrics or []:
        spec = cat["metrics"].get(m)
        if not spec:
            continue
        for key in spec["datasets"]:
            item = out.setdefault(key, {"key": key, **_brief(key), "for_metrics": [], "score": 0})
            item["for_metrics"].append(m)
            item["score"] += 10
    if query:
        q = query.replace(" ", "")
        for key, ds in cat["datasets"].items():
            words = set(ds.get("tags", [])) | {ds["name"]} | {c["desc"] for c in ds["columns"].values()}
            score = sum(1 for w in words if w and w.replace(" ", "") in q)
            if score:
                item = out.setdefault(key, {"key": key, **_brief(key), "for_metrics": [], "score": 0})
                item["score"] += score
    return sorted(out.values(), key=lambda x: -x["score"])[: max(top_k, len(out) if metrics else top_k)]


def _brief(key: str) -> dict:
    ds = load_catalog()["datasets"][key]
    return {"name": ds["name"], "grain": ds["grain"], "export": ds["export"]}


def schema_peek(key: str, include_samples: bool = False, db_path=None) -> dict:
    """명세 컬럼과 실제 테이블 컬럼을 대조하고, 데이터 기간을 확인합니다.

    include_samples=True 는 오프라인(로컬 모델) 모드에서만 사용합니다. 외부 LLM 에는
    원본 행을 보내지 않고 컬럼 구조와 기간만 전달합니다(계획서 4.3).
    """
    spec = load_catalog()["datasets"][key]
    con = db.connect(db_path)
    try:
        exists = con.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?", [key]).fetchone()[0] > 0
        if not exists:
            return {"key": key, "name": spec["name"], "exists": False, "missing_columns": list(spec["columns"])}
        cols = {r[0]: r[1] for r in con.execute(
            "SELECT column_name, data_type FROM information_schema.columns WHERE table_name = ?", [key]).fetchall()}
        missing = [c for c in spec["columns"] if c not in cols]
        period = None
        for c in ("base_year_month", "base_date"):
            if c in cols:
                lo, hi = con.execute(f'SELECT MIN("{c}"), MAX("{c}") FROM "{key}"').fetchone()
                period = {"column": c, "from": str(lo), "to": str(hi)}
                break
        rows = con.execute(f'SELECT COUNT(*) FROM "{key}"').fetchone()[0]
        res = {"key": key, "name": spec["name"], "exists": True, "columns": cols, "missing_columns": missing,
               "period": period, "rows": rows, "export": spec["export"], "grain": spec["grain"]}
        if include_samples:
            res["samples"] = con.execute(f'SELECT * FROM "{key}" LIMIT 3').df().to_dict("records")
        return res
    finally:
        con.close()


def schema_text(keys: list[str]) -> str:
    """LLM 코드 생성용 스키마 설명(컬럼명·타입·설명만, 원본 데이터 없음)."""
    cat = load_catalog()["datasets"]
    lines = []
    for k in keys:
        ds = cat[k]
        lines.append(f"- 테이블 `{k}` — {ds['name']} ({ds['grain']})")
        for c, spec in ds["columns"].items():
            lines.append(f"    - {c} {spec['type']}: {spec['desc']}")
    return "\n".join(lines)
