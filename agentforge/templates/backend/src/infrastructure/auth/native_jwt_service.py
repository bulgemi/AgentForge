"""JWT token issuance and signature verification service."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

import jwt


class NativeJWTService:
    """Issues and verifies JWT access and refresh tokens using HMAC-SHA256."""

    def __init__(
        self,
        secret_key: str = "agentforge-insecure-dev-secret-key-change-me",
        algorithm: str = "HS256",
        access_token_expire_minutes: int = 60,
        refresh_token_expire_days: int = 7,
    ) -> None:
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = access_token_expire_minutes
        self.refresh_token_expire_days = refresh_token_expire_days

    def create_access_token(
        self,
        subject: str,
        claims: Mapping[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(minutes=self.access_token_expire_minutes))

        payload: dict[str, Any] = {
            "sub": subject,
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "access",
        }
        if claims:
            payload.update(claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def create_refresh_token(
        self,
        subject: str,
        claims: Mapping[str, Any] | None = None,
        expires_delta: timedelta | None = None,
    ) -> str:
        now = datetime.now(timezone.utc)
        expire = now + (expires_delta or timedelta(days=self.refresh_token_expire_days))

        payload: dict[str, Any] = {
            "sub": subject,
            "jti": str(uuid.uuid4()),
            "iat": int(now.timestamp()),
            "exp": int(expire.timestamp()),
            "type": "refresh",
        }
        if claims:
            payload.update(claims)

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> dict[str, Any]:
        """Decode and verify JWT signature and expiration."""
        return jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
