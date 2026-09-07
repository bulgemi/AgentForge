"""SQLModel database models and repository implementation for User and Permissions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Sequence
from sqlmodel import Field, SQLModel, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...domain.entities.user import User, UserRole, UserStatus
from ...domain.ports.user_repository import UserRepositoryPort


class UserTable(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(primary_key=True)
    username: str = Field(index=True, unique=True, nullable=False)
    email: str | None = Field(default=None, index=True)
    password_hash: str | None = Field(default=None)
    role: str = Field(default="user", index=True)
    status: str = Field(default="active", index=True)
    failed_login_attempts: int = Field(default=0)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SQLModelUserRepository(UserRepositoryPort):
    """SQLModel async repository implementing UserRepositoryPort."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: str) -> User | None:
        stmt = select(UserTable).where(UserTable.id == user_id)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        return self._to_entity(record) if record else None

    async def get_by_username(self, username: str) -> User | None:
        stmt = select(UserTable).where(UserTable.username == username)
        result = await self.session.execute(stmt)
        record = result.scalar_one_or_none()
        return self._to_entity(record) if record else None

    async def save(self, user: User) -> User:
        stmt = select(UserTable).where(UserTable.id == user.id)
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()

        pwd_hash = getattr(user, "password_hash", None)

        now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        c_at = user.created_at.replace(tzinfo=None) if (user.created_at and user.created_at.tzinfo) else (user.created_at or now_naive)
        u_at = user.updated_at.replace(tzinfo=None) if (user.updated_at and user.updated_at.tzinfo) else (user.updated_at or now_naive)

        if not existing:
            existing = UserTable(
                id=user.id,
                username=user.username,
                email=user.email,
                password_hash=pwd_hash,
                role=user.role.value if hasattr(user.role, "value") else str(user.role),
                status=user.status.value if hasattr(user.status, "value") else str(user.status),
                failed_login_attempts=user.failed_login_attempts,
                created_at=c_at,
                updated_at=u_at,
            )
            self.session.add(existing)
        else:
            existing.username = user.username
            existing.email = user.email
            if pwd_hash:
                existing.password_hash = pwd_hash
            existing.role = user.role.value if hasattr(user.role, "value") else str(user.role)
            existing.status = user.status.value if hasattr(user.status, "value") else str(user.status)
            existing.failed_login_attempts = user.failed_login_attempts
            existing.updated_at = now_naive

        await self.session.commit()
        await self.session.refresh(existing)
        return self._to_entity(existing)

    async def list_users(
        self,
        offset: int = 0,
        limit: int = 20,
        role: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[User], int]:
        stmt = select(UserTable)
        if role:
            stmt = stmt.where(UserTable.role == role)
        if status:
            stmt = stmt.where(UserTable.status == status)
        if search:
            stmt = stmt.where(UserTable.username.contains(search) | UserTable.email.contains(search))

        # Count total
        all_recs = (await self.session.execute(stmt)).scalars().all()
        total = len(all_recs)

        # Apply pagination
        paginated_stmt = stmt.offset(offset).limit(limit)
        page_recs = (await self.session.execute(paginated_stmt)).scalars().all()

        return [self._to_entity(r) for r in page_recs], total

    async def update_status(self, user_id: str, status: UserStatus) -> bool:
        stmt = select(UserTable).where(UserTable.id == user_id)
        res = await self.session.execute(stmt)
        user = res.scalar_one_or_none()
        if not user:
            return False
        user.status = status.value
        user.updated_at = datetime.now(timezone.utc)
        await self.session.commit()
        return True

    def _to_entity(self, rec: UserTable) -> User:
        user = User(
            id=rec.id,
            username=rec.username,
            email=rec.email,
            role=UserRole(rec.role),
            status=UserStatus(rec.status),
            failed_login_attempts=rec.failed_login_attempts,
            created_at=rec.created_at,
            updated_at=rec.updated_at,
        )
        setattr(user, "password_hash", rec.password_hash)
        return user
