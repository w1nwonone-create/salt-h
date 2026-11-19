@echo off
chcp 65001 > nul
cd /d %~dp0
if not exist .venv\Scripts\activate.bat (
  echo 먼저 install.bat 을 실행해 주세요.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
if not exist data\jeju.duckdb python scripts\build_sample_data.py
echo Jeju-AgenticX 를 시작합니다. 잠시 후 브라우저가 열립니다. (이 창을 닫으면 종료됩니다)
start "" http://localhost:8501
streamlit run app.py
