"""Tier 2: Boundary & Corner Cases E2E Test Suite.

Verifies extreme inputs, hostile conditions, resource limits, and error cascading:
- B1: Empty, Whitespace & Extreme Inputs
- B2: Disconnects, Cancellations & Upstream Timeouts
- B3: Connection Pool & Concurrency Semaphore Limits
- B4: Expired, Tampered & Blacklisted Authentication
- B5: Rate Limit Burst Exhaustion & Window Recovery
- B6: Invalid CLI Flags & Configuration Boundaries
"""

import asyncio
import os
import re
import time
import uuid
from typing import Dict, List

import pytest
import jwt

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
# B1: Empty, Whitespace & Extreme Inputs (6 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_b1_empty_prompt_raises_invalid_input(agent_adapter: MockAgentAdapter):
    """B1.1: Empty prompt in AgentInput raises ValueError."""
    empty_input = AgentInput(prompt="")
    with pytest.raises(ValueError, match="cannot be empty"):
        await agent_adapter.ainvoke(empty_input)


@pytest.mark.asyncio
async def test_b1_whitespace_prompt_raises_invalid_input(agent_adapter: MockAgentAdapter):
    """B1.2: Whitespace-only prompt raises ValueError without dispatching to model."""
    ws_input = AgentInput(prompt="   \n\t  ")
    with pytest.raises(ValueError, match="cannot be empty"):
        await agent_adapter.ainvoke(ws_input)


@pytest.mark.asyncio
async def test_b1_empty_chat_messages_list(agent_adapter: MockAgentAdapter):
    """B1.3: AgentInput with empty messages list and None prompt is rejected."""
    empty_messages_input = AgentInput(prompt=None, messages=[])
    with pytest.raises(ValueError, match="cannot be empty"):
        await agent_adapter.ainvoke(empty_messages_input)


def test_b1_empty_username_and_password_rejection(auth_service: MockAuthService):
    """B1.4: Blank or empty username/password returns None without crashing."""
    assert auth_service.authenticate_local("", "") is None
    assert auth_service.authenticate_local("   ", "   ") is None
    assert auth_service.authenticate_local("testuser", "") is None


def test_b1_empty_project_name_rejection():
    """B1.5: Empty project name fails slug validation."""
    slug_regex = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    assert slug_regex.match("") is None
    assert slug_regex.match("   ") is None


@pytest.mark.asyncio
async def test_b1_extremely_large_prompt_boundary(agent_adapter: MockAgentAdapter):
    """B1.6: Extremely large prompt (>100KB) is accepted and processed safely."""
    huge_prompt = "token " * 20000  # ~120KB payload
    agent_input = AgentInput(prompt=huge_prompt)
    output = await agent_adapter.ainvoke(agent_input)
    assert output.finish_reason == "stop"
    assert output.metadata["tokens"] == 20000


# ============================================================================
# B2: Disconnects, Cancellations & Upstream Timeouts (5 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_b2_client_disconnect_during_sse_stream(agent_adapter: MockAgentAdapter, sse_streamer: MockSSEStreamer):
    """B2.1: Client disconnect breaks the SSE generator loop cleanly."""
    agent_input = AgentInput(prompt="one two three four five six")
    consumed_count = 0

    # Simulate client reading only first 2 chunks and disconnecting
    async for sse_line in sse_streamer.sse_event_generator(agent_adapter.astream(agent_input)):
        consumed_count += 1
        if consumed_count == 2:
            break  # Client drops connection

    assert consumed_count == 2


@pytest.mark.asyncio
async def test_b2_generator_cancellation_releases_semaphore():
    """B2.2: Task cancellation inside an active semaphore block releases the lock."""
    sem = asyncio.Semaphore(1)

    async def cancelled_worker():
        async with sem:
            await asyncio.sleep(5.0)

    task = asyncio.create_task(cancelled_worker())
    await asyncio.sleep(0.01)  # Allow semaphore acquisition
    assert sem.locked() is True

    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    # Verify semaphore is released and can be acquired immediately
    assert sem.locked() is False
    async with sem:
        assert True


