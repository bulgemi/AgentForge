"""AWS Bedrock enterprise agent implementation."""

from __future__ import annotations

from typing import AsyncGenerator
from ...core.adapter import AgentChunk, AgentEventType, AgentInput, BaseAgentAdapter


class ProjectAgentAdapter(BaseAgentAdapter):
    """Custom AWS Bedrock Agent adapter."""

    def __init__(self, name: str = "{{ project_name }}") -> None:
        super().__init__(name=name)

    async def astream(self, input_data: AgentInput) -> AsyncGenerator[AgentChunk, None]:
        yield AgentChunk(event=AgentEventType.META, data={"provider": "aws-bedrock"})
        yield AgentChunk(event=AgentEventType.TOKEN, data=f"[AWS Bedrock Agent: {self.name}]\n")
        yield AgentChunk(event=AgentEventType.TOKEN, data=f"Secure prompt execution: '{input_data.prompt}'\n")
        yield AgentChunk(event=AgentEventType.DONE, data={"status": "completed"})
