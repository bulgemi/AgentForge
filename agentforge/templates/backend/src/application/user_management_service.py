"""Application service for administrator user account operations."""

from __future__ import annotations

import secrets
import string
import uuid
from typing import Sequence

from ..domain.entities.user import User, UserRole, UserStatus
from ..domain.ports.user_repository import UserRepositoryPort
from .dto.user_dto import CreateUserRequest, ResetPasswordResponse, UpdateUserRequest, UserResponse


class UserManagementService:
    """Administrator use cases for managing enterprise user accounts."""

    def __init__(self, user_repo: UserRepositoryPort, password_hasher: Any) -> None:
        self.user_repo = user_repo
        self.password_hasher = password_hasher

    def _generate_temp_password(self, length: int = 12) -> str:
        chars = string.ascii_letters + string.digits + "!@#$%^&*"
        return "".join(secrets.choice(chars) for _ in range(length))

    async def create_user(self, req: CreateUserRequest) -> tuple[UserResponse, str]:
        existing = await self.user_repo.get_by_username(req.username)
        if existing:
            raise ValueError(f"Username '{req.username}' already exists.")

        raw_pwd = req.initial_password or self._generate_temp_password()
        pwd_hash = self.password_hasher.hash(raw_pwd)

        role = UserRole(req.role.lower())
        user = User(
            id=str(uuid.uuid4()),
            username=req.username,
            email=req.email,
            role=role,
            status=UserStatus.PENDING_PASSWORD_CHANGE if not req.initial_password else UserStatus.ACTIVE,
        )
        setattr(user, "password_hash", pwd_hash)
        saved = await self.user_repo.save(user)

        return self._to_response(saved), raw_pwd

    async def list_users(
        self,
        page: int = 1,
        size: int = 20,
        role: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[UserResponse], int]:
        offset = (page - 1) * size
        users, total = await self.user_repo.list_users(
            offset=offset, limit=size, role=role, status=status, search=search
        )
        return [self._to_response(u) for u in users], total

    async def unlock_user(self, user_id: str) -> UserResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise LookupError(f"User {user_id} not found.")
        user.failed_login_attempts = 0
        user.status = UserStatus.ACTIVE
        saved = await self.user_repo.save(user)
        return self._to_response(saved)

    async def reset_password(self, user_id: str) -> ResetPasswordResponse:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise LookupError(f"User {user_id} not found.")

        temp_pwd = self._generate_temp_password()
        pwd_hash = self.password_hasher.hash(temp_pwd)
        setattr(user, "password_hash", pwd_hash)
        user.status = UserStatus.PENDING_PASSWORD_CHANGE
        user.failed_login_attempts = 0
        await self.user_repo.save(user)

        return ResetPasswordResponse(user_id=user_id, temporary_password=temp_pwd)

    def _to_response(self, u: User) -> UserResponse:
        return UserResponse(
            id=u.id,
            username=u.username,
            email=u.email,
            role=u.role.value if hasattr(u.role, "value") else str(u.role),
            status=u.status.value if hasattr(u.status, "value") else str(u.status),
            failed_login_attempts=u.failed_login_attempts,
            created_at=u.created_at.isoformat(),
            updated_at=u.updated_at.isoformat(),
        )
