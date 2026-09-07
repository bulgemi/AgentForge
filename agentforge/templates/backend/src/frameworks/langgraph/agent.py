"""LangGraph StateGraph custom agent implementation."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncGenerator, Optional
try:
    from ....core.adapter import (
        AgentChunk,
        AgentEventType,
        AgentInput,
        AgentOutput,
        BaseAgentAdapter,
    )
except (ImportError, ValueError):
    from src.core.adapter import (
        AgentChunk,
        AgentEventType,
        AgentInput,
        AgentOutput,
        BaseAgentAdapter,
    )


class ProjectAgentAdapter(BaseAgentAdapter):
    """Custom LangGraph agent adapter."""

    def __init__(self, name: str = "{{ project_name }}", **kwargs: Any) -> None:
        super().__init__(name=name, **kwargs)
        self.name = name

    async def ainvoke(self, input_data: AgentInput, context: Optional[Any] = None) -> AgentOutput:
        prompt = input_data.get_prompt_or_last_message() if hasattr(input_data, "get_prompt_or_last_message") else getattr(input_data, "prompt", "")
        return AgentOutput(
            content=f"Hello! I am {self.name} powered by LangGraph. You said: {prompt}"
        )

    async def astream(self, input_data: AgentInput, context: Optional[Any] = None) -> AsyncGenerator[AgentChunk, None]:
        prompt = input_data.get_prompt_or_last_message() if hasattr(input_data, "get_prompt_or_last_message") else getattr(input_data, "prompt", "")
        tokens = [
            f"Hello from [LangGraph Agent: {self.name}]!\n\n",
            f"Processing your request: '{prompt}'\n\n",
            "This project is running with full Clean Architecture and real-time SSE streaming.",
        ]
        for token in tokens:
            await asyncio.sleep(0.03)
            yield AgentChunk(event=AgentEventType.TOKEN, data=token, content=token)
        yield AgentChunk(event=AgentEventType.DONE, data={"status": "completed"})

    async def ahandle_interrupt(
        self,
        interrupt_id: str,
        decision: str,
        state_update: Optional[dict[str, Any]] = None,
        context: Optional[Any] = None,
    ) -> AgentOutput:
        return AgentOutput(
            content=f"[LangGraph Agent: {self.name}] Resumed at {interrupt_id} with decision: '{decision}'",
            metadata={"resumed": True, "interrupt_id": interrupt_id, "decision": decision},
        )