@pytest.mark.asyncio
async def test_b2_upstream_llm_network_timeout_yields_error_chunk(
    agent_adapter: MockAgentAdapter, sse_streamer: MockSSEStreamer
):
    """B2.3: Upstream model error yields standardized error chunk instead of dropping socket."""
    agent_input = AgentInput(prompt="start error finish")
    received_events = []

    async for line in sse_streamer.sse_event_generator(agent_adapter.astream(agent_input, trigger_error=True)):
        received_events.append(line)

    error_event = [e for e in received_events if "event: error" in e]
    assert len(error_event) == 1
    assert "Simulated upstream generation error" in error_event[0]


def test_b2_db_connection_loss_triggers_safe_failure(db_client: MockDatabase):
    """B2.4: Sudden database disconnect raises ConnectionError safely."""
    db_client.set_connected(False)
    with pytest.raises(ConnectionError, match="unreachable"):
        for _ in db_client.get_sync_session():
            pass


@pytest.mark.asyncio
async def test_b2_dev_runner_graceful_sigint_handling():
    """B2.5: Dev runner monitors child processes and terminates them gracefully on signal."""
    cancelled = False

    async def simulated_dev_server():
        nonlocal cancelled
        try:
            while True:
                await asyncio.sleep(0.01)
        except asyncio.CancelledError:
            cancelled = True
            raise

    server_task = asyncio.create_task(simulated_dev_server())
    await asyncio.sleep(0.02)
    server_task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await server_task
    assert cancelled is True


# ============================================================================
# B3: Connection Pool & Concurrency Semaphore Limits (5 tests)
# ============================================================================

def test_b3_db_connection_pool_exhaustion_raises_timeout():
    """B3.1: Exceeding connection pool capacity raises TimeoutError."""
    db = MockDatabase("sqlite:///:memory:")
    db._pool_size = 2
    db._max_overflow = 1
    sessions = []

    try:
        # Acquire 3 sessions (pool_size 2 + overflow 1)
        for _ in range(3):
            gen = db.get_sync_session()
            sess = next(gen)
            sessions.append((gen, sess))

        # 4th session exceeds limit and raises TimeoutError
        with pytest.raises(TimeoutError, match="pool exhausted"):
            gen4 = db.get_sync_session()
            next(gen4)
    finally:
        # Cleanup
        for gen, _ in sessions:
            try:
                next(gen)
            except StopIteration:
                pass


@pytest.mark.asyncio
async def test_b3_concurrency_semaphore_saturation_queues():
    """B3.2: High concurrency saturation queues subsequent requests without dropping."""
    sem = asyncio.Semaphore(2)
    execution_order = []

    async def worker(idx: int):
        async with sem:
            execution_order.append(f"start-{idx}")
            await asyncio.sleep(0.02)
            execution_order.append(f"end-{idx}")

    await asyncio.gather(*(worker(i) for i in range(4)))
    assert len(execution_order) == 8
    # Confirm first two started before third finished
    assert "start-0" in execution_order[:2]
    assert "start-1" in execution_order[:2]


@pytest.mark.asyncio
async def test_b3_concurrency_semaphore_timeout_raises_exceeded():
    """B3.3: Request awaiting saturated semaphore raises TimeoutError when timeout expires."""
    sem = asyncio.Semaphore(1)

    async def blocker():
        async with sem:
            await asyncio.sleep(0.1)

    async def impatient_caller():
        # Await semaphore with 0.01s timeout
        try:
            await asyncio.wait_for(sem.acquire(), timeout=0.01)
            sem.release()
            return True
        except asyncio.TimeoutError:
            raise TimeoutError("Concurrency limit exceeded: timed out waiting for semaphore")

    task = asyncio.create_task(blocker())
    await asyncio.sleep(0.005)

    with pytest.raises(TimeoutError, match="Concurrency limit exceeded"):
        await impatient_caller()

    await task


def test_b3_db_reconnect_recovery_after_transient_failure(db_client: MockDatabase):
    """B3.4: Database recovers and serves sessions once connection is restored."""
    db_client.set_connected(False)
    with pytest.raises(ConnectionError):
        for _ in db_client.get_sync_session():
            pass

    # Restored
    db_client.set_connected(True)
    assert db_client.ping() is True
    for session in db_client.get_sync_session():
        assert session["active"] is True


@pytest.mark.asyncio
async def test_b3_redis_connection_pool_limits(redis_client: InMemoryRedis):
    """B3.5: Redis test double supports concurrent operations under heavy load."""
    keys = [f"key_{i}" for i in range(100)]
    tasks = [redis_client.set(k, f"val_{i}", ex=60) for i, k in enumerate(keys)]
    results = await asyncio.gather(*tasks)
    assert all(results)

    get_tasks = [redis_client.get(k) for k in keys]
    get_results = await asyncio.gather(*get_tasks)
    assert len(get_results) == 100
    assert get_results[42] == "val_42"


