@echo off
REM ─────────────────────────────────────────────────────────────────
REM 매크로 대시보드 일일 갱신 (블룸버그 PC에서 실행)
REM
REM Windows 작업 스케줄러에 등록: 매일 07:30 KST
REM 1) Bloomberg fetch (모든 티커)
REM 2) FRED fetch (백업/검증)
REM 3) Calendar 갱신 (schedule.yml 기반)
REM 4) Dashboard 빌드
REM 5) git add/commit/push → GitHub Pages 자동 배포
REM ─────────────────────────────────────────────────────────────────

cd /d "%~dp0"

echo === [%date% %time%] Bloomberg fetch ===
python scripts\fetch_bloomberg.py
if errorlevel 1 echo WARN: Bloomberg fetch had errors, continuing...

echo.
echo === [%date% %time%] FRED fetch ===
if "%FRED_API_KEY%"=="" (
    echo SKIP: FRED_API_KEY not set
) else (
    python scripts\fetch_fred.py
)

echo.
echo === [%date% %time%] Calendar refresh ===
python scripts\fetch_calendar.py

echo.
echo === [%date% %time%] Build dashboard ===
python scripts\build_dashboard.py

echo.
echo === [%date% %time%] Git push ===
git pull --rebase
git add data\ docs\
git diff --staged --quiet
if errorlevel 1 (
    git commit -m "daily refresh %date% %time%"
    git push
    echo Pushed.
) else (
    echo No changes.
)

echo.
echo === Done at %date% %time% ===
