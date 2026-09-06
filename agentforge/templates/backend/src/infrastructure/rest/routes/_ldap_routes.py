"""FastAPI routes for LDAP Directory Authentication."""

from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from ....application.auth_service import AuthenticationService
from ....application.dto.auth_dto import LoginRequest, TokenResponse
from ....core.database import get_async_session
from ...auth.auth_runtime import AuthRuntime
from ...database.user_model import SQLModelUserRepository
from ..dependencies.auth_deps import get_auth_runtime

router = APIRouter(prefix="/api/v1/auth", tags=["LDAP"])


@router.post("/ldap", response_model=TokenResponse)
async def ldap_login(
    req: LoginRequest,
    request: Request,
    runtime: Annotated[AuthRuntime, Depends(get_auth_runtime)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> TokenResponse:
    """Direct LDAP Directory login endpoint."""
    req.auth_type = "ldap"
    user_repo = SQLModelUserRepository(session)
    service = AuthenticationService(
        user_repo=user_repo,
        session_repo=runtime.session_repo,
        jwt_service=runtime.jwt_service,
        password_hasher=runtime.password_hasher,
        ldap_provider=runtime.ldap_provider,
    )
    try:
        ip = request.client.host if request.client else None
        agent = request.headers.get("user-agent")
        return await service.authenticate(req, ip_address=ip, user_agent=agent)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
