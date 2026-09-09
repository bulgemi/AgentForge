@echo off
@rem ==============================================================================
@rem {{ project_name }} ⚡ One-Click Local Development Server (Windows)
@rem Automatically verifies dependencies and starts Backend and Frontend servers.
@rem ==============================================================================

chcp 65001 >nul
setlocal enabledelayedexpansion

echo ==========================================================
echo       ⚡ Starting {{ project_name }} Local Dev Servers
echo ==========================================================
echo.

set "ROOT_DIR=%~dp0"
cd /d "%ROOT_DIR%"

@rem 1. Check if setup is needed
set "NEEDS_SETUP=0"
if not exist "backend\.venv" (
    set "NEEDS_SETUP=1"
)
if not exist "backend\.env" (
    set "NEEDS_SETUP=1"
)
if exist "frontend\package.json" (
    if not exist "frontend\node_modules" (
        set "NEEDS_SETUP=1"
    )
    if not exist "frontend\.env" (
        set "NEEDS_SETUP=1"
    )
)

if "%NEEDS_SETUP%"=="1" (
    echo [INFO] Environment not fully initialized. Running setup first...
    call setup.bat
    echo.
)

@rem 1.1 Start Docker Compose infrastructure if Docker is available
where docker >nul 2>nul
if %errorlevel% equ 0 (
    docker info >nul 2>nul
    if !errorlevel! equ 0 (
        if exist "docker-compose.yml" (
            echo [INFO] Starting local infrastructure (PostgreSQL, Redis, Langfuse, OpenSearch)...
            docker compose --profile infra up -d
            echo.
        )
    ) else (
        echo [WARN] Docker is installed but the Docker daemon is not running.
        echo [WARN] Skipping infrastructure startup. Start Docker Desktop to run Postgres, Redis, Langfuse, and OpenSearch.
        echo.
    )
) else (
    echo [WARN] Docker is not installed. Skipping infrastructure startup.
    echo.
)

@rem 2. Launch Backend
echo [INFO] Launching Backend API in background terminal...
cd /d "%ROOT_DIR%backend"
if exist ".venv\Scripts\uvicorn.exe" (
    start "AgentForge Backend [FastAPI]" cmd /k ".venv\Scripts\uvicorn.exe src.main:app --reload --port 8000"
) else (
    start "AgentForge Backend [FastAPI]" cmd /k "python -m uvicorn src.main:app --reload --port 8000"
)

@rem 3. Launch Frontend (if present)
cd /d "%ROOT_DIR%"
if exist "frontend\package.json" (
    echo [INFO] Launching Frontend SPA in background terminal...
    cd /d "%ROOT_DIR%frontend"
    start "AgentForge Frontend [Vite]" cmd /k "npm run dev"
) else if exist "frontend\app.py" (
    echo [INFO] Launching Streamlit UI in background terminal...
    cd /d "%ROOT_DIR%frontend"
    start "AgentForge Frontend [Streamlit]" cmd /k "streamlit run app.py"
)

cd /d "%ROOT_DIR%"
timeout /t 2 >nul

echo.
echo ==========================================================
echo       🎉 All Services are running!
echo ==========================================================
echo • Backend API Docs: http://localhost:8000/docs
echo • Healthcheck:      http://localhost:8000/health
if exist "frontend\package.json" (
    echo • Frontend Chat:    http://localhost:5173/
    echo • Admin Console:    http://localhost:5173/admin.html
) else if exist "frontend\app.py" (
    echo • Streamlit UI:     http://localhost:8501/
)
echo • Langfuse UI:      http://localhost:3000
echo • OpenSearch GUI:   http://localhost:5601
echo ==========================================================
echo.
echo Close the respective terminal windows to stop the servers.
echo.
pause
