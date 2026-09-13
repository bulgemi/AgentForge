#!/usr/bin/env bash
# AgentForge Backend Load Test Runner (Linux / macOS)
# Usage:
#   ./run.sh                  # Run interactive Web UI (http://localhost:8089)
#   ./run.sh --web            # Run interactive Web UI
#   ./run.sh --headless       # Run headless with default 5 users, 1m duration, output report.html
#   ./run.sh -u 10 -r 2 -t 2m --headless --html report.html # Custom Locust options

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if locust is available
if ! command -v locust &> /dev/null; then
    echo "⚠️  Locust is not installed in your current environment."
    echo "   Please install it using one of the following commands:"
    echo "     pip install locust"
    echo "   or inside project backend:"
    echo "     pip install -e '.[loadtest]'"
    exit 1
fi

HOST="${LOAD_TEST_HOST:-http://localhost:8000}"
echo "🚀 AgentForge Load Test Target: $HOST"

if [ $# -eq 0 ] || [ "$1" = "--web" ]; then
    echo "🌐 Launching Locust Web UI at http://localhost:8089"
    echo "   Open your browser to start and inspect the load test."
    exec locust -f locustfile.py --host "$HOST"
fi

if [ "$1" = "--headless" ]; then
    shift
    REPORT_FILE="load_test_report.html"
    echo "📊 Running Headless Load Test (5 Users, Spawn Rate 1, Duration 1m)..."
    exec locust -f locustfile.py \
        --host "$HOST" \
        --headless \
        -u 5 \
        -r 1 \
        -t 1m \
        --html "$REPORT_FILE" \
        "$@"
fi

# Pass through custom arguments
exec locust -f locustfile.py --host "$HOST" "$@"
