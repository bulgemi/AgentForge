"""LangChain LCEL chain custom agent implementation."""

from __future__ import annotations

from typing import AsyncGenerator
from ...core.adapter import AgentChunk, AgentEventType, AgentInput, BaseAgentAdapter


class ProjectAgentAdapter(BaseAgentAdapter):
    """Custom LangChain LCEL agent adapter."""

    def __init__(self, name: str = "{{ project_name }}") -> None:
        super().__init__(name=name)

    async def astream(self, input_data: AgentInput) -> AsyncGenerator[AgentChunk, None]:
        tokens = [
            f"[LangChain Chain: {self.name}] received input: '{input_data.prompt}'\n",
            "Executing sequential runnable pipeline...",
        ]
        for token in tokens:
            yield AgentChunk(event=AgentEventType.TOKEN, data=token)
        yield AgentChunk(event=AgentEventType.DONE, data={"status": "completed"})
