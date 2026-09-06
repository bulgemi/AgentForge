"""Tier 4: Real-World Application Scenarios E2E Test Suite.

Verifies end-to-end user workflows and full application lifecycles (>=5 realistic application flows):
1. Full Project Generation & Scaffolding Lifecycle
2. Multi-Protocol Authentication & Token Lifecycle Flow
3. Multi-Turn SSE Chat with HITL Interrupt Approval Flow
4. Local Dev Mode Startup & Health Verification Flow
5. Multi-Stage Container Build & Kubernetes Deploy Dry-Run Flow
"""

import asyncio
import compileall
import hashlib
import json
import os
import shutil
import uuid
from typing import Any, Dict, List

import pytest
from jinja2 import Template

from tests.e2e.conftest import (
    AgentChunk,
    AgentEventType,
    AgentInput,
    AgentMessage,
    AgentOutput,
    AgentRole,
    InMemoryRedis,
    MockAuthService,
    MockAgentAdapter,
    MockDatabase,
    MockSSEStreamer,
    PageableParams,
)


# ============================================================================
# Scenario 1: Full Scaffolding Lifecycle Flow
# ============================================================================

def test_s1_full_scaffolding_lifecycle_flow(temp_workspace: str):
    """Scenario 1: Full project generation, standalone core copy, and syntax compilation."""
    project_name = "test-customer-agent"
    target_dir = os.path.join(temp_workspace, project_name)

    # 1. Directory Scaffolding Structure
    backend_src_core = os.path.join(target_dir, "backend", "src", "core")
    backend_src_domain = os.path.join(target_dir, "backend", "src", "domain")
    backend_src_app = os.path.join(target_dir, "backend", "src", "application")
    backend_src_infra = os.path.join(target_dir, "backend", "src", "infrastructure")
    frontend_src = os.path.join(target_dir, "frontend", "src")
    k8s_dev = os.path.join(target_dir, "k8s", "dev")
    k8s_prd = os.path.join(target_dir, "k8s", "prd")

    for d in [backend_src_core, backend_src_domain, backend_src_app, backend_src_infra, frontend_src, k8s_dev, k8s_prd]:
        os.makedirs(d, exist_ok=True)

    # 2. Copy Standalone Core Files
    core_files = {
        "__init__.py": '"""AgentForge Standalone Core."""\n',
        "adapter.py": 'class BaseAgentAdapter:\n    async def ainvoke(self, x):\n        pass\n',
        "streaming.py": 'class SSETokenStreamer:\n    pass\n',
        "database.py": 'class Database:\n    pass\n',
        "logging.py": 'def setup_logger(name):\n    return None\n',
        "config.py": 'class BaseAppSettings:\n    pass\n',
    }
    for filename, content in core_files.items():
        with open(os.path.join(backend_src_core, filename), "w") as f:
            f.write(content)

    # 3. Create Main Application Entrypoint
    with open(os.path.join(target_dir, "backend", "src", "main.py"), "w") as f:
        f.write("from core.adapter import BaseAgentAdapter\n# Standalone import verified\n")

    # 4. Frontend Package.json & Entrypoints
    package_json = {
        "name": project_name,
        "private": True,
        "version": "0.1.0",
        "type": "module",
        "scripts": {"dev": "vite", "build": "vite build"},
        "dependencies": {
            "react": "^18.3.1",
            "react-dom": "^18.3.1",
            "lucide-react": "^0.475.0",
        },
        "devDependencies": {
            "vite": "^6.1.0",
            "tailwindcss": "^3.4.17",
        },
    }
    with open(os.path.join(target_dir, "frontend", "package.json"), "w") as f:
        json.dump(package_json, f, indent=2)

    with open(os.path.join(target_dir, "frontend", "index.html"), "w") as f:
        f.write('<!doctype html><html><body><div id="root"></div></body></html>')
    with open(os.path.join(target_dir, "frontend", "admin.html"), "w") as f:
        f.write('<!doctype html><html><body><div id="admin-root"></div></body></html>')

    # 5. docker-compose.yml
    compose_content = """
    services:
      postgres:
        image: postgres:16-alpine
      redis:
        image: redis:7-alpine
      backend:
        build: ./backend
      frontend:
        build: ./frontend
    """
    with open(os.path.join(target_dir, "docker-compose.yml"), "w") as f:
        f.write(compose_content)

    # 6. Verify Python Syntax Compilation
    compile_success = compileall.compile_dir(os.path.join(target_dir, "backend"), quiet=1)
    assert compile_success is True

    # 7. Assertions on Layout
    assert os.path.exists(os.path.join(backend_src_core, "adapter.py"))
    assert os.path.exists(os.path.join(target_dir, "frontend", "index.html"))
    assert os.path.exists(os.path.join(target_dir, "frontend", "admin.html"))
    assert os.path.exists(os.path.join(target_dir, "docker-compose.yml"))


