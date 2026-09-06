"""Comprehensive Unit Test Suite for AgentForge Core Runtime Engine.

Covers:
- adapter.py: Event types, models, exception hierarchy, 8 framework adapters, get_adapter factory
- streaming.py: SSETokenStreamer, anti-buffering headers, error shielding, RuntimeContext concurrency & cancellation
- database.py: Database singleton, sync/async session contexts & generators, ping/aping, PageableParams, pagination
- logging.py: JsonFormatter, correlation ID contextvars propagation, setup_logger
- config.py: BaseAppSettings, env overrides, CORS parsing, URL resolution
- __init__.py: 10 public symbols export completeness and zero-root-import decoupled architecture
"""

import asyncio
from datetime import datetime, timezone
import json
import logging
import os
from typing import AsyncGenerator, Optional
import uuid

import pytest
from sqlmodel import Field, SQLModel, select

from agentforge.core import (
    AdapterConfigurationError,
    AdapterError,
    AdapterExecutionError,
    AdapterTimeoutError,
    AgentChunk,
    AgentEventType,
    AgentInput,
    AgentMessage,
    AgentOutput,
    AgentRole,
    AutoGenAdapter,
    BaseAgentAdapter,
    BaseAppSettings,
    BedrockAdapter,
    CorrelationIdFilter,
    CrewAIAdapter,
    Database,
    DatabaseConnectionError,
    DatabaseError,
    DatabasePoolTimeoutError,
    DeepAgentAdapter,
    DualAsyncSessionContext,
    DualSyncSessionContext,
    GoogleGenAIAdapter,
    InterruptRequiredError,
    InvalidInputError,
    JsonFormatter,
    LangChainAdapter,
    LangGraphAdapter,
    LlamaIndexAdapter,
    Page,
    PageMetadata,
    PageableParams,
    RuntimeContext,
    SSETokenStreamer,
    apaginate,
    apply_pageable_params,
    db,
    get_adapter,
    get_async_session,
    get_correlation_id,
    get_pk_list,
    get_pk_values,
    get_session,
    get_settings,
    paginate,
    reset_correlation_id,
    set_correlation_id,
    setup_logger,
)


# ============================================================================
# Test Model for Database & Pagination Tests
# ============================================================================

class TestItem(SQLModel, table=True):
    __test__ = False
    __tablename__ = "test_items"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    score: int


# ============================================================================
# 1. Adapter & Protocols Unit Tests
# ============================================================================

def test_adapter_event_types():
    """Verify all 6 canonical AgentEventType enum values."""
    assert AgentEventType.TOKEN == "token"
    assert AgentEventType.EVIDENCE == "evidence"
    assert AgentEventType.META == "meta"
    assert AgentEventType.INTERRUPT == "interrupt"
    assert AgentEventType.ERROR == "error"
    assert AgentEventType.DONE == "done"


def test_adapter_roles():
    """Verify standard AgentRole values."""
    assert AgentRole.SYSTEM == "system"
    assert AgentRole.USER == "user"
    assert AgentRole.ASSISTANT == "assistant"
    assert AgentRole.TOOL == "tool"
    assert AgentRole.FUNCTION == "function"


def test_agent_message_and_input():
    """Verify AgentMessage and AgentInput models and prompt fallback helper."""
    msg1 = AgentMessage(role=AgentRole.SYSTEM, content="System prompt")
    msg2 = AgentMessage(role=AgentRole.USER, content="Latest user query")
    input_data = AgentInput(messages=[msg1, msg2])
    assert input_data.get_prompt_or_last_message() == "Latest user query"

    input_with_prompt = AgentInput(prompt="Explicit prompt", messages=[msg2])
    assert input_with_prompt.get_prompt_or_last_message() == "Explicit prompt"

    empty_input = AgentInput()
    assert empty_input.get_prompt_or_last_message() == ""


