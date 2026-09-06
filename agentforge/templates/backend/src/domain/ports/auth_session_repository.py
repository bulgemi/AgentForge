"""Port interface for Auth Session and Token Blacklist."""

from __future__ import annotations

from typing import Protocol
from ..entities.auth_session import AuthSession


class AuthSessionRepositoryPort(Protocol):
    """Abstract store for sessions and token revocation."""

    async def save_session(self, session: AuthSession) -> None:
        ...

    async def get_session(self, session_id: str) -> AuthSession | None:
        ...

    async def revoke_session(self, session_id: str) -> None:
        ...

    async def is_token_revoked(self, jti: str) -> bool:
        ...

    async def revoke_token(self, jti: str, ttl_seconds: int) -> None:
        ...
