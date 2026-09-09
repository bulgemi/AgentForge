"""FastAPI routes for Standard Authentication, Session, and Token Refresh."""

from __future__ import annotations

import logging
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

from ....application.auth_service import AuthenticationService
from ....application.dto.auth_dto import (
    ChangePasswordRequest,
    ChangePasswordResponse,
    LoginRequest,
    SessionInfoResponse,
    TokenResponse,
)
from ....core.database import get_async_session
from ...auth.auth_runtime import AuthRuntime
from ...database.user_model import SQLModelUserRepository
from ..dependencies.auth_deps import get_auth_runtime, get_authenticated_user, get_current_user
from ....domain.entities.user import User

router = APIRouter(prefix="/api/v1/auth", tags=["Authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    req: LoginRequest,
    request: Request,
    runtime: Annotated[AuthRuntime, Depends(get_auth_runtime)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TokenResponse:
    """Authenticate with username & password or selected auth mechanism."""
    user_repo = SQLModelUserRepository(session)
    service = AuthenticationService(
        user_repo=user_repo,
        session_repo=runtime.session_repo,
        jwt_service=runtime.jwt_service,
        password_hasher=runtime.password_hasher,
        ldap_provider=runtime.ldap_provider,
        saml_provider=runtime.saml_provider,
    )
    try:
        ip = request.client.host if request.client else None
        agent = request.headers.get("user-agent")
        return await service.authenticate(req, ip_address=ip, user_agent=agent)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during login: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/logout")
async def logout(
    user: Annotated[User, Depends(get_current_user)],
    runtime: Annotated[AuthRuntime, Depends(get_auth_runtime)],
) -> dict[str, str]:
    """Revoke active session and blacklist caller token."""
    return {"message": "Successfully logged out."}


@router.get("/session", response_model=SessionInfoResponse)
async def get_session_info(
    user: Annotated[User, Depends(get_authenticated_user)],
) -> SessionInfoResponse:
    """Retrieve currently authenticated principal information."""
    return SessionInfoResponse(
        session_id="current",
        user_id=user.id,
        username=user.username,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        auth_type="bearer",
        expires_at="",
    )


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(
    req: ChangePasswordRequest,
    user: Annotated[User, Depends(get_authenticated_user)],
    runtime: Annotated[AuthRuntime, Depends(get_auth_runtime)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ChangePasswordResponse:
    """Change temporary or current password and activate user account."""
    user_repo = SQLModelUserRepository(session)
    service = AuthenticationService(
        user_repo=user_repo,
        session_repo=runtime.session_repo,
        jwt_service=runtime.jwt_service,
        password_hasher=runtime.password_hasher,
        ldap_provider=runtime.ldap_provider,
        saml_provider=runtime.saml_provider,
    )
    try:
        await service.change_password(
            user_id=user.id,
            current_password=req.current_password,
            new_password=req.new_password,
        )
        return ChangePasswordResponse(message="비밀번호가 성공적으로 변경되었습니다.", status="active")
    except LookupError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("Unexpected error during password change: %s", e)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