def test_agent_chunk_dual_access_and_serialization():
    """Verify AgentChunk supports event and type property, to_dict, to_json, and to_sse_event."""
    chunk = AgentChunk(event=AgentEventType.TOKEN, data="token_text", content="token_text", id="chunk-1")
    assert chunk.event == AgentEventType.TOKEN
    assert chunk.type == AgentEventType.TOKEN
    assert chunk.content == "token_text"

    chunk_dict = chunk.to_dict()
    assert chunk_dict["event"] == "token"
    assert chunk_dict["type"] == "token"
    assert chunk_dict["id"] == "chunk-1"

    chunk_json = chunk.to_json()
    parsed = json.loads(chunk_json)
    assert parsed["type"] == "token"

    sse_text = chunk.to_sse_event()
    assert "event: token" in sse_text
    assert "id: chunk-1" in sse_text
    assert "data: " in sse_text


def test_adapter_exception_hierarchy():
    """Verify exception inheritance and attributes."""
    assert issubclass(AdapterConfigurationError, AdapterError)
    assert issubclass(AdapterExecutionError, AdapterError)
    assert issubclass(InvalidInputError, AdapterError)
    assert issubclass(InterruptRequiredError, AdapterError)
    assert issubclass(AdapterTimeoutError, AdapterError)

    interrupt_err = InterruptRequiredError("Approval needed", interrupt_id="int-123", payload={"amount": 100})
    assert interrupt_err.interrupt_id == "int-123"
    assert interrupt_err.payload == {"amount": 100}


def test_get_adapter_all_frameworks_and_aliases():
    """Verify get_adapter factory resolves all 8 frameworks and aliases."""
    cases = [
        ("langchain", LangChainAdapter),
        ("llamaindex", LlamaIndexAdapter),
        ("llama-index", LlamaIndexAdapter),
        ("google-genai", GoogleGenAIAdapter),
        ("googlegenai", GoogleGenAIAdapter),
        ("gemini", GoogleGenAIAdapter),
        ("adk", GoogleGenAIAdapter),
        ("crewai", CrewAIAdapter),
        ("autogen", AutoGenAdapter),
        ("langgraph", LangGraphAdapter),
        ("deepagent", DeepAgentAdapter),
        ("bedrock", BedrockAdapter),
        ("aws-bedrock", BedrockAdapter),
    ]
    for name, expected_cls in cases:
        adapter = get_adapter(name)
        assert isinstance(adapter, expected_cls)
        assert isinstance(adapter, BaseAgentAdapter)

    # Test underscore / hyphen normalization
    assert isinstance(get_adapter("google_genai"), GoogleGenAIAdapter)
    assert isinstance(get_adapter("aws_bedrock"), BedrockAdapter)

    with pytest.raises(ValueError, match="Unsupported agent framework"):
        get_adapter("unknown_framework")


@pytest.mark.asyncio
async def test_concrete_adapters_ainvoke_and_astream():
    """Verify ainvoke and astream execution across all 8 concrete adapters."""
    frameworks = ["langchain", "llamaindex", "google-genai", "crewai", "autogen", "langgraph", "deepagent", "bedrock"]
    for fw in frameworks:
        adapter = get_adapter(fw)
        await adapter.initialize()
        assert await adapter.health_check() is True

        # Test empty prompt raises InvalidInputError
        with pytest.raises(InvalidInputError):
            await adapter.ainvoke(AgentInput())

        # Test ainvoke
        output = await adapter.ainvoke(AgentInput(prompt="Test question", turn_id="t-1"))
        assert isinstance(output, AgentOutput)
        assert len(output.content) > 0

        # Test astream
        chunks = []
        async for chunk in adapter.astream(AgentInput(prompt="Test question")):
            chunks.append(chunk)

        assert len(chunks) > 0
        assert chunks[-1].event == AgentEventType.DONE


