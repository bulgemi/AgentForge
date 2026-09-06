"""FastAPI routes for Agent Conversations and Real-time SSE Token Streaming."""

from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ....application.chat_service import ChatService
from ....application.dto.chat_dto import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatSessionResponse,
    CreateChatRequest,
    InterruptResolveRequest,
)
from ....core.database import get_async_session
from ....core.streaming import SSETokenStreamer
from ...database.chat_model import SQLModelChatRepository
from ..dependencies.auth_deps import get_current_user
from ....domain.entities.user import User

router = APIRouter(prefix="/api/v1/chats", tags=["Chat & Streaming"])


def get_agent_adapter(request: Request):
    """Retrieve injected framework agent adapter from application state."""
    adapter = getattr(request.app.state, "agent_adapter", None)
    if not adapter:
        # Fallback to default mock adapter for standalone tests
        from ....core.adapter import LangGraphAdapter
        return LangGraphAdapter(name="default-agent")
    return adapter


@router.post("", response_model=ChatSessionResponse, status_code=status.HTTP_201_CREATED)
async def create_chat(
    req: CreateChatRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    request: Request,
) -> ChatSessionResponse:
    """Create a new chat conversation thread."""
    chat_repo = SQLModelChatRepository(session)
    adapter = get_agent_adapter(request)
    service = ChatService(chat_repo, adapter)
    created = await service.create_chat(user_id=user.id, title=req.title)
    return ChatSessionResponse(
        id=created.id,
        user_id=created.user_id,
        title=created.title,
        created_at=created.created_at.isoformat(),
        updated_at=created.updated_at.isoformat(),
    )


@router.get("", response_model=list[ChatSessionResponse])
async def list_chats(
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[ChatSessionResponse]:
    """List recent conversation sessions for authenticated user."""
    chat_repo = SQLModelChatRepository(session)
    sessions = await chat_repo.list_sessions(user_id=user.id)
    return [
        ChatSessionResponse(
            id=s.id,
            user_id=s.user_id,
            title=s.title,
            created_at=s.created_at.isoformat(),
            updated_at=s.updated_at.isoformat(),
        )
        for s in sessions
    ]


@router.get("/{chat_id}/messages", response_model=list[ChatMessageResponse])
async def get_messages(
    chat_id: str,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> list[ChatMessageResponse]:
    """Retrieve historical messages for a chat session."""
    chat_repo = SQLModelChatRepository(session)
    messages = await chat_repo.get_messages(chat_id=chat_id)
    return [
        ChatMessageResponse(
            id=m.id,
            chat_id=m.chat_id,
            role=m.role.value if hasattr(m.role, "value") else str(m.role),
            content=m.content,
            metadata=m.metadata,
            created_at=m.created_at.isoformat(),
        )
        for m in messages
    ]


@router.post("/{chat_id}/stream")
async def stream_chat_response(
    chat_id: str,
    req: ChatMessageRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    request: Request,
) -> StreamingResponse:
    """Send user message and stream real-time tokens and agent events via SSE."""
    chat_repo = SQLModelChatRepository(session)
    adapter = get_agent_adapter(request)
    service = ChatService(chat_repo, adapter)

    chunk_gen = service.stream_message(
        chat_id=chat_id,
        user_id=user.id,
        message=req.message,
        session_id=req.session_id,
    )

    streamer = SSETokenStreamer()
    return StreamingResponse(
        streamer.sse_event_generator(chunk_gen),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{chat_id}/interrupts/{interrupt_id}/resolve")
async def resolve_interrupt(
    chat_id: str,
    interrupt_id: str,
    req: InterruptResolveRequest,
    user: Annotated[User, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    request: Request,
) -> dict[str, str]:
    """Resolve a pending Human-in-the-Loop interrupt."""
    chat_repo = SQLModelChatRepository(session)
    adapter = get_agent_adapter(request)
    service = ChatService(chat_repo, adapter)

    res = await service.resolve_interrupt(chat_id, interrupt_id, req.decision)
    if not res:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interrupt not found.")
    return {"status": "resolved", "decision": req.decision}
