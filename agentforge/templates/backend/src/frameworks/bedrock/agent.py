"""AWS Bedrock enterprise agent implementation."""

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
    """Custom AWS Bedrock Agent adapter."""

    def __init__(self, name: str = "{{ project_name }}", **kwargs: Any) -> None:
        super().__init__(name=name, **kwargs)
        self.name = name

    async def ainvoke(self, input_data: AgentInput, context: Optional[Any] = None) -> AgentOutput:
        prompt = input_data.get_prompt_or_last_message() if hasattr(input_data, "get_prompt_or_last_message") else getattr(input_data, "prompt", "")
        return AgentOutput(
            content=f"Hello! I am {self.name} powered by AWS Bedrock. You said: {prompt}"
        )

    async def astream(self, input_data: AgentInput, context: Optional[Any] = None) -> AsyncGenerator[AgentChunk, None]:
        prompt = input_data.get_prompt_or_last_message() if hasattr(input_data, "get_prompt_or_last_message") else getattr(input_data, "prompt", "")
        yield AgentChunk(event=AgentEventType.META, data={"provider": "aws-bedrock"})
        await asyncio.sleep(0.03)
        yield AgentChunk(event=AgentEventType.TOKEN, data=f"[AWS Bedrock Agent: {self.name}]\n\n", content=f"[AWS Bedrock Agent: {self.name}]\n\n")
        await asyncio.sleep(0.03)
        yield AgentChunk(event=AgentEventType.TOKEN, data=f"Secure prompt execution for: '{prompt}'...\n\n", content=f"Secure prompt execution for: '{prompt}'...\n\n")
        await asyncio.sleep(0.03)
        yield AgentChunk(event=AgentEventType.TOKEN, data="Execution completed.", content="Execution completed.")
        yield AgentChunk(event=AgentEventType.DONE, data={"status": "completed"})

    async def ahandle_interrupt(
        self,
        interrupt_id: str,
        decision: str,
        state_update: Optional[dict[str, Any]] = None,
        context: Optional[Any] = None,
    ) -> AgentOutput:
        return AgentOutput(
            content=f"[Bedrock: {self.name}] Resumed at {interrupt_id} with decision: '{decision}'",
            metadata={"resumed": True, "interrupt_id": interrupt_id, "decision": decision},
        )
