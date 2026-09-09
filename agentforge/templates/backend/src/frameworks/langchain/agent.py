"""LangChain LCEL chain custom agent implementation."""

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
    """Custom LangChain LCEL agent adapter."""

    def __init__(self, name: str = "{{ project_name }}", **kwargs: Any) -> None:
        super().__init__(name=name, **kwargs)
        self.name = name

    async def ainvoke(self, input_data: AgentInput, context: Optional[Any] = None) -> AgentOutput:
        prompt = input_data.get_prompt_or_last_message() if hasattr(input_data, "get_prompt_or_last_message") else getattr(input_data, "prompt", "")
        return AgentOutput(
            content=f"Hello! I am {self.name} powered by LangChain. You said: {prompt}"
        )

    async def astream(self, input_data: AgentInput, context: Optional[Any] = None) -> AsyncGenerator[AgentChunk, None]:
        prompt = input_data.get_prompt_or_last_message() if hasattr(input_data, "get_prompt_or_last_message") else getattr(input_data, "prompt", "")
        tokens = [
            f"[LangChain Chain: {self.name}] received input: '{prompt}'\n\n",
            "Executing sequential runnable pipeline...\n\n",
            "Pipeline completed successfully.",
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
            content=f"[LangChain Chain: {self.name}] Resumed at {interrupt_id} with decision: '{decision}'",
            metadata={"resumed": True, "interrupt_id": interrupt_id, "decision": decision},
        )