@pytest.mark.asyncio
async def test_concrete_adapters_interrupt_handling():
    """Verify interrupt emission and resumption across adapters."""
    adapter = get_adapter("langgraph")
    chunks = []
    async for chunk in adapter.astream(AgentInput(prompt="Action requires interrupt")):
        chunks.append(chunk)

    interrupt_chunk = chunks[0]
    assert interrupt_chunk.event == AgentEventType.INTERRUPT
    assert interrupt_chunk.id is not None

    res = await adapter.ahandle_interrupt(
        interrupt_id=interrupt_chunk.id,
        decision="approve",
        state_update={"authorized": True},
    )
    assert isinstance(res, AgentOutput)
    assert "approve" in res.content or "approved" in res.content or res.finish_reason == "resumed"


# ============================================================================
# 2. Streaming Engine & Runtime Governance Unit Tests
# ============================================================================

def test_sse_token_streamer_headers():
    """Verify anti-buffering headers required for SSE."""
    headers = SSETokenStreamer.stream_headers()
    assert headers["Content-Type"] == "text/event-stream"
    assert headers["Cache-Control"] == "no-cache"
    assert headers["Connection"] == "keep-alive"
    assert headers["X-Accel-Buffering"] == "no"


def test_sse_token_streamer_format_event():
    """Verify RFC-compliant SSE wire formatting."""
    streamer = SSETokenStreamer()
    formatted = streamer.format_sse_event(
        event="token",
        data={"content": "hello\nworld"},
        event_id="id-001",
        retry=5000,
    )
    lines = [line for line in formatted.split("\n") if line]
    assert lines[0] == "event: token"
    assert lines[1] == "id: id-001"
    assert lines[2] == "retry: 5000"
    assert lines[3].startswith("data: ")


@pytest.mark.asyncio
async def test_sse_token_streamer_astream_sse_normal():
    """Verify astream_sse yields formatted SSE chunks and terminal done event."""
    streamer = SSETokenStreamer()

    async def sample_gen():
        yield AgentChunk(event=AgentEventType.TOKEN, data="Hello")
        yield AgentChunk(event=AgentEventType.TOKEN, data="World")

    events = []
    async for raw_sse in streamer.astream_sse(sample_gen()):
        events.append(raw_sse)

    assert len(events) == 3  # 2 tokens + 1 terminal done
    assert "event: token" in events[0]
    assert "event: token" in events[1]
    assert "event: done" in events[2]


@pytest.mark.asyncio
async def test_sse_token_streamer_error_shielding():
    """Verify uncaught generator errors are shielded into an event: error SSE event."""
    streamer = SSETokenStreamer()

    async def failing_gen():
        yield AgentChunk(event=AgentEventType.TOKEN, data="Before error")
        raise RuntimeError("Simulated upstream LLM crash")

    events = []
    async for raw_sse in streamer.astream_sse(failing_gen()):
        events.append(raw_sse)

    assert len(events) == 2
    assert "event: token" in events[0]
    assert "event: error" in events[1]
    assert "Simulated upstream LLM crash" in events[1]


@pytest.mark.asyncio
async def test_sse_token_streamer_aclose_clean_teardown():
    """Verify early aclose() / GeneratorExit terminates cleanly without RuntimeError (PEP 525 compliance)."""
    streamer = SSETokenStreamer()

    # Verify contract alias sse_event_generator
    assert streamer.sse_event_generator == streamer.astream_sse

    async def infinite_chunk_generator():
        for i in range(50):
            yield AgentChunk(event=AgentEventType.TOKEN, data=f"token_{i}", content=f"token_{i}")
            await asyncio.sleep(0.005)

    gen = streamer.astream_sse(infinite_chunk_generator())
    first_item = await anext(gen)
    assert "event: token" in first_item
    assert "token_0" in first_item

    # Must complete cleanly without RuntimeError: async generator ignored GeneratorExit
    try:
        await gen.aclose()
    except RuntimeError as exc:
        pytest.fail(f"aclose() violated PEP 525: {exc}")

    # Subsequent fetch must raise StopAsyncIteration
    with pytest.raises(StopAsyncIteration):
        await anext(gen)


@pytest.mark.asyncio
async def test_sse_token_streamer_aclose_on_error_stream_clean_teardown():
    """Verify calling aclose() after receiving an error event terminates cleanly without RuntimeError.

    Guarantees PEP 525 compliance when consumer closes stream while generator
    is suspended at the error event yield point (preventing 'async generator ignored GeneratorExit').
    """
    streamer = SSETokenStreamer()

    # Scenario 1: Upstream generator fails after yielding tokens; consumer reads error and closes immediately
    async def failing_after_token_gen():
        yield AgentChunk(event=AgentEventType.TOKEN, data="token_before_crash", content="token_before_crash")
        raise ValueError("Simulated LLM pipeline failure")

    gen = streamer.astream_sse(failing_after_token_gen())
    token_chunk = await anext(gen)
    assert "event: token" in token_chunk
    assert "token_before_crash" in token_chunk

    error_chunk = await anext(gen)
    assert "event: error" in error_chunk
    assert "Simulated LLM pipeline failure" in error_chunk

    # At this point, the generator is suspended at the error yield.
    # Calling aclose() must NOT raise RuntimeError: async generator ignored GeneratorExit
    try:
        await gen.aclose()
    except RuntimeError as exc:
        pytest.fail(f"aclose() after error chunk violated PEP 525: {exc}")

    # Subsequent fetch must immediately raise StopAsyncIteration
    with pytest.raises(StopAsyncIteration):
        await anext(gen)

    # Scenario 2: Upstream generator fails immediately on first chunk (no token preceding error)
    async def failing_immediately_gen():
        raise RuntimeError("Immediate upstream crash")
        yield AgentChunk(event=AgentEventType.TOKEN, data="never")  # pragma: no cover

    gen_imm = streamer.astream_sse(failing_immediately_gen())
    err_chunk_imm = await anext(gen_imm)
    assert "event: error" in err_chunk_imm
    assert "Immediate upstream crash" in err_chunk_imm

    try:
        await gen_imm.aclose()
    except RuntimeError as exc:
        pytest.fail(f"aclose() after immediate error violated PEP 525: {exc}")

    with pytest.raises(StopAsyncIteration):
        await anext(gen_imm)


@pytest.mark.asyncio
async def test_sse_token_streamer_cancellation_no_spurious_completed():
    """Verify cooperative cancellation and task cancellation do not emit spurious finish_reason: 'completed'."""
    streamer = SSETokenStreamer()

    async def sample_chunk_stream():
        for i in range(50):
            yield AgentChunk(event=AgentEventType.TOKEN, data=f"token_{i}", content=f"token_{i}")
            await asyncio.sleep(0.005)

    # 1. Cooperative cancellation via RuntimeContext
    ctx = RuntimeContext(correlation_id="corr-cancel-check")
    cooperative_events = []
    async for sse in streamer.astream_sse(sample_chunk_stream(), context=ctx):
        cooperative_events.append(sse)
        if len(cooperative_events) == 2:
            ctx.cancel("User cancelled generation")

    assert len(cooperative_events) >= 2
    # Verify no event falsely reports normal completion
    for ev in cooperative_events:
        assert '"finish_reason": "completed"' not in ev
        assert "completed" not in ev

    # 2. Asyncio Task cancellation via CancelledError
    task_events = []
    async def consumer():
        async for sse in streamer.astream_sse(sample_chunk_stream()):
            task_events.append(sse)

    t = asyncio.create_task(consumer())
    await asyncio.sleep(0.015)
    t.cancel()
    with pytest.raises(asyncio.CancelledError):
        await t

    assert len(task_events) > 0
    for ev in task_events:
        assert '"finish_reason": "completed"' not in ev


@pytest.mark.asyncio
async def test_runtime_context_cancellation_and_semaphore():
    """Verify RuntimeContext cancellation check and concurrency semaphore."""
    ctx = RuntimeContext(correlation_id="corr-test-1", semaphore_limits={"TEST_SEM": 1})
    assert ctx.correlation_id == "corr-test-1"
    assert await ctx.is_cancelled() is False

    # Semaphore acquire & release
    async with ctx.acquire_semaphore("TEST_SEM"):
        # Second acquire with 0.05s timeout must timeout
        with pytest.raises(asyncio.TimeoutError):
            async with ctx.acquire_semaphore("TEST_SEM", timeout=0.05):
                pass

    # Slot must be released now
    acquired_second_time = False
    async with ctx.acquire_semaphore("TEST_SEM", timeout=0.1):
        acquired_second_time = True
    assert acquired_second_time is True

    # Manual cancel
    ctx.cancel(reason="Client timeout")
    assert await ctx.is_cancelled() is True


@pytest.mark.asyncio
async def test_runtime_context_client_disconnected_and_concurrency_semaphore():
    """Verify RuntimeContext exposes client_disconnected and concurrency_semaphore per PROJECT.md:87."""
    ctx = RuntimeContext(correlation_id="corr-contract-test", semaphore_limits={"LLM": 2})

    # 1. Verify client_disconnected property and synchronization with cancellation state
    assert hasattr(ctx, "client_disconnected"), "RuntimeContext missing client_disconnected property"
    assert isinstance(ctx.client_disconnected, asyncio.Event)
    assert not ctx.client_disconnected.is_set()
    assert await ctx.is_cancelled() is False

    # Calling ctx.cancel() must set client_disconnected event
    ctx.cancel("Client disconnected from HTTP socket")
    assert ctx.client_disconnected.is_set() is True
    assert await ctx.is_cancelled() is True

    # Direct setting of client_disconnected event must reflect in is_cancelled()
    fresh_ctx = RuntimeContext(correlation_id="corr-direct-event")
    assert isinstance(fresh_ctx.client_disconnected, asyncio.Event)
    assert not fresh_ctx.client_disconnected.is_set()
    fresh_ctx.client_disconnected.set()
    assert await fresh_ctx.is_cancelled() is True

    # 2. Verify concurrency_semaphore property and semaphore functionality
    assert hasattr(ctx, "concurrency_semaphore"), "RuntimeContext missing concurrency_semaphore property"
    assert isinstance(ctx.concurrency_semaphore, asyncio.Semaphore)

    # Concurrency semaphore should support direct acquisition
    sem = fresh_ctx.concurrency_semaphore
    assert isinstance(sem, asyncio.Semaphore)
    async with sem:
        pass

    # 3. Context manager integration
    async with RuntimeContext(correlation_id="cm-contract-test") as cm_ctx:
        assert isinstance(cm_ctx.client_disconnected, asyncio.Event)
        assert isinstance(cm_ctx.concurrency_semaphore, asyncio.Semaphore)


# ============================================================================
# 3. Database Persistence & Pagination Unit Tests
# ============================================================================

def test_database_singleton():
    """Verify Database singleton pattern and reset capability."""
    db1 = Database()
    db2 = Database()
    assert db1 is db2

    Database.reset()
    db3 = Database()
    assert db3 is not None


def test_database_url_resolution():
    """Verify driver normalization between sync and async."""
    test_db = Database(url="sqlite:///:memory:")
    assert "sqlite:///:memory:" in test_db._resolve_url(is_async=False)
    assert "sqlite+aiosqlite:///:memory:" in test_db._resolve_url(is_async=True)

    test_pg = Database(url="postgresql://user:pass@localhost:5432/db")
    assert test_pg._resolve_url(is_async=False).startswith("postgresql+psycopg2://")
    assert test_pg._resolve_url(is_async=True).startswith("postgresql+asyncpg://")


