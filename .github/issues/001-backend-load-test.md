---
title: "feat(generator): add automated Locust load test template to backend"
labels: ["enhancement", "load-test", "backend", "generator"]
status: "completed"
created_at: "2026-09-13T18:35:00+09:00"
closed_at: "2026-09-13T18:37:30+09:00"
---

# feat(generator): Add Automated Locust Load Test Template to Backend

## Overview
Generate a complete Locust-based load testing suite under `backend/load_test/` when scaffolding new AgentForge projects.

## Scenario
1. Authenticate with ID/PW (`POST /api/v1/auth/login`)
2. Create conversation session (`POST /api/v1/chats`)
3. Sequentially ask 5 AgentForge questions over SSE streaming (`POST /api/v1/chats/{chat_id}/stream`)
   - Measure TTFT (Time To First Token)
   - Measure Total Stream Response Latency
4. Logout (`POST /api/v1/auth/logout`)

## Tasks
- [x] Create `agentforge/templates/backend/load_test/questions.json`
- [x] Create `agentforge/templates/backend/load_test/locustfile.py`
- [x] Create `agentforge/templates/backend/load_test/run.sh` & `run.bat`
- [x] Create `agentforge/templates/backend/load_test/README.md`
- [x] Update `agentforge/templates/backend/pyproject.toml`
- [x] Add unit test in `tests/test_generator.py`
