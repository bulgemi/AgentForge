@echo off
REM ==============================================================================
REM AgentForge Project-Scoped Runner (Windows Batch)
REM Tailored for lifecycle operations inside a scaffolded project.
REM Commands: sandbox, dev, build, deploy
REM Disallows: new (scaffolding must be run outside an existing project)
REM ==============================================================================

setlocal enabledelayedexpansion

set COMMAND=%~1

REM 1. Intercept 'new' command
if /i "%COMMAND%"=="new" (
    echo [AgentForge Runner] 오류: 'af.bat new'는 생성된 프로젝트 내부에서 사용할 수 없습니다.
    echo 새로운 AI 에이전트 프로젝트를 생성하려면 프로젝트 디렉토리 외부에서 전역 'af new'를 사용하세요.
    exit /b 1
)

REM 2. Project-scoped help message
if "%COMMAND%"=="" goto show_help
if "%COMMAND%"=="--help" goto show_help
if "%COMMAND%"=="-h" goto show_help
if "%COMMAND%"=="help" goto show_help
if "%COMMAND%"=="/?" goto show_help
goto execute_command

:show_help
echo ============================================================
echo   AgentForge Project Runner (af.bat)
echo ============================================================
echo 사용법: af.bat ^<command^> [options]
echo.
echo 사용 가능한 프로젝트 명령어:
echo   sandbox   클라우드(EKS/GKE/AKS)/로컬 K8s 샌드박스 관리 (up, watch, open, pause, resume, down)
echo   dev       로컬 개발 서버 실행 (Backend + Frontend)
echo   build     현재 프로젝트 Docker 컨테이너 이미지 빌드
echo   deploy    현재 프로젝트 Kubernetes 클러스터 배포
echo.
echo 옵션:
echo   -h, --help  도움말 표시
echo.
echo * 신규 프로젝트 생성('new')은 프로젝트 외부에서 전역 'af new'를 사용하세요.
exit /b 0

:execute_command
REM Priority 1: Global 'af' executable on PATH
where af >nul 2>&1
if %ERRORLEVEL% equ 0 (
    af %*
    exit /b %ERRORLEVEL%
)

REM Priority 2: AGENTFORGE_CLI environment variable
if defined AGENTFORGE_CLI (
    if exist "%AGENTFORGE_CLI%" (
        "%AGENTFORGE_CLI%" %*
        exit /b %ERRORLEVEL%
    )
)

set SCRIPT_DIR=%~dp0

REM Priority 3: Sibling AgentForge virtualenv
if exist "%SCRIPT_DIR%..\AgentForge\.venv\Scripts\af.exe" (
    "%SCRIPT_DIR%..\AgentForge\.venv\Scripts\af.exe" %*
    exit /b %ERRORLEVEL%
)

REM Priority 4: Backend virtualenv af
if exist "%SCRIPT_DIR%backend\.venv\Scripts\af.exe" (
    "%SCRIPT_DIR%backend\.venv\Scripts\af.exe" %*
    exit /b %ERRORLEVEL%
)

REM Priority 5: Python environment with agentforge
python -c "import agentforge" >nul 2>&1
if %ERRORLEVEL% equ 0 (
    python -m agentforge.cli.main %*
    exit /b %ERRORLEVEL%
)

REM Priority 6: 'uvx' from official GitHub repository
where uvx >nul 2>&1
if %ERRORLEVEL% equ 0 (
    uvx --from "git+https://github.com/bulgemi/AgentForge.git" af %*
    exit /b %ERRORLEVEL%
)

echo [AgentForge Runner] 'af' CLI를 실행할 수 없습니다.
echo 다음 중 하나의 방법으로 AgentForge CLI를 실행할 수 있습니다:
echo   1) pip install -e <AgentForge 저장소 경로>  (로컬 개발 연동, 권장)
echo   2) uv tool install git+https://github.com/bulgemi/AgentForge.git (전역 설치)
echo   3) uvx 설치 (무설치 즉시 실행)
exit /b 1
