# 🚀 AgentForge Backend Load Testing Suite

Automated Locust-based performance and stress testing suite for AgentForge backend services.

---

## 📋 Scenario Overview

Each virtual user executes a realistic, stateful conversational session:
1. **Login (`POST /api/v1/auth/login`)**: Authenticates with ID/PW and receives a JWT Bearer token.
2. **Create Chat (`POST /api/v1/chats`)**: Initializes a conversation thread with a unique ID.
3. **5-Turn SSE Streaming Dialogue (`POST /api/v1/chats/{chat_id}/stream`)**:
   - Submits 5 technical questions about AgentForge sequentially from `questions.json`.
   - Reads SSE (`text/event-stream`) token chunks in real-time.
   - **TTFT (Time To First Token)**: Measures latency from dispatch to the very first token chunk received.
   - **Total Streaming Latency**: Measures total elapsed time until the stream terminates.
4. **Logout (`POST /api/v1/auth/logout`)**: Terminates the session and revokes the active token.

---

## 🛠️ Prerequisites & Installation

Ensure the backend server is running (e.g., `http://localhost:8000`).

Install Locust and test dependencies:
```bash
# Inside backend/ directory:
pip install -e ".[loadtest]"

# Or standalone:
pip install locust
```

---

## ⚡ Quick Start

### 1. Interactive Web UI (Recommended for exploration)
```bash
# macOS / Linux
./run.sh

# Windows
run.bat
```
Open **[http://localhost:8089](http://localhost:8089)** in your browser, enter the number of users and spawn rate, and click **Start swarming**.

### 2. Headless Mode (Recommended for CI/CD & automated benchmarking)
```bash
# macOS / Linux
./run.sh --headless

# Windows
run.bat --headless
```
This runs with 5 virtual users for 1 minute and automatically exports a detailed summary report to `load_test_report.html`.

### 3. Custom Locust CLI Parameters
```bash
./run.sh -u 20 -r 4 -t 3m --headless --html benchmark_20users.html
```

---

## ⚙️ Configuration & Environment Variables

| Variable | Default | Description |
| :--- | :--- | :--- |
| `LOAD_TEST_HOST` | `http://localhost:8000` | Target backend URL |
| `LOAD_TEST_USER` | `admin` | Test username |
| `LOAD_TEST_PASSWORD` | `admin1234!` | Test user password |
| `LOAD_TEST_QUESTIONS_FILE` | `./questions.json` | Path to custom scenario questions JSON |

### Customizing Questions
Edit `questions.json` to change or expand the questions sent to the LLM agent without modifying any Python code.

---

## 📊 Key Metrics Tracked

- **`/api/v1/auth/login`**: Authentication latency and success rate.
- **`/api/v1/chats [Create]`**: Conversation initialization overhead.
- **`SSE_TTFT` (`/api/v1/chats/stream [TTFT - Q{n}]`)**: Time taken to receive the first token chunk (critical LLM responsiveness indicator).
- **`SSE_TOTAL` (`/api/v1/chats/stream [Total - Q{n}]`)**: Full stream generation and network completion duration.
- **`/api/v1/auth/logout`**: Clean session closure latency.
