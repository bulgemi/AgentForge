"""Unit and integration tests for Langfuse tracing configuration and agent adapter callback handler."""

from __future__ import annotations

import asyncio
import importlib.util
import os
from unittest.mock import MagicMock, patch

import pytest

from agentforge.core.adapter import (
    AgentChunk,
    AgentEventType,
    AgentInput,
    AgentMessage,
    AgentOutput,
    AgentRole,
)
from agentforge.core.config import BaseAppSettings, get_settings


# Load the template agent adapter dynamically
def _load_template_agent_module():
    template_path = os.path.join(
        os.path.dirname(__file__),
        "..",
        "agentforge",
        "templates",
        "backend",
        "src",
        "frameworks",
        "langgraph",
        "agent.py",
    )
    spec = importlib.util.spec_from_file_location("test_langgraph_agent", os.path.abspath(template_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 1. BaseAppSettings Configuration & Alias Tests
# ---------------------------------------------------------------------------

def test_langfuse_settings_defaults():
    """Verify default values for Langfuse settings."""
    settings = BaseAppSettings()
    assert settings.langfuse_enabled is False
    assert settings.langfuse_public_key is None
    assert settings.langfuse_secret_key is None
    assert settings.langfuse_base_url == "http://localhost:3000"
    assert settings.langfuse_host == "http://localhost:3000"


def test_langfuse_host_property_getter_and_setter():
    """Verify langfuse_host property getter and setter maintain synchronization."""
    settings = BaseAppSettings()
    assert settings.langfuse_host == settings.langfuse_base_url

    settings.langfuse_host = "http://custom-host:3000"
    assert settings.langfuse_base_url == "http://custom-host:3000"
    assert settings.langfuse_host == "http://custom-host:3000"


def test_langfuse_host_alias_in_constructor():
    """Verify initializing BaseAppSettings with langfuse_host maps to langfuse_base_url."""
    s1 = BaseAppSettings(langfuse_host="http://langfuse-alias:3000")
    assert s1.langfuse_base_url == "http://langfuse-alias:3000"
    assert s1.langfuse_host == "http://langfuse-alias:3000"

    s2 = BaseAppSettings(langfuse_base_url="http://langfuse-direct:3000")
    assert s2.langfuse_base_url == "http://langfuse-direct:3000"
    assert s2.langfuse_host == "http://langfuse-direct:3000"


def test_langfuse_environment_variable_aliases(monkeypatch):
    """Verify LANGFUSE_HOST and LANGFUSE_BASE_URL environment variables map correctly."""
    # Test LANGFUSE_HOST
    monkeypatch.setenv("LANGFUSE_HOST", "http://host-env:4000")
    monkeypatch.delenv("LANGFUSE_BASE_URL", raising=False)
    s_host = BaseAppSettings()
    assert s_host.langfuse_base_url == "http://host-env:4000"
    assert s_host.langfuse_host == "http://host-env:4000"

    # Test LANGFUSE_BASE_URL
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "http://base-url-env:5000")
    s_base = BaseAppSettings()
    assert s_base.langfuse_base_url == "http://base-url-env:5000"
    assert s_base.langfuse_host == "http://base-url-env:5000"


# ---------------------------------------------------------------------------
# 2. Agent Adapter _get_langfuse_callback Tests
# ---------------------------------------------------------------------------

def test_get_langfuse_callback_disabled():
    """Verify _get_langfuse_callback returns None when langfuse_enabled is False."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_agent")

    with patch.object(agent_mod, "get_settings") as mock_settings:
        mock_settings.return_value = BaseAppSettings(
            langfuse_enabled=False,
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
        )
        cb = adapter._get_langfuse_callback(AgentInput(prompt="hello"))
        assert cb is None


def test_get_langfuse_callback_missing_credentials():
    """Verify _get_langfuse_callback returns None when keys are missing or blank."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_agent")

    # None public key
    with patch.object(agent_mod, "get_settings") as mock_settings:
        mock_settings.return_value = BaseAppSettings(
            langfuse_enabled=True,
            langfuse_public_key=None,
            langfuse_secret_key="sk-test",
        )
        assert adapter._get_langfuse_callback(AgentInput(prompt="hello")) is None

    # Empty string public key
    with patch.object(agent_mod, "get_settings") as mock_settings:
        mock_settings.return_value = BaseAppSettings(
            langfuse_enabled=True,
            langfuse_public_key="   ",
            langfuse_secret_key="sk-test",
        )
        assert adapter._get_langfuse_callback(AgentInput(prompt="hello")) is None

    # None secret key
    with patch.object(agent_mod, "get_settings") as mock_settings:
        mock_settings.return_value = BaseAppSettings(
            langfuse_enabled=True,
            langfuse_public_key="pk-test",
            langfuse_secret_key=None,
        )
        assert adapter._get_langfuse_callback(AgentInput(prompt="hello")) is None