def test_database_sync_session_and_ping():
    """Verify sync engine initialization, health ping, and session context manager & generator."""
    test_db = Database()
    test_db.init_sync_engine("sqlite:///:memory:")
    assert test_db.ping() is True

    # Context manager test
    with test_db.get_sync_session() as session:
        result = session.execute(select(1)).scalar_one()
        assert result == 1

    # Generator test (FastAPI dependency style)
    gen = test_db.get_sync_session()
    for session in gen:
        result = session.execute(select(1)).scalar_one()
        assert result == 1


@pytest.mark.asyncio
async def test_database_async_session_and_aping():
    """Verify async engine initialization, health aping, and async session context manager & generator."""
    test_db = Database()
    test_db.init_async_engine("sqlite+aiosqlite:///:memory:")
    assert await test_db.aping() is True

    # Async context manager test
    async with test_db.get_async_session() as session:
        result = (await session.execute(select(1))).scalar_one()
        assert result == 1

    # Async generator test (FastAPI dependency style)
    async for session in test_db.get_async_session():
        result = (await session.execute(select(1))).scalar_one()
        assert result == 1


def test_pageable_params_validation():
    """Verify PageableParams validation and SQL injection protection on sort_by."""
    params = PageableParams(page=2, size=15, sort_by="created_at", sort_direction="desc")
    assert params.page == 2
    assert params.size == 15
    assert params.sort_by == "created_at"
    assert params.sort_direction == "desc"

    # SQL Injection attempt must be rejected
    with pytest.raises(ValueError, match="Invalid sort_by field"):
        PageableParams(sort_by="name; DROP TABLE users;--")


def test_page_metadata_calculation():
    """Verify PageMetadata calculates total_pages, has_next, and has_previous."""
    meta = PageMetadata.create(number=1, size=10, total_elements=25)
    assert meta.number == 1
    assert meta.size == 10
    assert meta.total_elements == 25
    assert meta.total_pages == 3
    assert meta.has_next is True
    assert meta.has_previous is False

    meta_page2 = PageMetadata.create(number=2, size=10, total_elements=25)
    assert meta_page2.has_next is True
    assert meta_page2.has_previous is True

    meta_last = PageMetadata.create(number=3, size=10, total_elements=25)
    assert meta_last.has_next is False
    assert meta_last.has_previous is True


def test_sync_and_async_pagination():
    """Verify paginate and apaginate on SQLModel entities."""
    test_db = Database()
    test_db.init_sync_engine("sqlite:///:memory:")
    test_db.init_async_engine("sqlite+aiosqlite:///:memory:")

    # Create tables
    SQLModel.metadata.create_all(test_db.sync_engine)

    # Insert 15 items
    with test_db.get_sync_session() as session:
        for i in range(15):
            session.add(TestItem(name=f"Item-{i}", score=i * 10))

    # Sync paginate
    with test_db.get_sync_session() as session:
        query = select(TestItem)
        params = PageableParams(page=1, size=5, sort_by="score", sort_direction="asc")
        page = paginate(session, query, params)
        assert isinstance(page, Page)
        assert len(page.items) == 5
        assert page.metadata.total_elements == 15
        assert page.metadata.total_pages == 3
        assert page.items[0].score == 0

    # PK helpers
    with test_db.get_sync_session() as session:
        item = session.exec(select(TestItem)).first()
        assert get_pk_list(TestItem) == ["id"]
        assert get_pk_values(item) == [item.id]


