"""Domain entities for Chat Sessions, Messages, and Human-in-the-Loop Interrupts."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


@dataclass
class ChatMessage:
    """Individual message in a conversation."""
    id: str
    chat_id: str
    role: MessageRole
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class InterruptState:
    """Pending Human-in-the-loop interrupt state."""
    interrupt_id: str
    chat_id: str
    action_name: str
    action_args: dict[str, Any]
    prompt: str
    status: str = "pending"  # pending, approved, rejected
    decision: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ChatSession:
    """Conversation thread session."""
    id: str
    user_id: str
    title: str = "New Conversation"
    active_interrupt: InterruptState | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
