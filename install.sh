#!/usr/bin/env bash
# ==============================================================================
# AgentForge ⚡ Installation Script (macOS / Linux)
# Sets up virtual environment and installs AgentForge in editable mode with CLI.
# ==============================================================================

set -euo pipefail

BOLD='\033[1m'
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}${BOLD}"
echo "=========================================================="
echo "          ⚡ AgentForge CLI & Environment Setup          "
echo "=========================================================="
echo -e "${NC}"

# 1. Check Python installation (3.12+)
PYTHON_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
else
    echo -e "${RED}[ERROR] Python is not installed. Please install Python 3.12 or higher.${NC}"
    exit 1
fi

PY_VER=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
PY_MAJOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.major)")
PY_MINOR=$($PYTHON_CMD -c "import sys; print(sys.version_info.minor)")

if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 12 ]; }; then
    echo -e "${RED}[ERROR] Python 3.12+ required. Current version: ${PY_VER}${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Found Python ${PY_VER} ($PYTHON_CMD)${NC}"

# 2. Check for uv or fallback to standard venv/pip
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if command -v uv >/dev/null 2>&1; then
    echo -e "${GREEN}✓ Detected uv - using ultra-fast package manager${NC}"
    if [ ! -d ".venv" ]; then
        echo -e "${CYAN}Creating virtual environment (.venv)...${NC}"
        uv venv .venv
    fi
    echo -e "${CYAN}Installing AgentForge in editable mode with development dependencies...${NC}"
    uv pip install --python .venv -e ".[dev]"
else
    echo -e "${YELLOW}ℹ uv not found. Falling back to standard python venv and pip.${NC}"
    if [ ! -d ".venv" ]; then
        echo -e "${CYAN}Creating virtual environment (.venv)...${NC}"
        $PYTHON_CMD -m venv .venv
    fi
    echo -e "${CYAN}Installing AgentForge in editable mode...${NC}"
    # shellcheck disable=SC1091
    source .venv/bin/activate
    pip install --upgrade pip >/dev/null 2>&1 || true
    pip install -e ".[dev]" || pip install -e .
fi

echo ""
echo -e "${GREEN}${BOLD}=========================================================="
echo "      🎉 AgentForge successfully installed!              "
echo "==========================================================${NC}"
echo ""
echo -e "To activate the environment and start building agents:"
echo -e "  ${CYAN}$ source .venv/bin/activate${NC}"
echo -e "  ${CYAN}$ af --help${NC} (or ${CYAN}agentforge --help${NC})"
echo ""
echo -e "Create your first AI agent project:"
echo -e "  ${CYAN}$ af new my-agent --framework langgraph --frontend react${NC}"
echo ""
