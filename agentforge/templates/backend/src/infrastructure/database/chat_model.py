"""SQLModel database models and repository implementation for Conversations."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Sequence
from sqlmodel import Field, SQLModel, select
from sqlalchemy import DateTime
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.chat import ChatMessage, ChatSession, InterruptState, MessageRole
from ...domain.ports.chat_repository import ChatRepositoryPort


class ChatSessionTable(SQLModel, table=True):
    __tablename__ = "chat_sessions"

    id: str = Field(primary_key=True)
    user_id: str = Field(index=True, nullable=False)
    title: str = Field(default="New Conversation")
    active_interrupt_json: str | None = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )


class ChatMessageTable(SQLModel, table=True):
    __tablename__ = "chat_messages"

    id: str = Field(primary_key=True)
    chat_id: str = Field(index=True, nullable=False)
    role: str = Field(index=True, nullable=False)
    content: str = Field(nullable=False)
    metadata_json: str | None = Field(default="{}")
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_type=DateTime(timezone=True),
    )


class SQLModelChatRepository(ChatRepositoryPort):
    """SQLModel async repository implementing ChatRepositoryPort."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_session(self, user_id: str, title: str = "New Conversation") -> ChatSession:
        session_id = str(uuid.uuid4())
        rec = ChatSessionTable(id=session_id, user_id=user_id, title=title)
        self.session.add(rec)
        await self.session.commit()
        await self.session.refresh(rec)
        return ChatSession(id=rec.id, user_id=rec.user_id, title=rec.title, created_at=rec.created_at, updated_at=rec.updated_at)

    async def get_session(self, chat_id: str) -> ChatSession | None:
        stmt = select(ChatSessionTable).where(ChatSessionTable.id == chat_id)
        res = await self.session.execute(stmt)
        rec = res.scalar_one_or_none()
        if not rec:
            return None
        interrupt = None
        if rec.active_interrupt_json:
            data = json.loads(rec.active_interrupt_json)
            interrupt = InterruptState(**data)
        return ChatSession(id=rec.id, user_id=rec.user_id, title=rec.title, active_interrupt=interrupt, created_at=rec.created_at, updated_at=rec.updated_at)

    async def list_sessions(self, user_id: str, limit: int = 50) -> Sequence[ChatSession]:
        stmt = select(ChatSessionTable).where(ChatSessionTable.user_id == user_id).order_by(ChatSessionTable.updated_at.desc()).limit(limit)
        res = await self.session.execute(stmt)
        return [
            ChatSession(id=r.id, user_id=r.user_id, title=r.title, created_at=r.created_at, updated_at=r.updated_at)
            for r in res.scalars().all()
        ]

    async def save_message(self, message: ChatMessage) -> ChatMessage:
        rec = ChatMessageTable(
            id=message.id,
            chat_id=message.chat_id,
            role=message.role.value if hasattr(message.role, "value") else str(message.role),
            content=message.content,
            metadata_json=json.dumps(message.metadata or {}),
            created_at=message.created_at,
        )
        self.session.add(rec)
        # Touch session updated_at
        stmt = select(ChatSessionTable).where(ChatSessionTable.id == message.chat_id)
        sess_rec = (await self.session.execute(stmt)).scalar_one_or_none()
        if sess_rec:
            sess_rec.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return message

    async def get_messages(self, chat_id: str, limit: int = 100) -> Sequence[ChatMessage]:
        stmt = select(ChatMessageTable).where(ChatMessageTable.chat_id == chat_id).order_by(ChatMessageTable.created_at.asc()).limit(limit)
        res = await self.session.execute(stmt)
        return [
            ChatMessage(
                id=r.id,
                chat_id=r.chat_id,
                role=MessageRole(r.role),
                content=r.content,
                metadata=json.loads(r.metadata_json or "{}"),
                created_at=r.created_at,
            )
            for r in res.scalars().all()
        ]

    async def set_interrupt(self, chat_id: str, interrupt: InterruptState) -> None:
        stmt = select(ChatSessionTable).where(ChatSessionTable.id == chat_id)
        rec = (await self.session.execute(stmt)).scalar_one_or_none()
        if rec:
            rec.active_interrupt_json = json.dumps({
                "interrupt_id": interrupt.interrupt_id,
                "chat_id": interrupt.chat_id,
                "action_name": interrupt.action_name,
                "action_args": interrupt.action_args,
                "prompt": interrupt.prompt,
                "status": interrupt.status,
                "decision": interrupt.decision,
            })
            await self.session.commit()

    async def resolve_interrupt(self, interrupt_id: str, decision: str) -> InterruptState | None:
        # Search session with active interrupt
        stmt = select(ChatSessionTable).where(ChatSessionTable.active_interrupt_json.contains(interrupt_id))
        rec = (await self.session.execute(stmt)).scalar_one_or_none()
        if rec and rec.active_interrupt_json:
            data = json.loads(rec.active_interrupt_json)
            data["status"] = "resolved"
            data["decision"] = decision
            rec.active_interrupt_json = None
            await self.session.commit()
            return InterruptState(**data)
        return None