def test_get_langfuse_callback_instantiation_success():
    """Verify _get_langfuse_callback instantiates and returns a CallbackHandler when enabled with credentials."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_agent")

    with patch.object(agent_mod, "get_settings") as mock_settings:
        mock_settings.return_value = BaseAppSettings(
            langfuse_enabled=True,
            langfuse_public_key="pk-lf-test-key",
            langfuse_secret_key="sk-lf-test-key",
            langfuse_base_url="http://localhost:3000",
        )
        input_data = AgentInput(
            prompt="test prompt",
            session_id="session-123",
            user_id="user-456",
        )
        cb = adapter._get_langfuse_callback(input_data)
        assert cb is not None
        # Handler must have a callable flush method
        assert hasattr(cb, "flush")
        assert callable(cb.flush)
        # Ensure underlying client has tracing_enabled=True, not a dummy disabled client
        client = getattr(cb, "_langfuse_client", None)
        if client is not None:
            assert getattr(client, "_tracing_enabled", getattr(client, "tracing_enabled", True)) is True


def test_get_langfuse_callback_host_normalization():
    """Verify host trailing slashes and whitespace are properly normalized and client is active."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_agent")

    with patch.object(agent_mod, "get_settings") as mock_settings:
        mock_settings.return_value = BaseAppSettings(
            langfuse_enabled=True,
            langfuse_public_key="pk-lf-norm-key",
            langfuse_secret_key="sk-lf-norm-key",
            langfuse_base_url="  http://localhost:3000/  ",
        )
        input_data = AgentInput(
            prompt="test prompt",
            session_id="session-norm",
            user_id="user-norm",
        )
        cb = adapter._get_langfuse_callback(input_data)
        assert cb is not None
        assert os.environ["LANGFUSE_HOST"] == "http://localhost:3000"
        assert os.environ["LANGFUSE_BASE_URL"] == "http://localhost:3000"
        client = getattr(cb, "_langfuse_client", None)
        if client is not None:
            assert getattr(client, "_tracing_enabled", getattr(client, "tracing_enabled", True)) is True


def test_get_langfuse_callback_import_failure_graceful_fallback():
    """Verify graceful fallback when langfuse cannot be imported."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_agent")

    with patch.object(agent_mod, "get_settings") as mock_settings:
        mock_settings.return_value = BaseAppSettings(
            langfuse_enabled=True,
            langfuse_public_key="pk-test",
            langfuse_secret_key="sk-test",
        )
        with patch.dict("sys.modules", {"langfuse": None, "langfuse.callback": None, "langfuse.langchain": None}):
            # Should not raise exception, but return None gracefully
            cb = adapter._get_langfuse_callback(AgentInput(prompt="hello"))
            assert cb is None


# ---------------------------------------------------------------------------
# 3. Execution & Lifecycle (ainvoke and astream) Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_ainvoke_injects_callbacks_and_flushes():
    """Verify ainvoke injects handler into config and flushes in finally block."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_agent")

    mock_handler = MagicMock()
    mock_handler.flush = MagicMock()

    mock_llm = MagicMock()
    mock_llm.ainvoke = MagicMock()

    mock_output_message = MagicMock()
    mock_output_message.content = "Test AI Response"

    captured_config = {}

    async def mock_graph_ainvoke(state, config=None):
        nonlocal captured_config
        captured_config = config
        return {"messages": [mock_output_message]}

    mock_graph = MagicMock()
    mock_graph.ainvoke = mock_graph_ainvoke

    with patch.object(adapter, "_init_llm", return_value=mock_llm), \
         patch.object(adapter, "_build_graph", return_value=mock_graph), \
         patch.object(adapter, "_get_langfuse_callback", return_value=mock_handler):

        input_data = AgentInput(
            prompt="Hello agent",
            session_id="session-xyz",
            user_id="user-abc",
        )

        output = await adapter.ainvoke(input_data)
        assert output.content == "Test AI Response"

        # Verify callbacks injection into execution config
        assert captured_config is not None
        assert "callbacks" in captured_config
        assert mock_handler in captured_config["callbacks"]
        assert captured_config["metadata"]["langfuse_user_id"] == "user-abc"
        assert captured_config["metadata"]["langfuse_session_id"] == "session-xyz"

        # Verify flush was called in finally
        mock_handler.flush.assert_called_once()


