"""Redis-backed session management, token revocation blacklist, and rate limiter."""

from __future__ import annotations

import json
import time
from typing import Any, Optional

from ...domain.entities.auth_session import AuthSession
from ...domain.ports.auth_session_repository import AuthSessionRepositoryPort


class RedisAuthSessionRepository(AuthSessionRepositoryPort):
    """Session and token blacklist implementation backed by Redis with in-memory fallback."""

    def __init__(self, redis_client: Any = None) -> None:
        self.redis = redis_client
        self._memory_sessions: dict[str, dict[str, Any]] = {}
        self._memory_blacklist: set[str] = set()

    async def save_session(self, session: AuthSession) -> None:
        key = f"auth:session:{session.session_id}"
        ttl = max(1, int((session.expires_at.timestamp() - time.time())))
        data = {
            "session_id": session.session_id,
            "user_id": session.user_id,
            "username": session.username,
            "auth_type": session.auth_type,
            "ip_address": session.ip_address,
            "user_agent": session.user_agent,
            "expires_at": session.expires_at.isoformat(),
        }

        if self.redis:
            try:
                await self.redis.set(key, json.dumps(data), ex=ttl)
                return
            except Exception:
                pass
        self._memory_sessions[session.session_id] = data

    async def get_session(self, session_id: str) -> AuthSession | None:
        key = f"auth:session:{session_id}"
        if self.redis:
            try:
                raw = await self.redis.get(key)
                if raw:
                    data = json.loads(raw)
                    return self._dict_to_session(data)
            except Exception:
                pass

        data = self._memory_sessions.get(session_id)
        if data:
            return self._dict_to_session(data)
        return None

    async def revoke_session(self, session_id: str) -> None:
        key = f"auth:session:{session_id}"
        if self.redis:
            try:
                await self.redis.delete(key)
            except Exception:
                pass
        self._memory_sessions.pop(session_id, None)

    async def is_token_revoked(self, jti: str) -> bool:
        key = f"auth:blacklist:{jti}"
        if self.redis:
            try:
                return bool(await self.redis.exists(key))
            except Exception:
                pass
        return jti in self._memory_blacklist

    async def revoke_token(self, jti: str, ttl_seconds: int = 3600) -> None:
        key = f"auth:blacklist:{jti}"
        if self.redis:
            try:
                await self.redis.set(key, "1", ex=ttl_seconds)
                return
            except Exception:
                pass
        self._memory_blacklist.add(jti)

    def _dict_to_session(self, data: dict[str, Any]) -> AuthSession:
        from datetime import datetime
        return AuthSession(
            session_id=data["session_id"],
            user_id=data["user_id"],
            username=data["username"],
            auth_type=data["auth_type"],
            ip_address=data.get("ip_address"),
            user_agent=data.get("user_agent"),
            expires_at=datetime.fromisoformat(data["expires_at"]),
        )
