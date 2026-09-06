#!/usr/bin/env bash
# ==============================================================================
# {{ project_name }} ⚡ One-Click Local Development Server (macOS / Linux)
# Automatically verifies dependencies and starts Backend and Frontend servers.
# ==============================================================================

set -euo pipefail

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}${BOLD}"
echo "=========================================================="
echo "      ⚡ Starting {{ project_name }} Local Dev Servers     "
echo "=========================================================="
echo -e "${NC}"

# 1. Dependency check & auto-setup
NEEDS_SETUP=false
if [ ! -d "backend/.venv" ]; then
    NEEDS_SETUP=true
fi
if [ -d "frontend" ] && [ -f "frontend/package.json" ] && [ ! -d "frontend/node_modules" ]; then
    NEEDS_SETUP=true
fi

if [ "$NEEDS_SETUP" = true ]; then
    echo -e "${YELLOW}ℹ Environment not fully initialized. Running setup first...${NC}\n"
    bash "$SCRIPT_DIR/setup.sh"
    echo ""
fi

# Trap cleanup to terminate child processes on exit/interrupt
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
    echo -e "\n${YELLOW}Shutting down development servers...${NC}"
    if [ -n "$BACKEND_PID" ]; then
        kill "$BACKEND_PID" 2>/dev/null || true
    fi
    if [ -n "$FRONTEND_PID" ]; then
        kill "$FRONTEND_PID" 2>/dev/null || true
    fi
    wait 2>/dev/null || true
    echo -e "${GREEN}✓ All services stopped cleanly.${NC}"
}
trap cleanup EXIT INT TERM

# 2. Launch Backend (FastAPI Uvicorn)
echo -e "${CYAN}🚀 Launching Backend API (FastAPI)...${NC}"
cd "$SCRIPT_DIR/backend"
if [ -f ".venv/bin/uvicorn" ]; then
    .venv/bin/uvicorn src.main:app --reload --port 8000 &
    BACKEND_PID=$!
elif command -v uv >/dev/null 2>&1; then
    uv run uvicorn src.main:app --reload --port 8000 &
    BACKEND_PID=$!
else
    python3 -m uvicorn src.main:app --reload --port 8000 &
    BACKEND_PID=$!
fi

# 3. Launch Frontend (if applicable)
cd "$SCRIPT_DIR"
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo -e "${CYAN}🚀 Launching Frontend SPA (Vite)...${NC}"
    cd "$SCRIPT_DIR/frontend"
    npm run dev &
    FRONTEND_PID=$!
elif [ -d "frontend" ] && [ -f "frontend/app.py" ]; then
    echo -e "${CYAN}🚀 Launching Streamlit UI...${NC}"
    cd "$SCRIPT_DIR/frontend"
    streamlit run app.py &
    FRONTEND_PID=$!
fi

cd "$SCRIPT_DIR"
sleep 2

echo -e "\n${GREEN}${BOLD}=========================================================="
echo "      🎉 All Services are running!                        "
echo "==========================================================${NC}"
echo -e "• ${BOLD}Backend API Docs${NC}: ${CYAN}http://localhost:8000/docs${NC}"
echo -e "• ${BOLD}Healthcheck${NC}:      ${CYAN}http://localhost:8000/health${NC}"
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo -e "• ${BOLD}Frontend Chat${NC}:    ${CYAN}http://localhost:5173/${NC}"
    echo -e "• ${BOLD}Admin Console${NC}:    ${CYAN}http://localhost:5173/admin.html${NC}"
elif [ -d "frontend" ] && [ -f "frontend/app.py" ]; then
    echo -e "• ${BOLD}Streamlit UI${NC}:     ${CYAN}http://localhost:8501/${NC}"
fi
echo -e "=========================================================="
echo -e "${YELLOW}Press Ctrl+C to stop all servers.${NC}\n"

# Wait indefinitely for background processes
wait
