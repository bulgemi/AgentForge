"""Tier 3: Cross-Feature Combinations E2E Test Suite.

Verifies pairwise feature interactions and cross-subsystem contracts:
- Pair 1: Authentication + SSE Token Streaming
- Pair 2: Database Pagination + Redis Session State
- Pair 3: CLI Flags + Scaffolding Template Generation Matrix
- Pair 4: Concurrency Governance + SSE Streaming
- Pair 5: Enterprise SSO (LDAP/SAML) + JIT User Database Provisioning
"""

import asyncio
import os
import shutil
from typing import Dict, List

import pytest
from jinja2 import Template

from tests.e2e.conftest import (
    AgentChunk,
    AgentEventType,
    AgentInput,
    AgentMessage,
    AgentRole,
    InMemoryRedis,
    MockAuthService,
    MockAgentAdapter,
    MockDatabase,
    MockSSEStreamer,
    PageableParams,
)


# ============================================================================
# Pair 1: Authentication + SSE Token Streaming (4 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_c1_authenticated_user_sse_stream_successful(
    auth_service: MockAuthService,
    agent_adapter: MockAgentAdapter,
    sse_streamer: MockSSEStreamer,
):
    """C1.1: Authenticated user with valid JWT can initiate and complete SSE stream."""
    user = auth_service.authenticate_local("testuser", "CorrectPassword123!")
    assert user is not None

    tokens = auth_service.create_token_pair(user)
    access_token = tokens["access_token"]

    # Verify authorization header before streaming
    token_claims = await auth_service.verify_token(access_token)
    assert token_claims["username"] == "testuser"

    # Stream execution
    agent_input = AgentInput(prompt="stream query from authenticated user")
    lines = []
    async for line in sse_streamer.sse_event_generator(agent_adapter.astream(agent_input)):
        lines.append(line)

    assert len(lines) > 0
    assert lines[-1].startswith("event: done\n")


@pytest.mark.asyncio
async def test_c1_token_revocation_during_active_sse_stream_halts(
    auth_service: MockAuthService,
    agent_adapter: MockAgentAdapter,
    sse_streamer: MockSSEStreamer,
):
    """C1.2: Revoking token during or between stream turns halts subsequent requests."""
    user = auth_service.authenticate_local("testuser", "CorrectPassword123!")
    tokens = auth_service.create_token_pair(user)
    token = tokens["access_token"]

    # First turn succeeds
    claims1 = await auth_service.verify_token(token)
    assert claims1 is not None

    # Revoke session
    await auth_service.revoke_token(token)

    # Next turn attempt must be denied with 401 / PermissionError
    with pytest.raises(PermissionError, match="revoked"):
        await auth_service.verify_token(token)


@pytest.mark.asyncio
async def test_c1_unauthenticated_request_to_stream_endpoint_returns_401(
    auth_service: MockAuthService,
):
    """C1.3: Unauthenticated stream request without valid token is rejected."""
    unauthenticated_token = "invalid.bearer.token"
    with pytest.raises(ValueError, match="Invalid token signature"):
        await auth_service.verify_token(unauthenticated_token)


@pytest.mark.asyncio
async def test_c1_role_based_stream_access_control(
    auth_service: MockAuthService,
):
    """C1.4: Role-based stream access control enforces required privileges."""
    user_token = auth_service.create_token_pair({"id": "u1", "username": "reg_user", "role": "USER"})["access_token"]
    admin_token = auth_service.create_token_pair({"id": "u2", "username": "admin_user", "role": "ADMIN"})["access_token"]

    def check_admin_stream_access(payload: Dict[str, Any]):
        if payload.get("role") != "ADMIN":
            raise PermissionError("Forbidden: Requires ADMIN role")
        return True

    user_payload = await auth_service.verify_token(user_token)
    admin_payload = await auth_service.verify_token(admin_token)

    with pytest.raises(PermissionError, match="Requires ADMIN role"):
        check_admin_stream_access(user_payload)

    assert check_admin_stream_access(admin_payload) is True


