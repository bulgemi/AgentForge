"""LangGraph StateGraph custom agent implementation."""

from __future__ import annotations

from typing import AsyncGenerator
from ...core.adapter import AgentChunk, AgentEventType, AgentInput, BaseAgentAdapter


class ProjectAgentAdapter(BaseAgentAdapter):
    """Custom LangGraph agent adapter."""

    def __init__(self, name: str = "{{ project_name }}") -> None:
        super().__init__(name=name)

    async def ainvoke(self, input_data: AgentInput) -> AgentOutput:
        return AgentOutput(
            content=f"Hello! I am {self.name} powered by LangGraph. You said: {input_data.prompt}"
        )

    async def astream(self, input_data: AgentInput) -> AsyncGenerator[AgentChunk, None]:
        tokens = [
            f"Hello from [LangGraph Agent: {self.name}]!\n\n",
            f"Processing your request: '{input_data.prompt}'\n\n",
            "This project is running with full Clean Architecture and real-time SSE streaming.",
        ]
        for token in tokens:
            yield AgentChunk(event=AgentEventType.TOKEN, data=token)
        yield AgentChunk(event=AgentEventType.DONE, data={"status": "completed"})
