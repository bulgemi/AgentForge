"""Data Transfer Objects for User Administration."""

from __future__ import annotations

from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class CreateUserRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr | None = None
    role: str = Field("user", description="admin, user, auditor")
    initial_password: str | None = None


class UpdateUserRequest(BaseModel):
    email: EmailStr | None = None
    role: str | None = None
    status: str | None = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: str | None = None
    role: str
    status: str
    failed_login_attempts: int = 0
    created_at: str
    updated_at: str


class ResetPasswordResponse(BaseModel):
    user_id: str
    temporary_password: str
