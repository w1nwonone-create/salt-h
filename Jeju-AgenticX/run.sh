#!/usr/bin/env bash
# Linux/macOS 실행 스크립트
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
[ -f .env ] || cp .env.example .env
[ -f data/jeju.duckdb ] || .venv/bin/python scripts/build_sample_data.py
exec .venv/bin/streamlit run app.py