@pytest.mark.asyncio
async def test_astream_injects_callbacks_and_flushes():
    """Verify astream injects handler into config and flushes in finally block."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_agent")

    mock_handler = MagicMock()
    mock_handler.flush = MagicMock()

    mock_llm = MagicMock()

    captured_config = {}

    async def mock_graph_astream(state, config=None, stream_mode="messages"):
        nonlocal captured_config
        captured_config = config
        chunk_obj = MagicMock()
        chunk_obj.content = "Streaming chunk"
        yield (chunk_obj, {})

    mock_graph = MagicMock()
    mock_graph.astream = mock_graph_astream

    with patch.object(adapter, "_init_llm", return_value=mock_llm), \
         patch.object(adapter, "_build_graph", return_value=mock_graph), \
         patch.object(adapter, "_get_langfuse_callback", return_value=mock_handler):

        input_data = AgentInput(
            prompt="Hello stream",
            chat_id="chat-789",
            user_id="user-456",
        )

        chunks = []
        async for chunk in adapter.astream(input_data):
            chunks.append(chunk)

        # Verify chunk reception
        token_chunks = [c for c in chunks if c.event == AgentEventType.TOKEN]
        done_chunks = [c for c in chunks if c.event == AgentEventType.DONE]
        assert len(token_chunks) == 1
        assert token_chunks[0].content == "Streaming chunk"
        assert len(done_chunks) == 1

        # Verify callbacks injection into execution config
        assert captured_config is not None
        assert "callbacks" in captured_config
        assert mock_handler in captured_config["callbacks"]
        assert captured_config["metadata"]["langfuse_session_id"] == "chat-789"
        assert captured_config["metadata"]["langfuse_user_id"] == "user-456"

        # Verify flush was called in finally
        mock_handler.flush.assert_called_once()


@pytest.mark.asyncio
async def test_non_blocking_flush_failure():
    """Verify that an exception raised by handler.flush() does not break execution or bubble up."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_agent")

    mock_handler = MagicMock()
    mock_handler.flush.side_effect = RuntimeError("Network timeout connecting to Langfuse server")

    mock_llm = MagicMock()
    mock_output_message = MagicMock()
    mock_output_message.content = "Normal Response"

    async def mock_graph_ainvoke(state, config=None):
        return {"messages": [mock_output_message]}

    mock_graph = MagicMock()
    mock_graph.ainvoke = mock_graph_ainvoke

    with patch.object(adapter, "_init_llm", return_value=mock_llm), \
         patch.object(adapter, "_build_graph", return_value=mock_graph), \
         patch.object(adapter, "_get_langfuse_callback", return_value=mock_handler):

        # Must NOT raise exception despite mock_handler.flush failing
        output = await adapter.ainvoke(AgentInput(prompt="hello"))
        assert output.content == "Normal Response"
        mock_handler.flush.assert_called_once()