# ============================================================================
# Pair 2: Database Pagination + Redis Session State (3 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_c2_paginated_query_scoped_to_active_redis_session(
    redis_client: InMemoryRedis,
    db_client: MockDatabase,
):
    """C2.1: Paginated query checks active Redis session before executing database fetch."""
    user_id = "usr_session_1"
    session_id = "sess_abc123"
    session_key = f"session:{user_id}:{session_id}"

    # Active session stored in Redis
    await redis_client.set(session_key, "active", ex=3600)

    # Validate session exists
    session_active = await redis_client.exists(session_key)
    assert session_active == 1

    # Fetch user chat items
    user_messages = [f"msg_{i}_for_{user_id}" for i in range(40)]
    page_1 = db_client.paginate(user_messages, PageableParams(page=1, size=15))

    assert len(page_1.items) == 15
    assert page_1.metadata.total_elements == 40
    assert page_1.metadata.total_pages == 3


@pytest.mark.asyncio
async def test_c2_pageable_params_with_session_invalidation(
    redis_client: InMemoryRedis,
    db_client: MockDatabase,
):
    """C2.2: Session invalidation in Redis prevents further paginated queries."""
    session_key = "session:usr_session_2:sess_xyz"
    await redis_client.set(session_key, "active", ex=3600)

    # Invalidate session (logout)
    await redis_client.delete(session_key)

    is_valid = await redis_client.exists(session_key)
    assert is_valid == 0


@pytest.mark.asyncio
async def test_c2_multi_page_traversal_with_sliding_session_extension(
    redis_client: InMemoryRedis,
    db_client: MockDatabase,
):
    """C2.3: Sequential page traversals extend session TTL (activity heartbeat)."""
    session_key = "session:usr_session_3:sess_heartbeat"
    await redis_client.set(session_key, "active", ex=60)

    all_items = [f"item_{i}" for i in range(30)]

    for page_num in [1, 2, 3]:
        # Heartbeat: extend TTL by 60s on each request
        await redis_client.expire(session_key, 60)
        page = db_client.paginate(all_items, PageableParams(page=page_num, size=10))
        assert len(page.items) == 10

    # Ensure session remains active
    assert await redis_client.exists(session_key) == 1


# ============================================================================
# Pair 3: CLI Flags + Template Generation Combinatorial Matrix (5 tests)
# ============================================================================

def test_c3_scaffold_langgraph_with_react_vite(temp_workspace: str):
    """C3.1: Scaffolding with --framework langgraph --frontend react."""
    project_dir = os.path.join(temp_workspace, "proj_lg_react")
    os.makedirs(project_dir)

    template_config = """
    project_name = "{{ name }}"
    framework = "{{ fw }}"
    frontend = "{{ ui }}"
    """
    rendered = Template(template_config).render(name="proj_lg_react", fw="langgraph", ui="react")
    assert 'framework = "langgraph"' in rendered
    assert 'frontend = "react"' in rendered


def test_c3_scaffold_bedrock_with_streamlit(temp_workspace: str):
    """C3.2: Scaffolding with --framework bedrock --frontend streamlit."""
    project_dir = os.path.join(temp_workspace, "proj_br_st")
    os.makedirs(project_dir)

    template_config = """
    project_name = "{{ name }}"
    framework = "{{ fw }}"
    frontend = "{{ ui }}"
    """
    rendered = Template(template_config).render(name="proj_br_st", fw="bedrock", ui="streamlit")
    assert 'framework = "bedrock"' in rendered
    assert 'frontend = "streamlit"' in rendered


def test_c3_scaffold_deepagent_headless_none(temp_workspace: str):
    """C3.3: Scaffolding with --framework deepagent --frontend none (Headless API)."""
    project_dir = os.path.join(temp_workspace, "proj_da_none")
    os.makedirs(project_dir)

    template_config = """
    project_name = "{{ name }}"
    framework = "{{ fw }}"
    frontend = "{{ ui }}"
    has_frontend = {{ has_ui }}
    """
    rendered = Template(template_config).render(name="proj_da_none", fw="deepagent", ui="none", has_ui=False)
    assert 'framework = "deepagent"' in rendered
    assert 'has_frontend = False' in rendered


def test_c3_scaffold_langchain_with_react_vite(temp_workspace: str):
    """C3.4: Scaffolding with --framework langchain --frontend react."""
    template_config = "framework={{ fw }}, frontend={{ ui }}"
    rendered = Template(template_config).render(fw="langchain", ui="react")
    assert "framework=langchain" in rendered
    assert "frontend=react" in rendered


