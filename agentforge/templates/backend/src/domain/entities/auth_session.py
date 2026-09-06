"""Domain entities for Authentication Sessions and Token Metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class AuthSession:
    """Authenticated user active session record."""
    session_id: str
    user_id: str
    username: str
    auth_type: str  # id_pw, ldap, saml
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revoked: bool = False