@pytest.mark.asyncio
async def test_fallback_when_langfuse_disabled_proceeds_normally():
    """Verify chat proceeds normally without callbacks when Langfuse is disabled."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_agent")

    mock_llm = MagicMock()
    mock_output_message = MagicMock()
    mock_output_message.content = "Normal Response Without Langfuse"

    captured_config = None

    async def mock_graph_ainvoke(state, config=None):
        nonlocal captured_config
        captured_config = config
        return {"messages": [mock_output_message]}

    mock_graph = MagicMock()
    mock_graph.ainvoke = mock_graph_ainvoke

    with patch.object(adapter, "_init_llm", return_value=mock_llm), \
         patch.object(adapter, "_build_graph", return_value=mock_graph), \
         patch.object(adapter, "_get_langfuse_callback", return_value=None):

        output = await adapter.ainvoke(AgentInput(prompt="hello"))
        assert output.content == "Normal Response Without Langfuse"
        # Config should be None or empty dict (no callbacks injected)
        assert captured_config is None or captured_config == {}


@pytest.mark.asyncio
async def test_ainvoke_with_real_langfuse_callback_unmocked():
    """Verify ainvoke with real unmocked CallbackHandler instantiates, injects, and flushes cleanly."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_real_agent")

    mock_llm = MagicMock()
    mock_output_message = MagicMock()
    mock_output_message.content = "Real Handler Result"

    captured_config = None

    async def mock_graph_ainvoke(state, config=None):
        nonlocal captured_config
        captured_config = config
        return {"messages": [mock_output_message]}

    mock_graph = MagicMock()
    mock_graph.ainvoke = mock_graph_ainvoke

    with patch.object(agent_mod, "get_settings") as mock_settings, \
         patch.object(adapter, "_init_llm", return_value=mock_llm), \
         patch.object(adapter, "_build_graph", return_value=mock_graph):

        mock_settings.return_value = BaseAppSettings(
            langfuse_enabled=True,
            langfuse_public_key="pk-lf-real-test",
            langfuse_secret_key="sk-lf-real-test",
            langfuse_base_url="http://localhost:3000",
        )

        input_data = AgentInput(
            prompt="Hello with real handler",
            session_id="session-real-123",
            user_id="user-real-456",
        )

        output = await adapter.ainvoke(input_data)
        assert output.content == "Real Handler Result"
        assert captured_config is not None
        assert "callbacks" in captured_config
        assert len(captured_config["callbacks"]) == 1
        real_cb = captured_config["callbacks"][0]
        assert hasattr(real_cb, "flush")
        assert captured_config["metadata"]["langfuse_session_id"] == "session-real-123"
        assert captured_config["metadata"]["langfuse_user_id"] == "user-real-456"
        assert "test_real_agent" in captured_config["tags"]


@pytest.mark.asyncio
async def test_astream_with_real_langfuse_callback_unmocked():
    """Verify astream with real unmocked CallbackHandler instantiates, injects, and flushes cleanly."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_real_stream_agent")

    mock_llm = MagicMock()
    captured_config = None

    async def mock_graph_astream(state, config=None, stream_mode="messages"):
        nonlocal captured_config
        captured_config = config
        chunk_obj = MagicMock()
        chunk_obj.content = "Real Streaming Token"
        yield (chunk_obj, {})

    mock_graph = MagicMock()
    mock_graph.astream = mock_graph_astream

    with patch.object(agent_mod, "get_settings") as mock_settings, \
         patch.object(adapter, "_init_llm", return_value=mock_llm), \
         patch.object(adapter, "_build_graph", return_value=mock_graph):

        mock_settings.return_value = BaseAppSettings(
            langfuse_enabled=True,
            langfuse_public_key="pk-lf-real-stream",
            langfuse_secret_key="sk-lf-real-stream",
            langfuse_base_url="http://localhost:3000",
        )

        input_data = AgentInput(
            prompt="Stream with real handler",
            chat_id="chat-real-789",
            user_id="user-real-000",
        )

        tokens = []
        async for chunk in adapter.astream(input_data):
            if chunk.event == AgentEventType.TOKEN:
                tokens.append(chunk.content)

        assert tokens == ["Real Streaming Token"]
        assert captured_config is not None
        assert "callbacks" in captured_config
        assert len(captured_config["callbacks"]) == 1
        real_cb = captured_config["callbacks"][0]
        assert hasattr(real_cb, "flush")
        assert captured_config["metadata"]["langfuse_session_id"] == "chat-real-789"
        assert captured_config["metadata"]["langfuse_user_id"] == "user-real-000"
        assert "test_real_stream_agent" in captured_config["tags"]


def test_get_langfuse_callback_handler_attributes_contract():
    """Verify CallbackHandler has session_id, user_id, host, tags, and flush explicitly attached."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_contract_agent")

    with patch.object(agent_mod, "get_settings") as mock_settings:
        mock_settings.return_value = BaseAppSettings(
            langfuse_enabled=True,
            langfuse_public_key="pk-lf-attr-key",
            langfuse_secret_key="sk-lf-attr-key",
            langfuse_base_url="http://localhost:3000",
        )
        # Case A: session_id provided
        inp_a = AgentInput(
            prompt="test",
            session_id="session-contract-1",
            user_id="user-contract-1",
        )
        cb_a = adapter._get_langfuse_callback(inp_a)
        assert cb_a is not None
        assert getattr(cb_a, "session_id", None) == "session-contract-1"
        assert getattr(cb_a, "user_id", None) == "user-contract-1"
        assert getattr(cb_a, "host", None) == "http://localhost:3000"
        assert "test_contract_agent" in getattr(cb_a, "tags", [])
        assert hasattr(cb_a, "flush") and callable(cb_a.flush)

        # Case B: chat_id fallback when session_id is None
        inp_b = AgentInput(
            prompt="test",
            chat_id="chat-contract-fallback",
            user_id="user-contract-2",
        )
        cb_b = adapter._get_langfuse_callback(inp_b)
        assert cb_b is not None
        assert getattr(cb_b, "session_id", None) == "chat-contract-fallback"


