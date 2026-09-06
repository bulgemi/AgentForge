"""AgentForge Core Runtime Configuration Module.

Provides Pydantic Settings management with environment variable and .env loading.
Designed for standalone zero-dependency execution.
"""

from __future__ import annotations

from functools import lru_cache
import json
from typing import Any, List, Literal, Optional, Union
from pydantic import AliasChoices, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class BaseAppSettings(BaseSettings):
    """Base application settings for AgentForge projects."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
        populate_by_name=True,
        protected_namespaces=("settings_",),
    )

    # -------------------------------------------------------------------------
    # 1. Core Application Settings
    # -------------------------------------------------------------------------
    app_name: str = Field(
        default="AgentForge App",
        validation_alias=AliasChoices("APP_NAME", "PROJECT_NAME"),
        description="Application display and project name",
    )
    environment: Literal["dev", "prd", "test"] = Field(
        default="dev",
        validation_alias=AliasChoices("ENVIRONMENT", "ENV"),
        description="Deployment target environment: dev, prd, or test",
    )
    host: str = Field(
        default="0.0.0.0",
        validation_alias=AliasChoices("HOST", "APP_HOST", "SERVER_HOST"),
        description="Bind host for the API server",
    )
    port: int = Field(
        default=8000,
        validation_alias=AliasChoices("PORT", "APP_PORT", "SERVER_PORT"),
        description="Port for the API server",
    )
    cors_origins: List[str] = Field(
        default_factory=lambda: ["*"],
        validation_alias=AliasChoices("CORS_ORIGINS", "CORS_ALLOWED_ORIGINS"),
        description="List of allowed CORS origins or comma-separated string",
    )
    log_level: str = Field(
        default="INFO",
        validation_alias=AliasChoices("LOG_LEVEL", "LOGGING_LEVEL"),
        description="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    log_format: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LOG_FORMAT"),
        description="Custom log format string",
    )
    debug: bool = Field(
        default=False,
        validation_alias=AliasChoices("DEBUG", "APP_DEBUG"),
        description="Enable debug mode and verbose tracebacks",
    )

    # -------------------------------------------------------------------------
    # 2. Database Settings
    # -------------------------------------------------------------------------
    database_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "DB_URL"),
        description="Full database connection URL. If omitted, built from components.",
    )
    database_driver: str = Field(
        default="postgresql+asyncpg",
        validation_alias=AliasChoices("DATABASE_DRIVER", "DB_DRIVER"),
        description="Database dialect and driver (e.g. postgresql+asyncpg, sqlite+aiosqlite)",
    )
    database_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("DATABASE_HOST", "DB_HOST"),
        description="Database server hostname or IP",
    )
    database_port: int = Field(
        default=5432,
        validation_alias=AliasChoices("DATABASE_PORT", "DB_PORT"),
        description="Database server port",
    )
    database_username: str = Field(
        default="postgres",
        validation_alias=AliasChoices("DATABASE_USERNAME", "DATABASE_USER", "DB_USER"),
        description="Database username",
    )
    database_password: str = Field(
        default="postgres",
        validation_alias=AliasChoices("DATABASE_PASSWORD", "DB_PASSWORD"),
        description="Database password",
    )
    database_dbname: str = Field(
        default="agentforge",
        validation_alias=AliasChoices("DATABASE_DBNAME", "DATABASE_NAME", "DB_NAME"),
        description="Database catalog / database name",
    )
    database_schema: str = Field(
        default="public",
        validation_alias=AliasChoices("DATABASE_SCHEMA", "DB_SCHEMA"),
        description="Database schema name",
    )
    database_auto_migrate: bool = Field(
        default=True,
        validation_alias=AliasChoices("DATABASE_AUTO_MIGRATE", "DB_AUTO_MIGRATE"),
        description="Automatically initialize or migrate database schema on startup",
    )
    database_pool_size: int = Field(
        default=10,
        validation_alias=AliasChoices("DATABASE_POOL_SIZE", "DB_POOL_SIZE"),
        description="Base connection pool size",
    )
    database_max_overflow: int = Field(
        default=20,
        validation_alias=AliasChoices("DATABASE_MAX_OVERFLOW", "DB_MAX_OVERFLOW"),
        description="Maximum connections to allow beyond pool_size",
    )
    database_pool_recycle: int = Field(
        default=1800,
        validation_alias=AliasChoices("DATABASE_POOL_RECYCLE", "DB_POOL_RECYCLE"),
        description="Seconds before recycling persistent connections",
    )
    database_pool_timeout: int = Field(
        default=30,
        validation_alias=AliasChoices("DATABASE_POOL_TIMEOUT", "DB_POOL_TIMEOUT"),
        description="Seconds to wait before timing out on pool checkout",
    )
    database_pool_pre_ping: bool = Field(
        default=True,
        validation_alias=AliasChoices("DATABASE_POOL_PRE_PING", "DB_POOL_PRE_PING"),
        description="Verify connection validity on checkout",
    )

    # -------------------------------------------------------------------------
    # 3. Redis Settings
    # -------------------------------------------------------------------------
    redis_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("REDIS_URL"),
        description="Full Redis URL. If omitted, built from components.",
    )
    redis_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("REDIS_HOST"),
        description="Redis server hostname or IP",
    )
    redis_port: int = Field(
        default=6379,
        validation_alias=AliasChoices("REDIS_PORT"),
        description="Redis server port",
    )
    redis_password: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("REDIS_PASSWORD"),
        description="Optional Redis authentication password",
    )
    redis_db: int = Field(
        default=0,
        validation_alias=AliasChoices("REDIS_DB"),
        description="Redis database index",
    )
    redis_ssl: bool = Field(
        default=False,
        validation_alias=AliasChoices("REDIS_SSL"),
        description="Enable SSL/TLS for Redis connection",
    )

    # -------------------------------------------------------------------------
    # 4. Security Settings
    # -------------------------------------------------------------------------
    secret_key: str = Field(
        default="change-me-in-production-at-least-32-chars-long",
        validation_alias=AliasChoices("SECRET_KEY", "JWT_SECRET_KEY"),
        description="Cryptographic secret key for signing tokens and sessions",
    )
    jwt_algorithm: str = Field(
        default="HS256",
        validation_alias=AliasChoices("JWT_ALGORITHM"),
        description="JWT signing algorithm",
    )
    access_token_expire_minutes: int = Field(
        default=60,
        validation_alias=AliasChoices("ACCESS_TOKEN_EXPIRE_MINUTES", "JWT_ACCESS_TOKEN_EXPIRE_MINUTES"),
        description="Access token validity period in minutes",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        validation_alias=AliasChoices("REFRESH_TOKEN_EXPIRE_DAYS", "JWT_REFRESH_TOKEN_EXPIRE_DAYS"),
        description="Refresh token validity period in days",
    )

    # -------------------------------------------------------------------------
    # 5. LLM Settings
    # -------------------------------------------------------------------------
    default_provider: str = Field(
        default="openai",
        validation_alias=AliasChoices("DEFAULT_PROVIDER", "LLM_PROVIDER"),
        description="Default LLM provider (openai, anthropic, google, bedrock, etc.)",
    )
    default_model: str = Field(
        default="gpt-4o",
        validation_alias=AliasChoices("DEFAULT_MODEL", "LLM_MODEL", "OPENAI_MODEL_NAME"),
        description="Default LLM model identifier",
    )
    timeout: float = Field(
        default=60.0,
        validation_alias=AliasChoices("LLM_TIMEOUT", "TIMEOUT", "LLM_TIMEOUT_SEC"),
        description="Timeout in seconds for LLM provider API calls",
    )
    max_retries: int = Field(
        default=3,
        validation_alias=AliasChoices("MAX_RETRIES", "LLM_MAX_RETRIES"),
        description="Maximum retry attempts on transient LLM errors",
    )
    openai_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_API_KEY", "LLM_API_KEY"),
        description="OpenAI API authentication key",
    )
    anthropic_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
        description="Anthropic API authentication key",
    )
    google_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GOOGLE_API_KEY", "GEMINI_API_KEY"),
        description="Google Gemini API authentication key",
    )
    openai_model_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("OPENAI_MODEL_NAME"),
        description="OpenAI model identifier (e.g. gpt-4o)",
    )
    gemini_model_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("GEMINI_MODEL_NAME"),
        description="Google Gemini model identifier (e.g. gemini-2.5-pro)",
    )
    claude_model_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("CLAUDE_MODEL_NAME"),
        description="Anthropic Claude model identifier (e.g. claude-3-5-sonnet-20240620)",
    )
    bedrock_model_id: Optional[str] = Field(
        default="anthropic.claude-3-5-sonnet-20240620-v1:0",
        validation_alias=AliasChoices("BEDROCK_MODEL_ID", "AWS_BEDROCK_MODEL_ID"),
        description="AWS Bedrock model identifier",
    )
    bedrock_region_name: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("BEDROCK_REGION_NAME", "AWS_REGION", "AWS_DEFAULT_REGION"),
        description="AWS Bedrock region name",
    )

    # -------------------------------------------------------------------------
    # 6. MCP Server Settings
    # -------------------------------------------------------------------------
    mcp_server_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AX_MCP_SERVER_URL", "MCP_SERVER_URL"),
        description="Model Context Protocol (MCP) server endpoint URL",
    )
    mcp_server_api_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("AX_MCP_SERVER_API_KEY", "MCP_SERVER_API_KEY"),
        description="Authentication API key for MCP server",
    )
    mcp_server_name: Optional[str] = Field(
        default="agentforge-mcp",
        validation_alias=AliasChoices("AX_MCP_SERVER_NAME", "MCP_SERVER_NAME"),
        description="Registered identifier for the MCP server",
    )

    # -------------------------------------------------------------------------
    # 7. Langfuse Tracing Settings
    # -------------------------------------------------------------------------
    langfuse_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("LANGFUSE_ENABLED"),
        description="Toggle for Langfuse LLM tracing and observability",
    )
    langfuse_public_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_PUBLIC_KEY"),
        description="Langfuse public API key",
    )
    langfuse_secret_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("LANGFUSE_SECRET_KEY"),
        description="Langfuse secret API key",
    )
    langfuse_base_url: Optional[str] = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("LANGFUSE_BASE_URL", "LANGFUSE_HOST"),
        description="Base URL for Langfuse server",
    )

    # -------------------------------------------------------------------------
    # 8. OpenSearch Settings
    # -------------------------------------------------------------------------
    opensearch_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("OPENSEARCH_URL"),
        description="Full OpenSearch endpoint URL. If omitted, built from components.",
    )
    opensearch_host: str = Field(
        default="localhost",
        validation_alias=AliasChoices("OPENSEARCH_HOST"),
        description="OpenSearch server host or IP",
    )
    opensearch_port: int = Field(
        default=9200,
        validation_alias=AliasChoices("OPENSEARCH_PORT"),
        description="OpenSearch server port",
    )
    opensearch_username: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("OPENSEARCH_USERNAME", "OPENSEARCH_USER"),
        description="OpenSearch authentication username",
    )
    opensearch_password: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("OPENSEARCH_PASSWORD"),
        description="OpenSearch authentication password",
    )
    opensearch_use_ssl: bool = Field(
        default=False,
        validation_alias=AliasChoices("OPENSEARCH_USE_SSL", "OPENSEARCH_SSL"),
        description="Enable SSL/TLS for OpenSearch connection",
    )
    opensearch_verify_certs: bool = Field(
        default=False,
        validation_alias=AliasChoices("OPENSEARCH_VERIFY_CERTS"),
        description="Verify SSL certificates for OpenSearch",
    )
    opensearch_index_prefix: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("OPENSEARCH_INDEX_PREFIX"),
        description="Prefix for OpenSearch indices",
    )

    # -------------------------------------------------------------------------
    # Validators
    # -------------------------------------------------------------------------
    @field_validator("environment", mode="before")
    @classmethod
    def normalize_environment(cls, v: Any) -> str:
        """Normalize common environment aliases to dev, prd, or test."""
        if isinstance(v, str):
            cleaned = v.strip().lower()
            if cleaned in ("development", "local", "dev"):
                return "dev"
            if cleaned in ("production", "prod", "prd"):
                return "prd"
            if cleaned in ("testing", "test"):
                return "test"
            return cleaned
        return "dev"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> List[str]:
        """Support parsing JSON arrays, comma-delimited strings, or lists."""
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return ["*"]
            if v_str.startswith("[") and v_str.endswith("]"):
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [part.strip() for part in v_str.split(",") if part.strip()]
        if isinstance(v, list):
            return [str(item).strip() for item in v if str(item).strip()]
        return ["*"]

    # -------------------------------------------------------------------------
    # Derived Properties
    # -------------------------------------------------------------------------
    @property
    def resolved_database_url(self) -> str:
        """Construct the database URL if not explicitly configured."""
        if self.database_url:
            return self.database_url
        if self.database_driver.startswith("sqlite"):
            return f"{self.database_driver}:///./agentforge.db"
        return (
            f"{self.database_driver}://{self.database_username}:{self.database_password}"
            f"@{self.database_host}:{self.database_port}/{self.database_dbname}"
        )

    @property
    def resolved_redis_url(self) -> str:
        """Construct the Redis URL if not explicitly configured."""
        if self.redis_url:
            return self.redis_url
        scheme = "rediss" if self.redis_ssl else "redis"
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"{scheme}://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def resolved_opensearch_url(self) -> str:
        """Construct the OpenSearch URL if not explicitly configured."""
        if self.opensearch_url and self.opensearch_url.strip():
            return self.opensearch_url.strip().rstrip("/")

        raw_host = (self.opensearch_host or "").strip()
        if not raw_host:
            raw_host = "localhost"

        scheme = "https" if self.opensearch_use_ssl else "http"

        if raw_host.startswith("https://"):
            scheme = "https"
            raw_host = raw_host[8:]
        elif raw_host.startswith("http://"):
            scheme = "http"
            raw_host = raw_host[7:]

        # Strip fragment, query parameters, and trailing path
        raw_host = raw_host.split("#")[0].split("?")[0].split("/")[0]

        # Extract embedded userinfo if present (e.g. user:pass@host)
        extracted_user = None
        extracted_pass = None
        if "@" in raw_host:
            auth_part, host_part = raw_host.rsplit("@", 1)
            raw_host = host_part
            if ":" in auth_part:
                extracted_user, extracted_pass = auth_part.split(":", 1)
            else:
                extracted_user = auth_part

        username = self.opensearch_username if self.opensearch_username is not None else extracted_user
        password = self.opensearch_password if self.opensearch_password is not None else extracted_pass

        # Handle bracketed IPv6, unbracketed IPv6, and hostname:port
        if raw_host.startswith("["):
            if "]:" in raw_host:
                parts = raw_host.split("]:", 1)
                host = parts[0] + "]"
                try:
                    port = int(parts[1])
                except ValueError:
                    port = self.opensearch_port
            else:
                host = raw_host
                port = self.opensearch_port
        elif raw_host.count(":") > 1:
            # Unbracketed IPv6 address: wrap in brackets per RFC 3986
            host = f"[{raw_host}]"
            port = self.opensearch_port
        elif ":" in raw_host:
            parts = raw_host.split(":", 1)
            host = parts[0]
            try:
                port = int(parts[1])
            except ValueError:
                port = self.opensearch_port
        else:
            host = raw_host
            port = self.opensearch_port

        if not host:
            host = "localhost"

        if username and password:
            auth = f"{username}:{password}@"
        elif username:
            auth = f"{username}@"
        elif password:
            auth = f":{password}@"
        else:
            auth = ""

        return f"{scheme}://{auth}{host}:{port}"


@lru_cache()
def get_settings() -> BaseAppSettings:
    """Cached singleton accessor for application settings."""
    return BaseAppSettings()
