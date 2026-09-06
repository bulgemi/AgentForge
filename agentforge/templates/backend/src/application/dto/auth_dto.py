"""Data Transfer Objects for Authentication and Session."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(..., description="User identifier or LDAP username")
    password: str = Field(..., description="User password")
    auth_type: str = Field("id_pw", description="Authentication mechanism: id_pw, ldap, saml")


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: str
    username: str
    role: str


class SessionInfoResponse(BaseModel):
    session_id: str
    user_id: str
    username: str
    role: str
    auth_type: str
    expires_at: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str