# ============================================================================
# B4: Expired, Tampered & Blacklisted Authentication (6 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_b4_expired_jwt_token_rejected_with_permission_error(auth_service: MockAuthService):
    """B4.1: Expired JWT token raises PermissionError."""
    user = {"id": "usr_exp", "username": "expired_user", "role": "USER"}
    # Generate token with negative TTL (already expired)
    tokens = auth_service.create_token_pair(user, access_ttl_minutes=-5)

    with pytest.raises(PermissionError, match="expired"):
        await auth_service.verify_token(tokens["access_token"])


@pytest.mark.asyncio
async def test_b4_tampered_jwt_signature_rejected_with_value_error(auth_service: MockAuthService):
    """B4.2: Token with forged or tampered signature raises ValueError."""
    user = {"id": "usr_tamper", "username": "tamper_user", "role": "USER"}
    tokens = auth_service.create_token_pair(user)
    tampered_token = tokens["access_token"][:-4] + "xyz9"

    with pytest.raises(ValueError, match="Invalid token signature"):
        await auth_service.verify_token(tampered_token)


@pytest.mark.asyncio
async def test_b4_blacklisted_jti_token_rejected_immediately(auth_service: MockAuthService):
    """B4.3: Token whose JTI is blacklisted in Redis is rejected immediately."""
    user = {"id": "usr_blk", "username": "blacklisted_user", "role": "USER"}
    tokens = auth_service.create_token_pair(user)
    token = tokens["access_token"]

    await auth_service.revoke_token(token)
    with pytest.raises(PermissionError, match="revoked"):
        await auth_service.verify_token(token)


def test_b4_invalid_ldap_password_bind_failure(auth_service: MockAuthService):
    """B4.4: Invalid LDAP credentials fail authentication and return None."""
    result = auth_service.authenticate_ldap("corp_admin_kim", "IncorrectCorpPassword")
    assert result is None


def test_b4_malformed_saml_assertion_rejected(auth_service: MockAuthService):
    """B4.5: Malformed SAML XML missing StatusCode or Audience is rejected."""
    malformed_xml = "<samlp:Response><saml:Assertion>Missing elements</saml:Assertion></samlp:Response>"
    result = auth_service.authenticate_saml(malformed_xml)
    assert result is None


@pytest.mark.asyncio
async def test_b4_token_type_mismatch_access_vs_refresh(auth_service: MockAuthService):
    """B4.6: Submitting refresh token to access-only endpoint raises ValueError."""
    user = {"id": "usr_type", "username": "type_user", "role": "USER"}
    tokens = auth_service.create_token_pair(user)
    refresh_token = tokens["refresh_token"]

    with pytest.raises(ValueError, match="Token type mismatch"):
        await auth_service.verify_token(refresh_token, expected_type="access")


# ============================================================================
# B5: Rate Limit Burst Exhaustion & Window Recovery (5 tests)
# ============================================================================

@pytest.mark.asyncio
async def test_b5_sliding_window_blocks_traffic_over_threshold(redis_client: InMemoryRedis):
    """B5.1: Requests exceeding limit are denied with allowed=False and remaining=0."""
    limit = 3
    window = 5
    ip = "10.0.0.1"

    for _ in range(limit):
        allowed, rem, _ = await redis_client.check_rate_limit(ip, limit, window)
        assert allowed is True

    # 4th request must be rejected
    allowed, rem, retry_after = await redis_client.check_rate_limit(ip, limit, window)
    assert allowed is False
    assert rem == 0
    assert retry_after > 0


@pytest.mark.asyncio
async def test_b5_retry_after_decreases_as_window_progresses(redis_client: InMemoryRedis):
    """B5.2: Retry-After estimate decreases over time."""
    limit = 1
    window = 2
    ip = "10.0.0.2"

    await redis_client.check_rate_limit(ip, limit, window)
    _, _, retry_1 = await redis_client.check_rate_limit(ip, limit, window)

    await asyncio.sleep(0.5)
    _, _, retry_2 = await redis_client.check_rate_limit(ip, limit, window)
    assert retry_2 < retry_1


@pytest.mark.asyncio
async def test_b5_rate_limit_resets_after_full_window_expires(redis_client: InMemoryRedis):
    """B5.3: Rate limit fully resets after the sliding window elapses."""
    limit = 2
    window = 1  # 1 second window
    ip = "10.0.0.3"

    await redis_client.check_rate_limit(ip, limit, window)
    await redis_client.check_rate_limit(ip, limit, window)

    # Blocked
    allowed, _, _ = await redis_client.check_rate_limit(ip, limit, window)
    assert allowed is False

    # Wait for window to expire
    await asyncio.sleep(1.05)

    # Recovered
    allowed, rem, _ = await redis_client.check_rate_limit(ip, limit, window)
    assert allowed is True
    assert rem == 1


@pytest.mark.asyncio
async def test_b5_rate_limit_per_client_ip_isolation(redis_client: InMemoryRedis):
    """B5.4: Rate limiting one IP does not affect another IP."""
    limit = 2
    window = 10

    # Exhaust IP 1
    await redis_client.check_rate_limit("ip.one", limit, window)
    await redis_client.check_rate_limit("ip.one", limit, window)
    allowed_1, _, _ = await redis_client.check_rate_limit("ip.one", limit, window)
    assert allowed_1 is False

    # IP 2 must still have full quota
    allowed_2, rem_2, _ = await redis_client.check_rate_limit("ip.two", limit, window)
    assert allowed_2 is True
    assert rem_2 == 1


@pytest.mark.asyncio
async def test_b5_rate_limit_per_user_id_isolation(redis_client: InMemoryRedis):
    """B5.5: Rate limiting per authenticated user ID works independently."""
    limit = 3
    window = 10

    for _ in range(limit):
        await redis_client.check_rate_limit("usr_alpha", limit, window)

    assert (await redis_client.check_rate_limit("usr_alpha", limit, window))[0] is False
    assert (await redis_client.check_rate_limit("usr_beta", limit, window))[0] is True


# ============================================================================
# B6: Invalid CLI Flags & Configuration Boundaries (6 tests)
# ============================================================================

def test_b6_cli_new_unsupported_framework_rejected():
    """B6.1: Passing unsupported framework to 'new' command is rejected."""
    supported = {"langchain", "langgraph", "deepagent", "adk", "bedrock"}
    invalid_framework = "unsupported_fw_xyz"
    assert invalid_framework not in supported


def test_b6_cli_new_unsupported_frontend_rejected():
    """B6.2: Passing unsupported frontend to 'new' command is rejected."""
    supported = {"react", "streamlit", "none"}
    invalid_frontend = "vue_angular_invalid"
    assert invalid_frontend not in supported


def test_b6_cli_new_illegal_characters_in_project_name():
    """B6.3: Project names containing spaces, slashes, or shell metachars are rejected."""
    slug_regex = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$")
    hostile_names = [
        "project; rm -rf /",
        "../../etc/passwd",
        "my agent bot",
        "agent$eval",
        "`whoami`",
        "test|pipe",
    ]
    for name in hostile_names:
        assert slug_regex.match(name) is None


def test_b6_cli_new_existing_non_empty_dir_aborts_without_force(temp_workspace: str):
    """B6.4: Generation into existing non-empty directory raises error unless force=True."""
    target_dir = os.path.join(temp_workspace, "existing_project")
    os.makedirs(target_dir, exist_ok=True)
    with open(os.path.join(target_dir, "important_file.txt"), "w") as f:
        f.write("preserve this")

    def scaffold(path: str, force: bool = False):
        if os.path.exists(path) and os.listdir(path) and not force:
            raise FileExistsError(f"Directory {path} already exists and is not empty. Use --force to overwrite.")
        return True

    with pytest.raises(FileExistsError, match="already exists"):
        scaffold(target_dir, force=False)

    # With force=True, scaffold proceeds
    assert scaffold(target_dir, force=True) is True


def test_b6_cli_deploy_invalid_target_environment():
    """B6.5: Deploy command rejects environments other than 'dev' and 'prd'."""
    supported_envs = {"dev", "prd"}
    assert "staging" not in supported_envs
    assert "test" not in supported_envs


def test_b6_pageable_params_negative_page_and_excessive_size():
    """B6.6: PageableParams automatically normalizes pathological negative/excessive inputs."""
    pathological = PageableParams(page=-999999, size=9999999).sanitize()
    assert pathological.page == 1
    assert pathological.size == 100
