"""FastAPI routes for SAML 2.0 Single Sign-On."""

from __future__ import annotations

from typing import Annotated
from fastapi import APIRouter, Depends, Form, HTTPException, Response, status
from fastapi.responses import HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from ....application.dto.auth_dto import TokenResponse
from ....core.database import get_async_session
from ...auth.auth_runtime import AuthRuntime
from ..dependencies.auth_deps import get_auth_runtime

router = APIRouter(prefix="/api/v1/sso", tags=["SAML SSO"])


@router.get("/metadata", response_class=Response)
async def get_metadata(
    runtime: Annotated[AuthRuntime, Depends(get_auth_runtime)],
) -> Response:
    """Return SAML 2.0 SP metadata XML."""
    if not runtime.saml_provider:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="SAML SSO is not configured or enabled.",
        )
    xml = runtime.saml_provider.get_sp_metadata()
    return Response(content=xml, media_type="application/xml")


@router.post("/acs")
async def assertion_consumer_service(
    SAMLResponse: Annotated[str, Form()],
    runtime: Annotated[AuthRuntime, Depends(get_auth_runtime)],
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> dict[str, str]:
    """SAML Assertion Consumer Service (ACS) endpoint."""
    if not runtime.saml_provider:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="SAML not enabled.")

    info = await runtime.saml_provider.process_authn_response(SAMLResponse)
    return {"message": "SAML authenticated successfully", "user": info.get("name_id", "")}