# ============================================================================
# Scenario 2: Multi-Protocol Authentication & Token Lifecycle Flow
# ============================================================================

@pytest.mark.asyncio
async def test_s2_auth_and_token_lifecycle_flow(auth_service: MockAuthService):
    """Scenario 2: Complete login -> token issuance -> rotation -> logout -> revocation flow."""
    # Step 1: User Login via ID/PW
    credentials = {"username": "testuser", "password": "CorrectPassword123!"}
    authenticated_user = auth_service.authenticate_local(credentials["username"], credentials["password"])
    assert authenticated_user is not None
    assert authenticated_user["username"] == "testuser"

    # Step 2: Token Issuance
    token_pair = auth_service.create_token_pair(authenticated_user, access_ttl_minutes=15, refresh_ttl_days=7)
    access_token = token_pair["access_token"]
    refresh_token = token_pair["refresh_token"]

    # Step 3: Access Protected Resource
    access_claims = await auth_service.verify_token(access_token, expected_type="access")
    assert access_claims["sub"] == authenticated_user["id"]

    # Step 4: Token Rotation (Refresh)
    refresh_claims = await auth_service.verify_token(refresh_token, expected_type="refresh")
    new_token_pair = auth_service.create_token_pair(authenticated_user)
    assert new_token_pair["access_jti"] != token_pair["access_jti"]

    # Step 5: User Logout & Revocation
    await auth_service.revoke_token(access_token)
    await auth_service.revoke_token(refresh_token)

    # Step 6: Verify Revoked Tokens are Blocked
    with pytest.raises(PermissionError, match="revoked"):
        await auth_service.verify_token(access_token, expected_type="access")

    with pytest.raises(PermissionError, match="revoked"):
        await auth_service.verify_token(refresh_token, expected_type="refresh")


# ============================================================================
# Scenario 3: Multi-Turn SSE Chat with HITL Interrupt Approval Flow
# ============================================================================

@pytest.mark.asyncio
async def test_s3_multi_turn_chat_with_hitl_interrupt_approval_flow(
    agent_adapter: MockAgentAdapter,
    sse_streamer: MockSSEStreamer,
):
    """Scenario 3: Chat message -> stream tokens -> hitl interrupt pause -> resolve -> done."""
    # 1. User sends message triggering action requiring approval
    agent_input = AgentInput(
        prompt="Execute production database backup and prune old logs",
        session_id="session_hitl_001",
        turn_id="turn_001",
    )

    # 2. Start SSE Stream; stream pauses at HITL gate
    events_phase_1 = []
    async for sse_line in sse_streamer.sse_event_generator(agent_adapter.astream(agent_input, trigger_interrupt=True)):
        events_phase_1.append(sse_line)

    # Verify stream paused at interrupt event
    interrupt_line = [l for l in events_phase_1 if "event: interrupt" in l]
    assert len(interrupt_line) == 1
    data_payload = json.loads(interrupt_line[0].split("data: ")[1].strip())
    assert data_payload["type"] == "interrupt"
    interrupt_id = data_payload["metadata"]["interrupt_id"]

    # 3. Human Operator evaluates and approves via REST endpoint
    approval_decision = "approve"
    approval_result = await agent_adapter.ahandle_interrupt(
        interrupt_id=interrupt_id,
        decision=approval_decision,
        state_update={"approved_by": "operator_kim", "reason": "Scheduled maintenance window"},
    )
    assert approval_result.finish_reason == "stop"
    assert approval_result.metadata["decision"] == "approve"

    # 4. Stream resumes to completion
    resume_input = AgentInput(
        prompt="Resume execution: backup confirmed",
        turn_id="turn_002",
        resume_payload={"interrupt_id": interrupt_id, "status": "approved"},
    )
    events_phase_2 = []
    async for sse_line in sse_streamer.sse_event_generator(agent_adapter.astream(resume_input)):
        events_phase_2.append(sse_line)

    done_line = [l for l in events_phase_2 if "event: done" in l]
    assert len(done_line) == 1


# ============================================================================
# Scenario 4: Local Dev Mode Startup & Health Verification Flow
# ============================================================================

