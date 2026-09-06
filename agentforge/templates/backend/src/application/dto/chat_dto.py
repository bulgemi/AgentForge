"""Data Transfer Objects for Conversations and Stream."""

from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


class CreateChatRequest(BaseModel):
    title: str = Field("New Conversation", description="Chat title")


class ChatSessionResponse(BaseModel):
    id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


class ChatMessageRequest(BaseModel):
    message: str = Field(..., description="User prompt or input")
    session_id: str | None = None


class ChatMessageResponse(BaseModel):
    id: str
    chat_id: str
    role: str
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class InterruptResolveRequest(BaseModel):
    decision: str = Field(..., description="approve or reject")
    feedback: str | None = None