@pytest.mark.asyncio
async def test_apaginate_with_async_session():
    """Verify apaginate asynchronously paginates SQLModel queries using an AsyncSession."""
    Database.reset()
    test_db = Database()
    test_db.init_async_engine("sqlite+aiosqlite:///:memory:")

    # Create tables asynchronously
    async with test_db.async_engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    # Seed 15 items via async session
    async with test_db.get_async_session() as session:
        for i in range(15):
            session.add(TestItem(name=f"AsyncItem-{i}", score=i * 10))

    # Test page 2 pagination (items 5..9)
    async with test_db.get_async_session() as session:
        query = select(TestItem)
        params = PageableParams(page=2, size=5, sort_by="score", sort_direction="asc")
        page = await apaginate(session, query, params)

        assert isinstance(page, Page)
        assert len(page.items) == 5
        assert page.metadata.total_elements == 15
        assert page.metadata.total_pages == 3
        assert page.metadata.number == 2
        assert page.metadata.has_next is True
        assert page.metadata.has_previous is True
        assert page.items[0].score == 50
        assert page.items[-1].score == 90

    # Test out-of-bounds page
    async with test_db.get_async_session() as session:
        query = select(TestItem)
        oob_params = PageableParams(page=99, size=5)
        oob_page = await apaginate(session, query, oob_params)

        assert oob_page.items == []
        assert oob_page.metadata.total_elements == 15
        assert oob_page.metadata.total_pages == 3
        assert oob_page.metadata.number == 99
        assert oob_page.metadata.has_next is False
        assert oob_page.metadata.has_previous is True


# ============================================================================
# 4. Logging & Correlation ID Propagation Unit Tests
# ============================================================================

