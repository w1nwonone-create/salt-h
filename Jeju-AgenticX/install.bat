@echo off
chcp 65001 > nul
cd /d %~dp0
echo ============================================
echo   Jeju-AgenticX 설치
echo ============================================
echo [1/4] Python 가상환경을 만듭니다...
python -m venv .venv
if errorlevel 1 (
  echo Python 3.11 이상을 먼저 설치해 주세요. https://www.python.org/downloads/
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
echo [2/4] 필요한 라이브러리를 설치합니다. 몇 분 걸릴 수 있습니다...
python -m pip install --upgrade pip > nul
pip install -r requirements.txt
if errorlevel 1 (
  echo 라이브러리 설치에 실패했습니다. 인터넷 연결을 확인해 주세요.
  pause
  exit /b 1
)
echo [3/4] 분석 데이터베이스를 준비합니다...
if not exist .env copy .env.example .env > nul
if not exist data\jeju.duckdb python scripts\build_sample_data.py
echo [4/4] 바탕화면에 'Jeju-AgenticX 실행' 바로가기를 만듭니다...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut([Environment]::GetFolderPath('Desktop')+'\Jeju-AgenticX 실행.lnk'); $s.TargetPath='%~dp0run.bat'; $s.WorkingDirectory='%~dp0'; $s.Save()"
echo.
echo 설치가 끝났습니다. 바탕화면의 'Jeju-AgenticX 실행' 을 눌러 시작하세요.
pause
