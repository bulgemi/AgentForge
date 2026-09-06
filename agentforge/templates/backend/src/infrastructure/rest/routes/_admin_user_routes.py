"""FastAPI routes for Administrator User and Account Governance."""

from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....application.dto.user_dto import (
    CreateUserRequest,
    ResetPasswordResponse,
    UserResponse,
)
from ....application.user_management_service import UserManagementService
from ....core.database import Page, PageMetadata, get_async_session
from ...auth.auth_runtime import AuthRuntime
from ...database.user_model import SQLModelUserRepository
from ..dependencies.auth_deps import get_auth_runtime, require_admin_user
from ....domain.entities.user import User

router = APIRouter(prefix="/api/v1/admin/users", tags=["User Administration"])


@router.get("", response_model=dict)
async def list_users(
    admin: Annotated[User, Depends(require_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    runtime: Annotated[AuthRuntime, Depends(get_auth_runtime)],
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    role: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    search: str | None = Query(None),
) -> dict:
    """List system users with pagination, role, status filtering and search."""
    user_repo = SQLModelUserRepository(session)
    service = UserManagementService(user_repo, runtime.password_hasher)
    items, total = await service.list_users(
        page=page, size=size, role=role, status=status_filter, search=search
    )
    total_pages = max(1, (total + size - 1) // size)
    return {
        "items": [i.model_dump() for i in items],
        "metadata": {
            "page": page,
            "size": size,
            "total_elements": total,
            "total_pages": total_pages,
        },
    }


@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_user(
    req: CreateUserRequest,
    admin: Annotated[User, Depends(require_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    runtime: Annotated[AuthRuntime, Depends(get_auth_runtime)],
) -> dict:
    """Create a new user account with role assignment."""
    user_repo = SQLModelUserRepository(session)
    service = UserManagementService(user_repo, runtime.password_hasher)
    try:
        user_resp, initial_pwd = await service.create_user(req)
        return {"user": user_resp.model_dump(), "initial_password": initial_pwd}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/{user_id}/unlock", response_model=UserResponse)
async def unlock_user(
    user_id: str,
    admin: Annotated[User, Depends(require_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    runtime: Annotated[AuthRuntime, Depends(get_auth_runtime)],
) -> UserResponse:
    """Unlock a locked user account and reset failed login counter."""
    user_repo = SQLModelUserRepository(session)
    service = UserManagementService(user_repo, runtime.password_hasher)
    try:
        return await service.unlock_user(user_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("/{user_id}/reset-password", response_model=ResetPasswordResponse)
async def reset_password(
    user_id: str,
    admin: Annotated[User, Depends(require_admin_user)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
    runtime: Annotated[AuthRuntime, Depends(get_auth_runtime)],
) -> ResetPasswordResponse:
    """Generate a temporary password and require password change on next login."""
    user_repo = SQLModelUserRepository(session)
    service = UserManagementService(user_repo, runtime.password_hasher)
    try:
        return await service.reset_password(user_id)
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