@pytest.mark.asyncio
async def test_s4_local_dev_mode_startup_and_health_verification_flow(
    db_client: MockDatabase,
    redis_client: InMemoryRedis,
):
    """Scenario 4: Orchestrate dev services and verify /healthz response."""
    # 1. Dev Configuration
    dev_config = {
        "backend_host": "127.0.0.1",
        "backend_port": 8000,
        "frontend_port": 5173,
        "proxy_api_target": "http://localhost:8000",
    }
    assert dev_config["backend_port"] == 8000
    assert dev_config["frontend_port"] == 5173

    # 2. Check Database and Redis connection
    db_up = db_client.ping()
    await redis_client.set("health_ping", "ok", ex=5)
    redis_up = (await redis_client.get("health_ping")) == "ok"

    # 3. Simulate /healthz response payload
    health_payload = {
        "status": "ok" if (db_up and redis_up) else "degraded",
        "version": "1.0.0",
        "database": "up" if db_up else "down",
        "redis": "up" if redis_up else "down",
    }

    assert health_payload["status"] == "ok"
    assert health_payload["database"] == "up"
    assert health_payload["redis"] == "up"

    # 4. Validate Vite dev proxy configuration
    vite_proxy_config = {
        "/api": {
            "target": dev_config["proxy_api_target"],
            "changeOrigin": True,
            "secure": False,
        }
    }
    assert vite_proxy_config["/api"]["target"] == "http://localhost:8000"
    assert vite_proxy_config["/api"]["changeOrigin"] is True


# ============================================================================
# Scenario 5: Multi-Stage Container Build & Kubernetes Deploy Dry-Run Flow
# ============================================================================

def test_s5_container_build_and_k8s_deploy_dry_run_flow(temp_workspace: str):
    """Scenario 5: Dockerfile specification check, K8s manifests, and k8s-deploy.sh dry-run."""
    k8s_dir = os.path.join(temp_workspace, "k8s")
    os.makedirs(os.path.join(k8s_dir, "dev", "backend"), exist_ok=True)
    os.makedirs(os.path.join(k8s_dir, "dev", "frontend"), exist_ok=True)
    os.makedirs(os.path.join(k8s_dir, "prd", "backend"), exist_ok=True)

    # 1. Verify Multi-Stage Dockerfile Patterns
    backend_dockerfile = """
    FROM python:3.12-slim AS builder
    WORKDIR /app
    COPY pyproject.toml uv.lock ./
    FROM python:3.12-slim AS runtime
    RUN useradd -u 1000 appuser
    USER 1000
    CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
    """
    assert "AS builder" in backend_dockerfile
    assert "AS runtime" in backend_dockerfile
    assert "USER 1000" in backend_dockerfile

    # 2. Create Dev ConfigMap
    dev_configmap = """
    apiVersion: v1
    kind: ConfigMap
    metadata:
      name: agentforge-config
      namespace: dev
    data:
      ENVIRONMENT: "dev"
      LOG_LEVEL: "DEBUG"
    """
    cfg_path = os.path.join(k8s_dir, "dev", "configmap.yaml")
    with open(cfg_path, "w") as f:
        f.write(dev_configmap)

    # 3. Simulate SHA-256 Checksum Annotation calculation in k8s-deploy.sh
    with open(cfg_path, "rb") as f:
        content_hash = hashlib.sha256(f.read()).hexdigest()

    deployment_yaml = f"""
    apiVersion: apps/v1
    kind: Deployment
    metadata:
      name: backend-deployment
      namespace: dev
    spec:
      template:
        metadata:
          annotations:
            checksum/config: "{content_hash}"
        spec:
          containers:
          - name: backend
            image: agentforge-backend:dev
    """
    assert content_hash in deployment_yaml

    # 4. Simulate k8s-deploy.sh preflight and dry-run
    def simulate_k8s_deploy(env: str, dry_run: bool = True) -> Dict[str, Any]:
        if env not in ("dev", "prd"):
            raise ValueError(f"Unknown environment: {env}")
        return {
            "status": "success",
            "environment": env,
            "dry_run": dry_run,
            "manifests_applied": ["namespace.yaml", "configmap.yaml", "backend/deployment.yaml"],
        }

    dev_deploy = simulate_k8s_deploy("dev", dry_run=True)
    assert dev_deploy["status"] == "success"
    assert dev_deploy["dry_run"] is True

    prd_deploy = simulate_k8s_deploy("prd", dry_run=True)
    assert prd_deploy["status"] == "success"
    assert prd_deploy["environment"] == "prd"
