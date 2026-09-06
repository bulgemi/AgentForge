"""Agent Development Kit (ADK) modular agent implementation."""

from __future__ import annotations

from typing import AsyncGenerator
from ...core.adapter import AgentChunk, AgentEventType, AgentInput, BaseAgentAdapter


class ProjectAgentAdapter(BaseAgentAdapter):
    """Custom ADK modular tool agent adapter."""

    def __init__(self, name: str = "{{ project_name }}") -> None:
        super().__init__(name=name)

    async def astream(self, input_data: AgentInput) -> AsyncGenerator[AgentChunk, None]:
        yield AgentChunk(event=AgentEventType.TOKEN, data=f"[ADK Tool Runner: {self.name}]\n")
        yield AgentChunk(event=AgentEventType.TOKEN, data=f"Invoking tools for: {input_data.prompt}\n")
        yield AgentChunk(event=AgentEventType.DONE, data={"status": "completed"})
