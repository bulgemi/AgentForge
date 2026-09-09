"""Application service orchestrating authentication (ID/PW, LDAP, SAML) and tokens."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from ..domain.entities.auth_session import AuthSession
from ..domain.entities.user import User, UserStatus
from ..domain.ports.auth_session_repository import AuthSessionRepositoryPort
from ..domain.ports.user_repository import UserRepositoryPort
from .dto.auth_dto import LoginRequest, TokenResponse


class AuthenticationService:
    """Handles authentication across ID/Password, LDAP, and SAML SSO providers."""

    def __init__(
        self,
        user_repo: UserRepositoryPort,
        session_repo: AuthSessionRepositoryPort,
        jwt_service: Any,
        password_hasher: Any,
        ldap_provider: Any = None,
        saml_provider: Any = None,
    ) -> None:
        self.user_repo = user_repo
        self.session_repo = session_repo
        self.jwt_service = jwt_service
        self.password_hasher = password_hasher
        self.ldap_provider = ldap_provider
        self.saml_provider = saml_provider

    async def authenticate(
        self,
        request: LoginRequest,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> TokenResponse:
        """Authenticate user via requested auth_type and issue JWT access/refresh tokens."""
        auth_type = request.auth_type.lower()

        if auth_type == "ldap":
            if not self.ldap_provider:
                raise ValueError("LDAP provider is not configured.")
            user_info = await self.ldap_provider.authenticate(request.username, request.password)
            user = await self.user_repo.get_by_username(request.username)
            if not user:
                # Auto-provision LDAP user
                user = User(
                    id=str(uuid.uuid4()),
                    username=request.username,
                    email=user_info.get("email"),
                    role=user_info.get("role", "user"),
                )
                await self.user_repo.save(user)
        elif auth_type == "saml":
            raise NotImplementedError("SAML authentication flows via /sso/acs endpoint.")
        else:
            # Default ID/PW
            user = await self.user_repo.get_by_username(request.username)
            if not user:
                raise PermissionError("Invalid username or password.")
            if user.status == UserStatus.LOCKED:
                raise PermissionError("Account is locked due to consecutive failed attempts.")

            # Validate password
            stored_hash = getattr(user, "password_hash", None)
            if not stored_hash or not self.password_hasher.verify(request.password, stored_hash):
                user.failed_login_attempts += 1
                if user.failed_login_attempts >= 5:
                    user.status = UserStatus.LOCKED
                await self.user_repo.save(user)
                raise PermissionError("Invalid username or password.")

            # Reset attempts on success
            if user.failed_login_attempts > 0:
                user.failed_login_attempts = 0
                await self.user_repo.save(user)

        # Issue Tokens
        session_id = str(uuid.uuid4())
        expires_in = 3600  # 1 hour
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(seconds=expires_in)

        access_token = self.jwt_service.create_access_token(
            subject=user.id,
            claims={
                "username": user.username,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "session_id": session_id,
            },
            expires_delta=timedelta(seconds=expires_in),
        )
        refresh_token = self.jwt_service.create_refresh_token(
            subject=user.id,
            claims={"session_id": session_id},
        )

        session = AuthSession(
            session_id=session_id,
            user_id=user.id,
            username=user.username,
            auth_type=auth_type,
            ip_address=ip_address,
            user_agent=user_agent,
            expires_at=expires_at,
        )
        await self.session_repo.save_session(session)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
            user_id=user.id,
            username=user.username,
            role=user.role.value if hasattr(user.role, "value") else str(user.role),
            status=user.status.value if hasattr(user.status, "value") else str(user.status),
        )

    async def change_password(
        self,
        user_id: str,
        current_password: str,
        new_password: str,
    ) -> None:
        """Change user password, enforce complexity, and activate account."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise LookupError("User not found.")

        # 1. Verify current password
        stored_hash = getattr(user, "password_hash", None)
        if not stored_hash or not self.password_hasher.verify(current_password, stored_hash):
            raise ValueError("현재 비밀번호가 일치하지 않습니다.")

        # 2. Check that new password differs from current password
        if current_password == new_password:
            raise ValueError("새 비밀번호는 현재(임시) 비밀번호와 달라야 합니다.")

        # 3. Password complexity validation: at least 8 chars, letters, numbers, and special characters
        if len(new_password) < 8:
            raise ValueError("비밀번호는 최소 8자 이상이어야 합니다.")

        has_letter = any(c.isalpha() for c in new_password)
        has_digit = any(c.isdigit() for c in new_password)
        special_characters = set('~!@#$%^&*()-_=+[{]}\\|;:\'",<.>/?`')
        has_special = any(c in special_characters for c in new_password)

        if not (has_letter and has_digit and has_special):
            raise ValueError("비밀번호는 영문, 숫자, 특수문자를 모두 포함해야 합니다.")

        # 4. Hash and save new password, set status to ACTIVE
        new_hash = self.password_hasher.hash(new_password)
        setattr(user, "password_hash", new_hash)
        user.status = UserStatus.ACTIVE
        user.failed_login_attempts = 0
        await self.user_repo.save(user)

    async def logout(self, session_id: str, jti: str | None = None) -> None:
        """Revoke active session and blacklist token."""
        await self.session_repo.revoke_session(session_id)
        if jti:
            await self.session_repo.revoke_token(jti, ttl_seconds=3600)
