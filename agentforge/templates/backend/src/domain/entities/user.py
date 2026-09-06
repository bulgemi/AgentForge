"""Domain entities for User, Authentication and Authorization."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class UserRole(str, Enum):
    """System authorization roles."""
    ADMIN = "admin"
    USER = "user"
    AUDITOR = "auditor"


class UserStatus(str, Enum):
    """User account lifecycle status."""
    ACTIVE = "active"
    LOCKED = "locked"
    SUSPENDED = "suspended"
    PENDING_PASSWORD_CHANGE = "pending_password_change"


@dataclass
class User:
    """Core domain representation of an authenticated user."""
    id: str
    username: str
    email: str | None = None
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.ACTIVE
    failed_login_attempts: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def is_active(self) -> bool:
        return self.status == UserStatus.ACTIVE

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN
