"""Port interface for Chat storage."""

from __future__ import annotations

from typing import Protocol, Sequence
from ..entities.chat import ChatMessage, ChatSession, InterruptState


class ChatRepositoryPort(Protocol):
    """Abstract persistence for conversations and messages."""

    async def create_session(self, user_id: str, title: str = "New Conversation") -> ChatSession:
        ...

    async def get_session(self, chat_id: str) -> ChatSession | None:
        ...

    async def list_sessions(self, user_id: str, limit: int = 50) -> Sequence[ChatSession]:
        ...

    async def save_message(self, message: ChatMessage) -> ChatMessage:
        ...

    async def get_messages(self, chat_id: str, limit: int = 100) -> Sequence[ChatMessage]:
        ...

    async def set_interrupt(self, chat_id: str, interrupt: InterruptState) -> None:
        ...

    async def resolve_interrupt(self, interrupt_id: str, decision: str) -> InterruptState | None:
        ...
