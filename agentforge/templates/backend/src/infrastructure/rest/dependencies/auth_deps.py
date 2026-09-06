"""FastAPI dependencies for Authentication and Role-based Access Control."""

from __future__ import annotations

from typing import Annotated
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.database import get_async_session
from ..auth.auth_runtime import AuthRuntime
from ..database.user_model import SQLModelUserRepository
from ...domain.entities.user import User, UserRole, UserStatus

security = HTTPBearer(auto_error=False)


async def get_auth_runtime(request: Request) -> AuthRuntime:
    runtime = getattr(request.app.state, "auth_runtime", None)
    if not runtime:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication runtime is not initialized.",
        )
    return runtime


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
    runtime: Annotated[AuthRuntime, Depends(get_auth_runtime)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    """Extract and validate JWT Bearer token, verifying session and user active status."""
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = runtime.jwt_service.decode_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check revocation blacklist
    jti = payload.get("jti")
    if jti and await runtime.session_repo.is_token_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    repo = SQLModelUserRepository(session)
    user = await repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is not active.")

    return user


async def require_admin_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Authorize only administrative users."""
    if not user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator privileges required.",
        )
    return user