@pytest.mark.asyncio
async def test_ainvoke_with_malformed_config_resilience():
    """Verify ainvoke handles malformed/non-dict config inputs without raising exceptions."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_resilience_agent")

    mock_llm = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = "Resilience Success"

    async def mock_graph_ainvoke(state, config=None):
        return {"messages": [mock_msg]}

    mock_graph = MagicMock()
    mock_graph.ainvoke = mock_graph_ainvoke

    with patch.object(adapter, "_init_llm", return_value=mock_llm), \
         patch.object(adapter, "_build_graph", return_value=mock_graph):

        # 1. Config with non-dict metadata
        inp1 = AgentInput(prompt="hi", config={"metadata": "not-a-dict"})
        res1 = await adapter.ainvoke(inp1)
        assert res1.content == "Resilience Success"

        # 2. Config with non-list callbacks
        inp2 = AgentInput(prompt="hi", config={"callbacks": 12345})
        res2 = await adapter.ainvoke(inp2)
        assert res2.content == "Resilience Success"

        # 3. Config with non-list tags
        inp3 = AgentInput(prompt="hi", config={"tags": 99999})
        res3 = await adapter.ainvoke(inp3)
        assert res3.content == "Resilience Success"


@pytest.mark.asyncio
async def test_astream_with_malformed_config_resilience():
    """Verify astream handles malformed config inputs without breaking token streaming."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_stream_resilience_agent")

    mock_llm = MagicMock()

    async def mock_graph_astream(state, config=None, stream_mode="messages"):
        chunk = MagicMock()
        chunk.content = "Resilient Stream Token"
        yield (chunk, {})

    mock_graph = MagicMock()
    mock_graph.astream = mock_graph_astream

    with patch.object(adapter, "_init_llm", return_value=mock_llm), \
         patch.object(adapter, "_build_graph", return_value=mock_graph):

        inp = AgentInput(prompt="hi", config={"metadata": "bad-meta", "callbacks": "bad-callbacks"})
        tokens = []
        async for chunk in adapter.astream(inp):
            if chunk.event == AgentEventType.TOKEN:
                tokens.append(chunk.content)
        assert tokens == ["Resilient Stream Token"]


@pytest.mark.asyncio
async def test_ainvoke_and_astream_awaitable_flush():
    """Verify async awaitable flush methods are properly awaited without runtime warnings."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_awaitable_agent")

    mock_llm = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = "Awaitable Result"

    mock_graph = MagicMock()
    async def mock_graph_ainvoke(state, config=None):
        return {"messages": [mock_msg]}
    async def mock_graph_astream(state, config=None, stream_mode="messages"):
        chunk = MagicMock()
        chunk.content = "Async Chunk"
        yield (chunk, {})
    mock_graph.ainvoke = mock_graph_ainvoke
    mock_graph.astream = mock_graph_astream

    flush_called = False
    class AsyncFlushHandler:
        async def flush(self):
            nonlocal flush_called
            flush_called = True
            await asyncio.sleep(0.001)

    handler = AsyncFlushHandler()

    with patch.object(adapter, "_init_llm", return_value=mock_llm), \
         patch.object(adapter, "_build_graph", return_value=mock_graph), \
         patch.object(adapter, "_get_langfuse_callback", return_value=handler):

        flush_called = False
        res = await adapter.ainvoke(AgentInput(prompt="test ainvoke"))
        assert res.content == "Awaitable Result"
        assert flush_called is True

        flush_called = False
        async for chunk in adapter.astream(AgentInput(prompt="test astream")):
            pass
        assert flush_called is True


def test_langfuse_callback_module_aliasing():
    """Verify langfuse.callback can be imported and accessed even on Langfuse v4+."""
    import sys
    import langfuse

    # Trigger agent module load which sets up the alias
    _load_template_agent_module()

    assert hasattr(langfuse, "callback")
    from langfuse.callback import CallbackHandler
    assert CallbackHandler is not None


def test_extract_text_content_helper():
    """Verify _extract_text_content properly normalizes strings, block lists, and None."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_text_agent")

    assert adapter._extract_text_content("hello") == "hello"
    assert adapter._extract_text_content([{"type": "text", "text": "extracted text"}]) == "extracted text"
    assert adapter._extract_text_content([{"text": "generic text"}]) == "generic text"
    assert adapter._extract_text_content(["part1", "part2"]) == "part1part2"
    assert adapter._extract_text_content(None) == ""
    assert adapter._extract_text_content(12345) == "12345"


