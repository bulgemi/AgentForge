"""agentforge/core/streaming.py

Streaming Engine and Request Governance Layer for AgentForge.
Provides SSETokenStreamer for high-performance Server-Sent Events serialization
and RuntimeContext for concurrency control, correlation tracking, and client disconnect handling.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from enum import Enum
import inspect
import json
import logging
from typing import Any, AsyncGenerator, Dict, Optional, Union
import uuid

from .adapter import AgentChunk, AgentEventType

logger = logging.getLogger(__name__)


# ============================================================================
# 1. Runtime Context & Concurrency Governance
# ============================================================================

class RuntimeContext:
    """
    Request-scoped execution context managing correlation IDs, resource semaphores,
    and client disconnection detection.
    """

    _global_semaphores: Dict[str, asyncio.Semaphore] = {}

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        session_id: Optional[str] = None,
        chat_id: Optional[str] = None,
        user_id: Optional[str] = None,
        request: Optional[Any] = None,  # FastAPI/Starlette Request
        semaphore_limits: Optional[Dict[str, int]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        client_disconnected: Optional[asyncio.Event] = None,
        concurrency_semaphore: Optional[asyncio.Semaphore] = None,
    ) -> None:
        self.correlation_id: str = correlation_id or str(uuid.uuid4())
        self.session_id: Optional[str] = session_id
        self.chat_id: Optional[str] = chat_id
        self.user_id: Optional[str] = user_id
        self.request: Optional[Any] = request
        self.metadata: Dict[str, Any] = metadata or {}
        self.cancellation_event: asyncio.Event = client_disconnected if client_disconnected is not None else asyncio.Event()
        self._concurrency_semaphore: Optional[asyncio.Semaphore] = concurrency_semaphore

        # Initialize default concurrency limits
        limits = {"LLM": 5, "HTTP": 10, "MCP": 5}
        if semaphore_limits:
            limits.update(semaphore_limits)
            for name, limit in semaphore_limits.items():
                self._global_semaphores[name] = asyncio.Semaphore(limit)

        for name, limit in limits.items():
            if name not in self._global_semaphores:
                self._global_semaphores[name] = asyncio.Semaphore(limit)

    @property
    def client_disconnected(self) -> asyncio.Event:
        """
        asyncio.Event signaling client disconnection or request cancellation (PROJECT.md:87).
        Mirrors and coordinates directly with cancellation_event.
        """
        return self.cancellation_event

    @client_disconnected.setter
    def client_disconnected(self, event: asyncio.Event) -> None:
        self.cancellation_event = event

    @property
    def concurrency_semaphore(self) -> asyncio.Semaphore:
        """
        Active concurrency semaphore for execution governance (PROJECT.md:87).
        Provides access to the active LLM concurrency semaphore.
        """
        if self._concurrency_semaphore is not None:
            return self._concurrency_semaphore
        sem = self._global_semaphores.get("LLM")
        if sem is None:
            sem = asyncio.Semaphore(5)
            self._global_semaphores["LLM"] = sem
        return sem

    @concurrency_semaphore.setter
    def concurrency_semaphore(self, sem: asyncio.Semaphore) -> None:
        self._concurrency_semaphore = sem
        self._global_semaphores["LLM"] = sem

    @classmethod
    def reset_semaphores(cls) -> None:
        """Reset global semaphores dictionary (useful for test isolation)."""
        cls._global_semaphores.clear()

    async def is_cancelled(self) -> bool:
        """
        Check if current execution has been cancelled or client aborted the HTTP connection.
        Safely inspects request.is_disconnected() if available.
        """
        if self.cancellation_event.is_set():
            return True

        if self.request is not None and hasattr(self.request, "is_disconnected"):
            try:
                if inspect.iscoroutinefunction(self.request.is_disconnected):
                    disconnected = await self.request.is_disconnected()
                elif callable(self.request.is_disconnected):
                    disconnected = self.request.is_disconnected()
                    if inspect.isawaitable(disconnected):
                        disconnected = await disconnected
                else:
                    disconnected = bool(self.request.is_disconnected)

                if disconnected:
                    logger.info(
                        f"[RuntimeContext] Client disconnect detected for correlation_id={self.correlation_id}"
                    )
                    self.cancellation_event.set()
                    return True
            except Exception as e:
                logger.debug(f"[RuntimeContext] Error inspecting client disconnect: {e}")

        return False

    def cancel(self, reason: Optional[str] = None) -> None:
        """Manually trigger cancellation of the active request."""
        logger.info(f"[RuntimeContext] Request {self.correlation_id} cancelled. Reason: {reason}")
        self.cancellation_event.set()

    @asynccontextmanager
    async def acquire_semaphore(self, name: str, timeout: Optional[float] = None) -> AsyncGenerator[None, None]:
        """
        Asynchronously acquire a named concurrency semaphore slot (e.g. 'LLM', 'HTTP', 'MCP').
        Releases slot immediately upon exit or error.
        """
        if name == "LLM" and self._concurrency_semaphore is not None:
            sem = self._concurrency_semaphore
        else:
            sem = self._global_semaphores.get(name)
            if sem is None:
                sem = asyncio.Semaphore(5)
                self._global_semaphores[name] = sem

        acquired = False
        try:
            if timeout is not None:
                await asyncio.wait_for(sem.acquire(), timeout=timeout)
            else:
                await sem.acquire()
            acquired = True
            yield
        finally:
            if acquired:
                sem.release()

    async def __aenter__(self) -> "RuntimeContext":
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if exc_type and issubclass(exc_type, asyncio.CancelledError):
            self.cancel("Task cancelled")


# ============================================================================
# 2. SSE Token Streamer
# ============================================================================

class SSETokenStreamer:
    """
    High-performance converter transforming asynchronous generators of AgentChunk
    into standard Server-Sent Events (SSE) wire format.
    """

    @staticmethod
    def stream_headers() -> Dict[str, str]:
        """
        Standard HTTP response headers required for unbuffered, realtime SSE streaming.
        X-Accel-Buffering: no prevents Nginx reverse proxies from buffering chunks.
        """
        return {
            "Content-Type": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }

    @staticmethod
    def format_sse_event(
        event: Union[AgentEventType, str],
        data: Union[Dict[str, Any], str],
        event_id: Optional[str] = None,
        retry: Optional[int] = None,
    ) -> str:
        """
        Format an event and payload into RFC-compliant Server-Sent Events wire format.
        """
        event_name = event.value if isinstance(event, Enum) else str(event)

        if isinstance(data, str):
            payload_str = data
        else:
            payload_str = json.dumps(data, default=str)

        lines: list[str] = [f"event: {event_name}"]
        if event_id:
            lines.append(f"id: {event_id}")
        if retry is not None:
            lines.append(f"retry: {retry}")

        for line in payload_str.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
            lines.append(f"data: {line}")

        return "\n".join(lines) + "\n\n"

    async def astream_sse(
        self,
        source: AsyncGenerator[AgentChunk, None],
        context: Optional[RuntimeContext] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream AgentChunk generator as formatted SSE wire text.
        Guarantees:
        1. Cancellation detection: breaks immediately if client disconnects.
        2. Error shielding: catches generator exceptions and yields event: error.
        3. Terminal completion: guarantees event: done or event: interrupt marks end of stream.
        """
        terminal_emitted = False
        aborted = False

        try:
            # Proactive pre-flight cancellation check
            if context and await context.is_cancelled():
                logger.info(f"[SSEStreamer] Aborting stream: context already cancelled ({context.correlation_id})")
                aborted = True
                return

            async for chunk in source:
                # Proactive disconnect check
                if context and await context.is_cancelled():
                    logger.info(f"[SSEStreamer] Aborting stream on client cancellation ({context.correlation_id})")
                    aborted = True
                    break

                event_name = chunk.event.value if isinstance(chunk.event, Enum) else str(chunk.event)

                payload: Dict[str, Any] = {
                    "type": event_name,
                    "content": chunk.content if chunk.content is not None else (chunk.data if isinstance(chunk.data, str) else None),
                    "data": chunk.data,
                    "metadata": chunk.metadata,
                    "timestamp": chunk.timestamp,
                }
                if chunk.error:
                    payload["error"] = chunk.error
                if chunk.id:
                    payload["id"] = chunk.id

                if event_name in (AgentEventType.DONE.value, AgentEventType.INTERRUPT.value):
                    terminal_emitted = True

                yield self.format_sse_event(event=event_name, data=payload, event_id=chunk.id)

        except (GeneratorExit, asyncio.CancelledError):
            aborted = True
            logger.info("[SSEStreamer] Stream task or generator was cancelled / closed early")
            raise
        except Exception as exc:
            logger.error(f"[SSEStreamer] Uncaught error during stream generation: {exc}", exc_info=True)
            err_payload = {
                "type": AgentEventType.ERROR.value,
                "error": str(exc),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            terminal_emitted = True
            try:
                yield self.format_sse_event(event=AgentEventType.ERROR, data=err_payload)
            except (GeneratorExit, asyncio.CancelledError):
                aborted = True
                raise
        finally:
            # Guarantee terminal done event only for normal completion (not aborted or closed early)
            if not terminal_emitted and not aborted:
                done_payload = {
                    "type": AgentEventType.DONE.value,
                    "content": "",
                    "data": {"finish_reason": "completed"},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                yield self.format_sse_event(event=AgentEventType.DONE, data=done_payload)

    # Alias for interface contract compatibility (PROJECT.md line 83)
    sse_event_generator = astream_sse

    def to_fastapi_response(
        self,
        source: AsyncGenerator[AgentChunk, None],
        context: Optional[RuntimeContext] = None,
        status_code: int = 200,
    ) -> Any:
        """
        Construct a FastAPI/Starlette StreamingResponse with proper SSE headers.
        Lazily imports StreamingResponse so core remains usable without FastAPI installed.
        """
        try:
            from fastapi.responses import StreamingResponse
        except ImportError:
            try:
                from starlette.responses import StreamingResponse
            except ImportError as e:
                raise RuntimeError("FastAPI or Starlette must be installed to use to_fastapi_response()") from e

        return StreamingResponse(
            content=self.astream_sse(source=source, context=context),
            status_code=status_code,
            headers=self.stream_headers(),
            media_type="text/event-stream",
        )
