"""Authentication runtime container managing provider lifecycles."""

from __future__ import annotations

import logging
from typing import Any

from .auth_config import AuthConfig, get_auth_config
from .ldap3_provider import LDAP3IdentityProvider
from .native_jwt_service import NativeJWTService
from .password_hashing import DefaultPasswordHasher
from .pysaml2_provider import PySAML2ServiceProvider
from .redis_session import RedisAuthSessionRepository

logger = logging.getLogger(__name__)


class AuthRuntime:
    """Runtime container holding active auth service providers and connection pools."""

    def __init__(self, config: AuthConfig) -> None:
        self.config = config
        self.jwt_service = NativeJWTService(
            secret_key=config.jwt_secret_key,
            algorithm=config.jwt_algorithm,
            access_token_expire_minutes=config.access_token_expire_minutes,
            refresh_token_expire_days=config.refresh_token_expire_days,
        )
        self.password_hasher = DefaultPasswordHasher()
        self.session_repo = RedisAuthSessionRepository()

        self.ldap_provider: LDAP3IdentityProvider | None = None
        if config.ldap_enabled:
            self.ldap_provider = LDAP3IdentityProvider(
                server_uri=config.ldap_server_uri,
                bind_dn=config.ldap_bind_dn,
                bind_password=config.ldap_bind_password,
                user_search_base=config.ldap_user_base,
            )

        self.saml_provider: PySAML2ServiceProvider | None = None
        if config.saml_enabled:
            self.saml_provider = PySAML2ServiceProvider(
                entity_id=config.saml_sp_entity_id,
                acs_url=config.saml_acs_url,
            )

    async def initialize(self) -> None:
        logger.info("AuthRuntime initialized (LDAP: %s, SAML: %s)", bool(self.ldap_provider), bool(self.saml_provider))

    async def close(self) -> None:
        logger.info("AuthRuntime shutting down.")


async def build_auth_runtime(config: AuthConfig | None = None) -> AuthRuntime:
    cfg = config or get_auth_config()
    runtime = AuthRuntime(cfg)
    await runtime.initialize()
    return runtime
