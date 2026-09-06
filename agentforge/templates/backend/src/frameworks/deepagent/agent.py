"""DeepAgent reasoning and planning agent implementation."""

from __future__ import annotations

from typing import AsyncGenerator
from ...core.adapter import AgentChunk, AgentEventType, AgentInput, BaseAgentAdapter


class ProjectAgentAdapter(BaseAgentAdapter):
    """Custom DeepAgent reasoning agent adapter."""

    def __init__(self, name: str = "{{ project_name }}") -> None:
        super().__init__(name=name)

    async def astream(self, input_data: AgentInput) -> AsyncGenerator[AgentChunk, None]:
        yield AgentChunk(event=AgentEventType.META, data={"status": "planning"})
        yield AgentChunk(event=AgentEventType.TOKEN, data="[Deep Reasoning Phase 1: Problem Decomposition]\n")
        yield AgentChunk(event=AgentEventType.TOKEN, data=f"Analyzing intent for '{input_data.prompt}'...\n")
        yield AgentChunk(event=AgentEventType.TOKEN, data="Solution synthesis concluded.\n")
        yield AgentChunk(event=AgentEventType.DONE, data={"status": "completed"})
