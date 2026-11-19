"""Jeju-AgenticX 전역 설정.

모든 경로·임계값은 여기서만 정의합니다. 센터 PC에서 반출 제한 실데이터를 쓸 때는
`.env`의 JEJU_DB_PATH 만 바꾸면 동일한 코드가 실데이터로 동작합니다.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:  # .env 는 선택 사항
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env")
except Exception:  # pragma: no cover
    pass

DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
DB_PATH = Path(os.getenv("JEJU_DB_PATH") or DATA_DIR / "jeju.duckdb")
CATALOG_PATH = DATA_DIR / "data_catalog.yaml"
PLACES_PATH = DATA_DIR / "places.yaml"
TEMPLATE_DIR = ROOT / "analysis_templates"
REPORT_TEMPLATE_DIR = ROOT / "templates"
PROMPT_DIR = ROOT / "prompts"
RUNS_DIR = Path(os.getenv("JEJU_RUNS_DIR") or ROOT / "runs")

# ---- LLM ------------------------------------------------------------------
# LLM_MODE: auto | anthropic | ollama | rules
LLM_MODE = os.getenv("LLM_MODE", "auto").lower()
LLM_API_KEY = os.getenv("LLM_API_KEY") or os.getenv("ANTHROPIC_API_KEY") or ""
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:3b-instruct-q4_K_M")
LLM_TIMEOUT = float(os.getenv("LLM_TIMEOUT", "60"))

# ---- 분석 기준 ---------------------------------------------------------------
PEAK_MONTHS = [7, 8]            # 성수기
OFF_MONTHS = [11, 12, 1, 2]     # 비수기
ANALYSIS_MONTHS = 24            # 월 단위 비교 기간(최근 n개월)
RAIN_MM = 1.0                   # 우천일 기준 일강수량(mm)
MIN_DAYS_PER_GROUP = 10         # 날씨 비교 그룹별 최소 일수 (미달 시 '참고용')
MIN_USE_CNT = 5                 # 최소 집계 기준: 이용 건수 미만 셀은 비노출
MIN_POS_STORES = 3              # 외식업 표본 점포 수 미만이면 비노출
STOP_RADIUS_M = 500             # 후보지 반경 내 정류소
YEAR_EFFECT_THRESHOLD = 0.10    # 연도별 성수기 규모 차이가 이보다 크면 동일 연도 비교로 재분석
GRID_BOUNDARY_M = 100           # 격자 경계까지 거리가 이보다 가까우면 인접 격자 함께 표시

# ---- Agent 반복 한도 -----------------------------------------------------------
MAX_CODE_FIX = 3
MAX_REANALYSIS = 2
SANDBOX_TIMEOUT_S = 60
