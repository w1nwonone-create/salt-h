"""duckdb_query — 읽기 전용 조회 Tool (Navigator·Critic 용 메타 조회)."""
from __future__ import annotations

import hashlib
from pathlib import Path

import duckdb

import config


def connect(db_path: Path | str | None = None):
    path = Path(db_path or config.DB_PATH)
    if not path.exists():
        raise FileNotFoundError(
            f"데이터베이스가 없습니다: {path}\n먼저 `python scripts/build_sample_data.py` 를 실행해 주세요."
        )
    return duckdb.connect(str(path), read_only=True)


def duckdb_query(sql: str, params: dict | list | None = None, db_path=None):
    """SELECT 전용. 결과를 DataFrame 으로 반환."""
    if not sql.lstrip().upper().startswith(("SELECT", "WITH", "DESCRIBE", "SHOW")):
        raise ValueError("duckdb_query 는 조회(SELECT) 전용입니다.")
    con = connect(db_path)
    try:
        return con.execute(sql, params or []).df()
    finally:
        con.close()


def data_version(db_path=None) -> dict:
    """재현성 기록용: DB 파일 해시·메타·테이블 행 수."""
    path = Path(db_path or config.DB_PATH)
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    con = connect(path)
    try:
        tables = [r[0] for r in con.execute("SELECT table_name FROM information_schema.tables ORDER BY 1").fetchall()]
        rows = {t: con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0] for t in tables}
        meta = {}
        if "_meta" in tables:
            meta = dict(con.execute("SELECT key, value FROM _meta").fetchall())
    finally:
        con.close()
    return {"db_path": str(path), "sha256": h.hexdigest(), "tables": rows, "meta": meta}
