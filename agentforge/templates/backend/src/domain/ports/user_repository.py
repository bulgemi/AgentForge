"""Port interfaces for repositories and external integrations."""

from __future__ import annotations

from typing import Protocol, Sequence
from ..entities.user import User, UserStatus


class UserRepositoryPort(Protocol):
    """Abstract port for user persistence."""

    async def get_by_id(self, user_id: str) -> User | None:
        ...

    async def get_by_username(self, username: str) -> User | None:
        ...

    async def save(self, user: User) -> User:
        ...

    async def list_users(
        self,
        offset: int = 0,
        limit: int = 20,
        role: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[User], int]:
        ...

    async def update_status(self, user_id: str, status: UserStatus) -> bool:
        ...
