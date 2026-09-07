@echo off
@rem ==============================================================================
@rem AgentForge ⚡ Installation Script (Windows)
@rem Sets up virtual environment and installs AgentForge in editable mode with CLI.
@rem ==============================================================================

chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================================
echo           ⚡ AgentForge CLI & Environment Setup (Windows)
echo ==========================================================
echo.

@rem 1. Check Python installation
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
    echo [ERROR] Python is not found. Please install Python 3.12 or higher from https://python.org.
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('%PYTHON_CMD% --version 2^>^&1') do set "PY_VER=%%i"
echo [OK] Found Python %PY_VER% (%PYTHON_CMD%)

@rem Check Python version >= 3.12
%PYTHON_CMD% -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python 3.12+ is required. Current version is %PY_VER%.
    pause
    exit /b 1
)

@rem 2. Navigate to script directory
cd /d "%~dp0"

@rem 3. Check for uv or fallback to standard venv/pip
where uv >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [OK] Detected uv - using ultra-fast package manager
    if not exist ".venv" (
        echo Creating virtual environment (.venv)...
        uv venv .venv
    )
    echo Installing AgentForge in editable mode with development dependencies...
    uv pip install --python .venv -e ".[dev]"
) else (
    echo [INFO] uv not found. Falling back to standard python venv and pip.
    if not exist ".venv" (
        echo Creating virtual environment (.venv)...
        %PYTHON_CMD% -m venv .venv
    )
    echo Installing AgentForge in editable mode...
    call .venv\Scripts\activate.bat
    python -m pip install --upgrade pip >nul 2>&1
    pip install -e ".[dev]" || pip install -e .
)

echo.
echo ==========================================================
echo       🎉 AgentForge successfully installed!
echo ==========================================================
echo.
echo To activate the virtual environment:
echo   ^> .venv\Scripts\activate
echo   ^> af --help (or agentforge --help)
echo.
echo Create your first AI agent project:
echo   ^> af new my-agent --framework langgraph --frontend react
echo.
pause