@pytest.mark.asyncio
async def test_astream_with_structured_content_blocks_no_validation_error():
    """Verify astream with Anthropic/Bedrock structured content block chunks does not raise ValidationError."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_blocks_agent")

    mock_llm = MagicMock()

    async def mock_graph_astream(state, config=None, stream_mode="messages"):
        chunk = MagicMock()
        # Anthropic content block structure
        chunk.content = [{"type": "text", "text": "Anthropic block stream token"}]
        yield (chunk, {})

    mock_graph = MagicMock()
    mock_graph.astream = mock_graph_astream

    with patch.object(adapter, "_init_llm", return_value=mock_llm), \
         patch.object(adapter, "_build_graph", return_value=mock_graph):

        input_data = AgentInput(prompt="hello stream blocks")
        tokens = []
        async for chunk in adapter.astream(input_data):
            if chunk.event == AgentEventType.TOKEN:
                tokens.append(chunk.content)

        assert tokens == ["Anthropic block stream token"]


@pytest.mark.asyncio
async def test_ainvoke_with_structured_content_blocks():
    """Verify ainvoke with structured content block response extracts clean string."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_blocks_invoke_agent")

    mock_llm = MagicMock()
    mock_msg = MagicMock()
    mock_msg.content = [{"type": "text", "text": "Clean final message content"}]

    async def mock_graph_ainvoke(state, config=None):
        return {"messages": [mock_msg]}

    mock_graph = MagicMock()
    mock_graph.ainvoke = mock_graph_ainvoke

    with patch.object(adapter, "_init_llm", return_value=mock_llm), \
         patch.object(adapter, "_build_graph", return_value=mock_graph):

        res = await adapter.ainvoke(AgentInput(prompt="hello invoke blocks"))
        assert res.content == "Clean final message content"


def test_session_id_whitespace_fallback_to_chat_id():
    """Verify whitespace-only session_id cleanly falls back to chat_id."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_fallback_agent")

    with patch.object(agent_mod, "get_settings") as mock_settings:
        mock_settings.return_value = BaseAppSettings(
            langfuse_enabled=True,
            langfuse_public_key="pk-lf-test",
            langfuse_secret_key="sk-lf-test",
            langfuse_base_url="http://localhost:3000",
        )
        input_data = AgentInput(
            prompt="test fallback",
            session_id="    ",
            chat_id="actual-chat-id-123",
            user_id="  user-padded  ",
        )
        cb = adapter._get_langfuse_callback(input_data)
        assert cb is not None
        assert getattr(cb, "session_id", None) == "actual-chat-id-123"
        assert getattr(cb, "user_id", None) == "user-padded"


def test_prepare_messages_null_input_safe():
    """Verify _prepare_messages handles None safely without throwing AttributeError."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="test_null_prep_agent")
    assert adapter._prepare_messages(None) == []


def test_execution_config_trace_name_and_metadata():
    """Verify _build_execution_config attaches langfuse_trace_name and tags."""
    agent_mod = _load_template_agent_module()
    adapter = agent_mod.ProjectAgentAdapter(name="my_custom_agent")

    mock_handler = MagicMock()
    input_data = AgentInput(prompt="test trace", session_id="s1", user_id="u1")

    config = adapter._build_execution_config(input_data, mock_handler)
    assert config["metadata"]["langfuse_trace_name"] == "my_custom_agent"
    assert config["metadata"]["langfuse_user_id"] == "u1"
    assert config["metadata"]["langfuse_session_id"] == "s1"
    assert "my_custom_agent" in config["tags"]
    assert "agentforge" in config["tags"]

