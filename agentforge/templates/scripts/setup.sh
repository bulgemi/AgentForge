#!/usr/bin/env bash
# ==============================================================================
# {{ project_name }} ⚡ One-Click Environment Setup (macOS / Linux)
# Installs backend Python virtual environment and frontend npm dependencies.
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
echo "      ⚡ {{ project_name }} - Environment Setup           "
echo "=========================================================="
echo -e "${NC}"

# 1. Backend Setup
echo -e "${BOLD}[1/2] Setting up Backend...${NC}"
cd "$SCRIPT_DIR/backend"

PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python 3.10+ required but not found.${NC}"
    exit 1
fi

if command -v uv >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Detected uv for ultra-fast backend dependency installation${NC}"
    if [ ! -d ".venv" ]; then
        uv venv .venv
    fi
    uv pip install -e ".[dev]"
else
    echo -e "${YELLOW}ℹ uv not found, using standard venv and pip.${NC}"
    if [ ! -d ".venv" ]; then
        $PYTHON_CMD -m venv .venv
    fi
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install --upgrade pip setuptools wheel
    pip install -e ".[dev]"
fi
echo -e "${GREEN}✓ Backend environment ready (.venv)${NC}\n"

# 2. Frontend Setup (if present)
cd "$SCRIPT_DIR"
if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
    echo -e "${BOLD}[2/2] Setting up Frontend...${NC}"
    cd "$SCRIPT_DIR/frontend"
    if ! command -v npm >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️ npm is not installed. Please install Node.js (v18+) to run frontend.${NC}"
    else
        echo -e "${CYAN}Installing frontend npm dependencies...${NC}"
        npm install
        echo -e "${GREEN}✓ Frontend dependencies installed (node_modules)${NC}\n"
    fi
else
    echo -e "${BOLD}[2/2] Frontend directory not detected (Headless mode). Skipping.${NC}\n"
fi

cd "$SCRIPT_DIR"
echo -e "${GREEN}${BOLD}=========================================================="
echo "      🎉 Setup completed! Run the application:           "
echo "        $ ./run.sh                                       "
echo "==========================================================${NC}"
