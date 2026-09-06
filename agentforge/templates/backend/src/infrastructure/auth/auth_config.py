"""Authentication configuration loaded from environment variables."""

from __future__ import annotations

from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings


class AuthConfig(BaseSettings):
    """Unified configuration for Multi-protocol Authentication."""
    jwt_secret_key: str = Field("agentforge-secret-key-super-secure-change-in-prod", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field("HS256", alias="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(60, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(7, alias="REFRESH_TOKEN_EXPIRE_DAYS")

    # LDAP
    ldap_enabled: bool = Field(False, alias="LDAP_ENABLED")
    ldap_server_uri: str = Field("ldap://127.0.0.1:389", alias="LDAP_SERVER_URI")
    ldap_bind_dn: str = Field("", alias="LDAP_BIND_DN")
    ldap_bind_password: str = Field("", alias="LDAP_BIND_PASSWORD")
    ldap_user_base: str = Field("ou=users,dc=example,dc=com", alias="LDAP_USER_BASE")

    # SAML
    saml_enabled: bool = Field(False, alias="SAML_ENABLED")
    saml_sp_entity_id: str = Field("https://localhost:8000/sp", alias="SAML_SP_ENTITY_ID")
    saml_acs_url: str = Field("https://localhost:8000/api/v1/sso/acs", alias="SAML_ACS_URL")

    # Redis
    redis_url: str | None = Field(None, alias="REDIS_URL")

    # CORS
    cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
        alias="CORS_ORIGINS",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def get_auth_config() -> AuthConfig:
    return AuthConfig()
