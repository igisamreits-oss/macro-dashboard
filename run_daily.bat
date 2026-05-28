@echo off
REM ─────────────────────────────────────────────────────────────────
REM 매크로 대시보드 일일 갱신 (블룸버그 PC, 매일 07:30 KST)
REM   1) Bloomberg fetch  2) FRED fetch  3) Calendar  4) Build
REM   5) Pull-rebase + push (with retry to handle Actions cron race)
REM 모든 출력은 logs\run_YYYYMMDD.log에 기록.
REM ─────────────────────────────────────────────────────────────────

cd /d "%~dp0"

if not exist logs mkdir logs
set LOGFILE=logs\run_%date:~0,4%%date:~5,2%%date:~8,2%.log

call :log "============================================"
call :log "START [%date% %time%]"

call :log "[1/4] Bloomberg fetch"
python scripts\fetch_bloomberg.py >> "%LOGFILE%" 2>&1
if errorlevel 1 call :log "  WARN: bloomberg fetch errors, continuing"

call :log "[2/4] FRED fetch"
if "%FRED_API_KEY%"=="" (
    call :log "  SKIP: FRED_API_KEY not set"
) else (
    python scripts\fetch_fred.py >> "%LOGFILE%" 2>&1
)

call :log "[3/4] Calendar refresh"
python scripts\fetch_calendar.py >> "%LOGFILE%" 2>&1

call :log "[4/4] Build dashboard"
python scripts\build_dashboard.py >> "%LOGFILE%" 2>&1

call :log "git pull --rebase"
git pull --rebase >> "%LOGFILE%" 2>&1
if errorlevel 1 (
    call :log "  rebase conflict detected; taking our version + rebuilding"
    git checkout --ours data\ docs\ >> "%LOGFILE%" 2>&1
    python scripts\build_dashboard.py >> "%LOGFILE%" 2>&1
    git add data\ docs\ >> "%LOGFILE%" 2>&1
    git rebase --continue >> "%LOGFILE%" 2>&1
)

git add data\ docs\
git diff --staged --quiet
if errorlevel 1 (
    git commit -m "daily refresh %date% %time%" >> "%LOGFILE%" 2>&1
    REM Retry push up to 3 times with re-rebase between attempts
    for /L %%i in (1,1,3) do (
        git push >> "%LOGFILE%" 2>&1
        if not errorlevel 1 (
            call :log "  push OK on attempt %%i"
            goto :done
        )
        call :log "  push failed attempt %%i, pulling..."
        git pull --rebase >> "%LOGFILE%" 2>&1
    )
    call :log "  PUSH FAILED after 3 attempts -- inspect log"
) else (
    call :log "  no changes to commit"
)

:done
call :log "END [%date% %time%]"
goto :eof

:log
echo [%date% %time%] %~1>> "%LOGFILE%"
echo [%date% %time%] %~1
goto :eof
