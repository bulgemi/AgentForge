"""Application service for Chat conversations and agent streaming integration."""

from __future__ import annotations

import uuid
from typing import Any, AsyncGenerator

from ..core.adapter import AgentChunk, AgentInput, BaseAgentAdapter
from ..domain.entities.chat import ChatMessage, ChatSession, InterruptState, MessageRole
from ..domain.ports.chat_repository import ChatRepositoryPort


class ChatService:
    """Manages chat conversations and orchestrates execution via BaseAgentAdapter."""

    def __init__(self, chat_repo: ChatRepositoryPort, agent_adapter: BaseAgentAdapter) -> None:
        self.chat_repo = chat_repo
        self.agent_adapter = agent_adapter

    async def create_chat(self, user_id: str, title: str = "New Conversation") -> ChatSession:
        return await self.chat_repo.create_session(user_id=user_id, title=title)

    async def stream_message(
        self,
        chat_id: str,
        user_id: str,
        message: str,
        session_id: str | None = None,
    ) -> AsyncGenerator[AgentChunk, None]:
        """Record user message and stream agent response chunks."""
        # 1. Save user message
        user_msg = ChatMessage(
            id=str(uuid.uuid4()),
            chat_id=chat_id,
            role=MessageRole.USER,
            content=message,
        )
        await self.chat_repo.save_message(user_msg)

        # 2. Build AgentInput
        agent_input = AgentInput(
            prompt=message,
            session_id=session_id or chat_id,
            user_id=user_id,
        )

        full_content: list[str] = []

        # 3. Stream from adapter
        async for chunk in self.agent_adapter.astream(agent_input):
            if chunk.event.value == "token":
                text = chunk.content if chunk.content is not None else (chunk.data if isinstance(chunk.data, str) else "")
                if text:
                    full_content.append(text)
            elif chunk.event.value == "interrupt":
                # Save interrupt state
                interrupt = InterruptState(
                    interrupt_id=chunk.id or str(uuid.uuid4()),
                    chat_id=chat_id,
                    action_name=chunk.data.get("action", "action") if isinstance(chunk.data, dict) else "action",
                    action_args=chunk.data.get("args", {}) if isinstance(chunk.data, dict) else {},
                    prompt=str(chunk.data),
                )
                await self.chat_repo.set_interrupt(chat_id, interrupt)
            yield chunk

        # 4. Save final assistant message
        if full_content:
            asst_msg = ChatMessage(
                id=str(uuid.uuid4()),
                chat_id=chat_id,
                role=MessageRole.ASSISTANT,
                content="".join(full_content),
            )
            await self.chat_repo.save_message(asst_msg)

    async def resolve_interrupt(
        self,
        chat_id: str,
        interrupt_id: str,
        decision: str,
    ) -> InterruptState | None:
        return await self.chat_repo.resolve_interrupt(interrupt_id, decision)
