@echo off
@rem ==============================================================================
@rem {{ project_name }} ⚡ One-Click Environment Setup (Windows)
@rem Installs backend Python virtual environment and frontend npm dependencies.
@rem ==============================================================================

chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================================
echo       ⚡ {{ project_name }} - Environment Setup (Windows)
echo ==========================================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

@rem 1. Backend Setup
echo [1/2] Setting up Backend...
cd /d "%ROOT_DIR%backend"

set "PYTHON_CMD="
py -3 --version >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "PYTHON_CMD=py -3"
) else (
    python --version >nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "PYTHON_CMD=python"
    )
)

if "%PYTHON_CMD%"=="" (
    echo [ERROR] Python 3.10+ is required but not found.
    pause
    exit /b 1
)

where uv >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Detected uv for ultra-fast backend dependency installation
    if not exist ".venv" (
        uv venv .venv
    )
    uv pip install -e ".[dev]"
) else (
    echo [INFO] uv not found, using standard venv and pip.
    if not exist ".venv" (
        %PYTHON_CMD% -m venv .venv
    )
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip setuptools wheel
    pip install -e ".[dev]"
)
echo [OK] Backend environment ready (.venv)
echo.

@rem 2. Frontend Setup
cd /d "%ROOT_DIR%"
if exist "frontend\package.json" (
    echo [2/2] Setting up Frontend...
    cd /d "%ROOT_DIR%frontend"
    where npm >nul 2>&1
    if %ERRORLEVEL% NEQ 0 (
        echo [WARNING] npm is not installed. Please install Node.js to use frontend.
    ) else (
        echo Installing frontend npm dependencies...
        call npm install
        echo [OK] Frontend dependencies installed (node_modules)
    )
) else (
    echo [2/2] Frontend directory not detected (Headless mode). Skipping.
)

cd /d "%ROOT_DIR%"
echo.
echo ==========================================================
echo       🎉 Setup completed! Run the application:
echo         run.bat
echo ==========================================================
echo.
pause
