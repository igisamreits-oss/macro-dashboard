@echo off
REM ─────────────────────────────────────────────────────────────────
REM 매크로 대시보드 일일 갱신 (블룸버그 PC, 매일 07:30 KST)
REM
REM 전략: 원격을 항상 truth로 본다.
REM   1) git fetch + reset --hard origin/main  (로컬 변경 모두 폐기)
REM   2) Bloomberg/FRED/Calendar fetch + build (data/docs 재생성)
REM   3) commit + push (충돌 거의 발생 안 함)
REM   4) push 실패 시 다시 1)부터 재시도 (최대 3회)
REM
REM 이 방식이 rebase보다 단순하고 detached HEAD/conflict 발생 가능성 없음.
REM ─────────────────────────────────────────────────────────────────

cd /d "%~dp0"

if not exist logs mkdir logs
set LOGFILE=logs\run_%date:~0,4%%date:~5,2%%date:~8,2%.log

call :log "============================================"
call :log "START [%date% %time%]"

for /L %%i in (1,1,3) do (
    call :log "----- Attempt %%i -----"
    call :run_once
    if not errorlevel 1 (
        call :log "SUCCESS on attempt %%i"
        goto :done
    )
    call :log "Attempt %%i failed, will retry..."
    timeout /t 5 /nobreak > nul
)
call :log "FAILED after 3 attempts -- inspect log"

:done
call :log "END [%date% %time%]"
goto :eof


:run_once
REM 1) Sync to remote (discard any local changes)
call :log "[sync] fetch + reset --hard origin/main"
git fetch origin main >> "%LOGFILE%" 2>&1
if errorlevel 1 ( call :log "  fetch failed" & exit /b 1 )
git reset --hard origin/main >> "%LOGFILE%" 2>&1
if errorlevel 1 ( call :log "  reset failed" & exit /b 1 )

REM 2) Fetch fresh data + build
call :log "[1/4] Bloomberg fetch"
python scripts\fetch_bloomberg.py >> "%LOGFILE%" 2>&1
if errorlevel 1 call :log "  WARN: bbg fetch had errors, continuing"

call :log "[2/4] FRED fetch"
if "%FRED_API_KEY%"=="" (
    call :log "  SKIP: FRED_API_KEY not set"
) else (
    python scripts\fetch_fred.py >> "%LOGFILE%" 2>&1
)

call :log "[3/5] Calendar refresh"
python scripts\fetch_calendar.py >> "%LOGFILE%" 2>&1

call :log "[4/5] Citi research feed"
python scripts\research\scrape_citi.py >> "%LOGFILE%" 2>&1
if errorlevel 1 call :log "  WARN: citi scrape had errors, continuing"

call :log "[5/5] Build dashboard"
python scripts\build_dashboard.py >> "%LOGFILE%" 2>&1

REM 3) Commit + push
git add data\ docs\
git diff --staged --quiet
if not errorlevel 1 (
    call :log "  no changes to commit"
    exit /b 0
)
git commit -m "daily refresh %date% %time%" >> "%LOGFILE%" 2>&1
call :log "[push] attempting"
git push >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log "  push rejected (remote moved); will retry from scratch"
    exit /b 1
)
call :log "  push OK"
exit /b 0


:log
echo [%date% %time%] %~1>> "%LOGFILE%"
echo [%date% %time%] %~1
goto :eof