def test_json_formatter_standard_fields():
    """Verify JsonFormatter outputs valid JSON containing all 8 standard schema fields."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test_logger",
        level=logging.INFO,
        pathname="/app/src/test.py",
        lineno=42,
        msg="Sample log message",
        args=(),
        exc_info=None,
    )
    formatted = formatter.format(record)
    parsed = json.loads(formatted)

    required_fields = ["timestamp", "level", "message", "logger", "correlation_id", "path", "line", "exception"]
    for field in required_fields:
        assert field in parsed

    assert parsed["level"] == "INFO"
    assert parsed["message"] == "Sample log message"
    assert parsed["logger"] == "test_logger"
    assert parsed["line"] == 42
    assert parsed["path"] == "/app/src/test.py"
    assert parsed["timestamp"].endswith("Z")


def test_correlation_id_context_propagation():
    """Verify correlation ID propagates via contextvars and is injected by CorrelationIdFilter."""
    logger = setup_logger("test_corr_logger", level="INFO", json_format=True)

    token = set_correlation_id("test-cid-999")
    try:
        assert get_correlation_id() == "test-cid-999"
        # Test record enrichment
        record = logging.LogRecord(
            name="test_corr_logger",
            level=logging.INFO,
            pathname="/app/test.py",
            lineno=10,
            msg="With correlation id",
            args=(),
            exc_info=None,
        )
        formatter = JsonFormatter()
        parsed = json.loads(formatter.format(record))
        assert parsed["correlation_id"] == "test-cid-999"
    finally:
        reset_correlation_id(token)

    assert get_correlation_id() is None


def test_setup_logger_idempotency():
    """Verify setup_logger reconfigures existing logger without duplicating handlers."""
    logger1 = setup_logger("idempotent_logger", level="DEBUG")
    handler_count_1 = len(logger1.handlers)
    assert handler_count_1 == 1

    logger2 = setup_logger("idempotent_logger", level="INFO")
    handler_count_2 = len(logger2.handlers)
    assert handler_count_2 == 1
    assert logger2.level == logging.INFO


def test_json_formatter_extra_fields_resilience():
    """Verify JsonFormatter handles custom extra fields and non-serializable objects safely."""
    formatter = JsonFormatter()
    record = logging.LogRecord(
        name="test_extra",
        level=logging.WARNING,
        pathname="/app/test.py",
        lineno=50,
        msg="Extra test",
        args=(),
        exc_info=None,
    )
    record.custom_obj = object()
    record.now = datetime.now()

    formatted = formatter.format(record)
    parsed = json.loads(formatted)
    assert "extra" in parsed
    assert "custom_obj" in parsed["extra"]
    assert "now" in parsed["extra"]


# ============================================================================
# 5. Configuration (BaseAppSettings) Unit Tests
# ============================================================================

def test_base_app_settings_defaults():
    """Verify BaseAppSettings loads standard enterprise defaults."""
    settings = BaseAppSettings()
    assert settings.app_name == "AgentForge App"
    assert settings.environment == "dev"
    assert settings.port == 8000
    assert settings.log_level == "INFO"
    assert settings.debug is False
    assert settings.database_pool_size == 10
    assert settings.database_pool_timeout == 30
    assert settings.default_provider == "openai"
    assert settings.default_model == "gpt-4o"
    assert settings.timeout == 60.0
    assert settings.max_retries == 3


def test_base_app_settings_environment_normalization():
    """Verify environment aliases (development, production, testing) normalize to dev, prd, test."""
    s1 = BaseAppSettings(environment="development")
    assert s1.environment == "dev"

    s2 = BaseAppSettings(environment="production")
    assert s2.environment == "prd"

    s3 = BaseAppSettings(environment="testing")
    assert s3.environment == "test"


def test_base_app_settings_cors_origins_parsing():
    """Verify cors_origins parsing from list, comma-separated string, and JSON string."""
    s1 = BaseAppSettings(cors_origins="http://localhost:3000, https://example.com")
    assert s1.cors_origins == ["http://localhost:3000", "https://example.com"]

    s2 = BaseAppSettings(cors_origins='["http://localhost:5173", "http://localhost:8080"]')
    assert s2.cors_origins == ["http://localhost:5173", "http://localhost:8080"]


def test_base_app_settings_resolved_urls():
    """Verify resolved_database_url and resolved_redis_url dynamic assembly."""
    settings = BaseAppSettings(
        database_driver="sqlite",
        database_url=None,
        redis_host="redis.internal",
        redis_port=6380,
        redis_password="secretpassword",
        redis_db=2,
    )
    assert "sqlite:///./agentforge.db" in settings.resolved_database_url
    assert settings.resolved_redis_url == "redis://:secretpassword@redis.internal:6380/2"


def test_get_settings_singleton():
    """Verify get_settings returns cached singleton instance."""
    assert get_settings() is get_settings()


# ============================================================================
# 6. Core Public Exports & Decoupling Architecture Audit
# ============================================================================

def test_core_10_public_symbols_export_completeness():
    """Verify all 10 core runtime symbols and companions are cleanly exported from agentforge.core."""
    import agentforge.core as core

    # The 10 required core runtime symbols:
    assert hasattr(core, "BaseAgentAdapter")
    assert hasattr(core, "AgentChunk")
    assert hasattr(core, "AgentEventType")
    assert hasattr(core, "SSETokenStreamer")
    assert hasattr(core, "RuntimeContext")
    assert hasattr(core, "Database")
    assert hasattr(core, "Page")
    assert hasattr(core, "PageableParams")
    assert hasattr(core, "setup_logger")
    assert hasattr(core, "BaseAppSettings")

    # Companions
    assert hasattr(core, "JsonFormatter")
    assert hasattr(core, "get_settings")
    assert hasattr(core, "PageMetadata")
    assert hasattr(core, "get_adapter")
    assert hasattr(core, "paginate")
    assert hasattr(core, "apaginate")
    assert hasattr(core, "get_session")
    assert hasattr(core, "get_async_session")


def test_core_zero_root_imports_ast_audit():
    """AST / text audit verifying no .py file in agentforge/core/ imports from agentforge root package."""
    import glob

    core_dir = os.path.dirname(__file__) + "/../agentforge/core"
    core_files = glob.glob(os.path.join(core_dir, "*.py"))
    assert len(core_files) >= 5

    for fpath in core_files:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        for line_no, line in enumerate(content.splitlines(), start=1):
            stripped = line.strip()
            # Ignore comments and docstrings
            if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            assert not stripped.startswith("from agentforge "), (
                f"Decoupling violation at {fpath}:{line_no} -> '{stripped}'"
            )
            assert not stripped.startswith("import agentforge"), (
                f"Decoupling violation at {fpath}:{line_no} -> '{stripped}'"
            )