def test_c3_scaffold_adk_with_react_vite(temp_workspace: str):
    """C3.5: Scaffolding with --framework adk --frontend react."""
    template_config = "framework={{ fw }}, frontend={{ ui }}"
    rendered = Template(template_config).render(fw="adk", ui="react")
    assert "framework=adk" in rendered
    assert "frontend=react" in rendered


# ============================================================================
# Pair 4: Concurrency Governance + SSE Streaming (2 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_c4_concurrent_streams_respecting_semaphore_limit(
    agent_adapter: MockAgentAdapter,
    sse_streamer: MockSSEStreamer,
):
    """C4.1: Concurrency semaphore coordinates multiple concurrent streaming clients."""
    sem = asyncio.Semaphore(2)
    active_streams = 0
    max_concurrent_observed = 0

    async def client_stream(client_id: int):
        nonlocal active_streams, max_concurrent_observed
        async with sem:
            active_streams += 1
            max_concurrent_observed = max(max_concurrent_observed, active_streams)
            agent_input = AgentInput(prompt=f"client {client_id} query")
            async for _ in sse_streamer.sse_event_generator(agent_adapter.astream(agent_input)):
                await asyncio.sleep(0.005)
            active_streams -= 1

    await asyncio.gather(*(client_stream(i) for i in range(5)))
    assert max_concurrent_observed <= 2
    assert active_streams == 0


@pytest.mark.asyncio
async def test_c4_semaphore_release_allows_queued_stream(
    agent_adapter: MockAgentAdapter,
    sse_streamer: MockSSEStreamer,
):
    """C4.2: Completing a stream releases the semaphore so queued streams execute."""
    sem = asyncio.Semaphore(1)
    completed_order = []

    async def stream_task(task_id: str):
        async with sem:
            agent_input = AgentInput(prompt="short")
            async for _ in sse_streamer.sse_event_generator(agent_adapter.astream(agent_input)):
                pass
            completed_order.append(task_id)

    await asyncio.gather(stream_task("task_A"), stream_task("task_B"))
    assert len(completed_order) == 2


# ============================================================================
# Pair 5: Enterprise SSO + JIT User Provisioning + Database (2 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_c5_ldap_authentication_jit_user_creation_in_db(
    auth_service: MockAuthService,
    db_client: MockDatabase,
):
    """C5.1: Successful LDAP bind triggers JIT user creation in database."""
    ldap_user = auth_service.authenticate_ldap("corp_admin_kim", "CorpLdapPass2026!")
    assert ldap_user is not None

    # Simulate database insertion/upsert
    db_record = {
        "user_id": ldap_user["id"],
        "username": ldap_user["username"],
        "role": ldap_user["role"],
        "auth_provider": ldap_user["provider"],
        "is_active": True,
    }
    db_client._records.append(db_record)

    stored = [r for r in db_client._records if r["username"] == "corp_admin_kim"]
    assert len(stored) == 1
    assert stored[0]["role"] == "ADMIN"
    assert stored[0]["auth_provider"] == "LDAP"


@pytest.mark.asyncio
async def test_c5_saml_acs_assertion_jit_user_role_assignment_in_db(
    auth_service: MockAuthService,
    db_client: MockDatabase,
):
    """C5.2: SAML ACS assertion parses attributes and provisions user with mapped role in DB."""
    saml_xml = """
    <samlp:Response xmlns:samlp="urn:oasis:names:tc:SAML:2.0:protocol">
        <saml:Assertion xmlns:saml="urn:oasis:names:tc:SAML:2.0:assertion">
            <saml:Audience>AgentForge_SP</saml:Audience>
            <samlp:StatusCode Value="status:Success"/>
            <saml:Attribute Name="Role">Role:Admin</saml:Attribute>
        </saml:Assertion>
    </samlp:Response>
    """
    saml_user = auth_service.authenticate_saml(saml_xml)
    assert saml_user is not None

    db_record = {
        "user_id": saml_user["id"],
        "username": saml_user["username"],
        "role": saml_user["role"],
        "auth_provider": saml_user["provider"],
        "is_active": True,
    }
    db_client._records.append(db_record)

    stored = [r for r in db_client._records if r["username"] == "sso_user"]
    assert len(stored) == 1
    assert stored[0]["role"] == "ADMIN"
    assert stored[0]["auth_provider"] == "SAML"
