@echo off
REM AgentForge Backend Load Test Runner (Windows)
REM Usage:
REM   run.bat              - Run interactive Web UI (http://localhost:8089)
REM   run.bat --web        - Run interactive Web UI
REM   run.bat --headless   - Run headless test and generate report.html

setlocal

set SCRIPT_DIR=%~dp0
cd /d "%SCRIPT_DIR%"

where locust >nul 2>nul
if %ERRORLEVEL% neq 0 (
    echo [WARNING] Locust is not installed in current environment.
    echo Run: pip install locust
    exit /b 1
)

if "%LOAD_TEST_HOST%"=="" (
    set HOST=http://localhost:8000
) else (
    set HOST=%LOAD_TEST_HOST%
)

echo [INFO] AgentForge Load Test Target: %HOST%

if "%~1"=="" goto web
if "%~1"=="--web" goto web
if "%~1"=="--headless" goto headless

locust -f locustfile.py --host %HOST% %*
goto end

:web
echo [INFO] Starting Locust Web UI at http://localhost:8089 ...
locust -f locustfile.py --host %HOST%
goto end

:headless
echo [INFO] Running Headless Load Test (5 Users, 1m duration)...
locust -f locustfile.py --host %HOST% --headless -u 5 -r 1 -t 1m --html load_test_report.html %2 %3 %4 %5 %6 %7 %8 %9
goto end

:end
endlocal
