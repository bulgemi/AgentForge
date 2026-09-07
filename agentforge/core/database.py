"""Database module for AgentForge Core Runtime.

Provides thread-safe singleton connection management, multi-dialect support
(PostgreSQL, SQLite), connection pooling, session lifecycle context managers,
health check ping/aping, and generic pagination helpers.
"""

from __future__ import annotations

import asyncio
from contextlib import AbstractAsyncContextManager, AbstractContextManager
import json
import logging
import os
import re
import threading
import urllib.parse
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Generator,
    Generic,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
)

from pydantic import BaseModel, ConfigDict, Field, field_validator
import sqlalchemy
from sqlalchemy import func, select, text
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession as SQLAlchemyAsyncSession,
    async_scoped_session,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session as SQLAlchemySession, scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel.main import FieldInfo as sqlmodel_FieldInfo

logger = logging.getLogger("agentforge.core.database")

__all__ = [
    "Database",
    "DBClient",
    "db",
    "DatabaseError",
    "DatabaseConnectionError",
    "DatabasePoolTimeoutError",
    "ConnectorError",
    "DualSyncSessionContext",
    "DualAsyncSessionContext",
    "get_session",
    "get_async_session",
    "PageMetadata",
    "Page",
    "PageableParams",
    "apply_pageable_params",
    "paginate",
    "apaginate",
    "get_pk_list",
    "get_pk_values",
]


# ============================================================================
# Exceptions
# ============================================================================

class DatabaseError(Exception):
    """Base exception for all AgentForge database operations."""
    pass


class DatabaseConnectionError(DatabaseError):
    """Raised when database connection or health check fails."""
    pass


class DatabasePoolTimeoutError(DatabaseError):
    """Raised when database connection pool times out during checkout."""
    pass


# Backward compatibility alias
ConnectorError = DatabaseError


# ============================================================================
# Helpers & Serializers
# ============================================================================

def _json_serializer(value: Any) -> str:
    """JSON serializer ensuring Unicode characters (e.g. Korean, CJK) are not escaped."""
    return json.dumps(value, ensure_ascii=False, default=str)


def _normalize_url(url: str, is_async: bool) -> str:
    """Normalizes database URLs to match required driver for sync/async execution."""
    if not url:
        return url
    if is_async:
        if url.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql+psycopg2://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            return url.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif url.startswith("sqlite://") and not url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite://", "sqlite+aiosqlite://", 1)
    else:
        if url.startswith("postgresql+asyncpg://"):
            return url.replace("postgresql+asyncpg://", "postgresql+psycopg2://", 1)
        elif url.startswith("sqlite+aiosqlite://"):
            return url.replace("sqlite+aiosqlite://", "sqlite://", 1)
        elif url.startswith("postgresql://") and not url.startswith("postgresql+psycopg2://"):
            return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


# ============================================================================
# Dual Session Context Managers (Context Manager + Generator)
# ============================================================================

class DualSyncSessionContext(AbstractContextManager):
    """Dual session context supporting both 'with' context manager and generator iteration."""

    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory
        self._session: Optional[Session] = None

    def __enter__(self) -> Session:
        self._session = self._session_factory()
        return self._session

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if self._session is None:
            return False
        try:
            if exc_type is not None:
                self._session.rollback()
            else:
                self._session.commit()
        finally:
            self._session.close()
        return False

    def __iter__(self) -> Generator[Session, None, None]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()


class DualAsyncSessionContext(AbstractAsyncContextManager):
    """Dual async session context supporting both 'async with' context manager and async generator iteration."""

    def __init__(self, session_factory: Callable[[], AsyncSession]):
        self._session_factory = session_factory
        self._session: Optional[AsyncSession] = None

    async def __aenter__(self) -> AsyncSession:
        self._session = self._session_factory()
        return self._session

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> bool:
        if self._session is None:
            return False
        try:
            if exc_type is not None:
                await self._session.rollback()
            else:
                await self._session.commit()
        finally:
            await self._session.close()
        return False

    async def __aiter__(self) -> AsyncGenerator[AsyncSession, None]:
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ============================================================================
# Database Singleton
# ============================================================================

class Database:
    """Thread-safe Database connection and session manager singleton.

    Manages sync/async SQLAlchemy engines, session factories, connection pools,
    health checks, and transaction lifecycles.
    """

    _instance: Optional["Database"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "Database":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        url: Optional[str] = None,
        settings: Optional[Any] = None,
        pool_size: Optional[int] = None,
        max_overflow: Optional[int] = None,
        pool_timeout: Optional[int] = None,
        pool_recycle: Optional[int] = None,
        pool_pre_ping: Optional[bool] = None,
        schema: Optional[str] = None,
    ) -> None:
        if getattr(self, "_initialized", False):
            if url is not None:
                self._configured_url = url
            if settings is not None:
                self._settings = settings
            return

        with self._lock:
            if getattr(self, "_initialized", False):
                return

            self._settings = settings
            self._configured_url = url or os.getenv("DATABASE_URL")
            self._schema = schema or os.getenv("DATABASE_SCHEMA")

            # Pool configuration
            self._pool_size = pool_size or int(os.getenv("DATABASE_POOL_SIZE", "10"))
            self._max_overflow = max_overflow or int(os.getenv("DATABASE_MAX_OVERFLOW", "20"))
            self._pool_timeout = pool_timeout or int(os.getenv("DATABASE_POOL_TIMEOUT", "30"))
            self._pool_recycle = pool_recycle or int(os.getenv("DATABASE_POOL_RECYCLE", "1800"))
            self._pool_pre_ping = (
                pool_pre_ping
                if pool_pre_ping is not None
                else os.getenv("DATABASE_POOL_PRE_PING", "true").lower() in ("true", "1", "yes")
            )

            # Cached engines & factories
            self._sync_engine: Optional[Engine] = None
            self._async_engine: Optional[AsyncEngine] = None
            self._sync_session_factory: Optional[sessionmaker] = None
            self._async_session_factory: Optional[async_sessionmaker] = None
            self._async_scoped_session: Optional[async_scoped_session] = None

            # Re-entrant initialization lock
            self._init_lock = threading.RLock()
            self._initialized = True

    @classmethod
    def reset(cls) -> None:
        """Resets the singleton instance and disposes all active engines. Useful for testing."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None

    @property
    def metadata(self) -> sqlalchemy.MetaData:
        """Returns the shared SQLModel metadata."""
        return SQLModel.metadata

    @property
    def sync_engine(self) -> Engine:
        """Returns the default sync Engine, initializing lazily if not created."""
        if self._sync_engine is None:
            self.init_sync_engine()
        return self._sync_engine

    @property
    def async_engine(self) -> AsyncEngine:
        """Returns the default async AsyncEngine, initializing lazily if not created."""
        if self._async_engine is None:
            self.init_async_engine()
        return self._async_engine

    @property
    def engine(self) -> Engine:
        """Alias for sync_engine (backward compatibility with pay)."""
        return self.sync_engine

    def _resolve_url(self, is_async: bool) -> str:
        """Resolves the database URL from config, settings, or fallback defaults."""
        raw_url = self._configured_url
        if not raw_url and self._settings is not None:
            raw_url = getattr(self._settings, "database_url", None)
            if not raw_url and hasattr(self._settings, "database_host"):
                user = urllib.parse.quote_plus(getattr(self._settings, "database_username", "postgres"))
                password = urllib.parse.quote_plus(getattr(self._settings, "database_password", "postgres"))
                host = getattr(self._settings, "database_host", "localhost")
                port = getattr(self._settings, "database_port", 5432)
                dbname = getattr(self._settings, "database_dbname", "agentforge")
                driver = getattr(self._settings, "database_driver", "postgresql")
                raw_url = f"{driver}://{user}:{password}@{host}:{port}/{dbname}"

        if not raw_url:
            raw_url = "sqlite:///agentforge.db"

        return _normalize_url(raw_url, is_async=is_async)

    def _build_connect_args(self, url: str, is_async: bool) -> Dict[str, Any]:
        """Builds dialect-specific connection arguments."""
        connect_args: Dict[str, Any] = {}
        if "sqlite" in url:
            connect_args["check_same_thread"] = False
        elif "postgresql" in url and self._schema:
            if is_async:
                connect_args["server_settings"] = {"search_path": self._schema}
            else:
                connect_args["options"] = f"-csearch_path={self._schema}"
        return connect_args

    def _build_pool_kwargs(self, url: str) -> Dict[str, Any]:
        """Builds dialect-appropriate connection pool parameters."""
        is_sqlite = "sqlite" in url
        is_memory = ":memory:" in url

        kwargs: Dict[str, Any] = {
            "pool_pre_ping": self._pool_pre_ping,
        }

        if is_sqlite and is_memory:
            kwargs["poolclass"] = StaticPool
            return kwargs

        if is_sqlite:
            if self._pool_recycle:
                kwargs["pool_recycle"] = self._pool_recycle
            return kwargs

        kwargs.update({
            "pool_size": self._pool_size,
            "max_overflow": self._max_overflow,
            "pool_timeout": self._pool_timeout,
            "pool_recycle": self._pool_recycle,
        })
        return kwargs

    def init_sync_engine(self, url: Optional[str] = None, **kwargs: Any) -> Engine:
        """Initializes the synchronous SQLAlchemy Engine and sessionmaker.

        Uses double-checked locking for thread safety.
        """
        if self._sync_engine is None or url is not None:
            with self._init_lock:
                if self._sync_engine is None or url is not None:
                    target_url = _normalize_url(url, is_async=False) if url else self._resolve_url(is_async=False)
                    pool_kwargs = self._build_pool_kwargs(target_url)
                    connect_args = self._build_connect_args(target_url, is_async=False)
                    pool_kwargs.update(kwargs)

                    self._sync_engine = create_engine(
                        target_url,
                        connect_args=connect_args,
                        json_serializer=_json_serializer,
                        **pool_kwargs,
                    )
                    self._sync_session_factory = sessionmaker(
                        bind=self._sync_engine,
                        autocommit=False,
                        autoflush=False,
                        expire_on_commit=False,
                        class_=Session,
                    )
                    logger.info("Initialized sync database engine: %s", self._sync_engine.url)
        return self._sync_engine

    def init_async_engine(self, url: Optional[str] = None, **kwargs: Any) -> AsyncEngine:
        """Initializes the asynchronous SQLAlchemy AsyncEngine and async_sessionmaker.

        Uses double-checked locking for thread safety.
        """
        if self._async_engine is None or url is not None:
            with self._init_lock:
                if self._async_engine is None or url is not None:
                    target_url = _normalize_url(url, is_async=True) if url else self._resolve_url(is_async=True)
                    pool_kwargs = self._build_pool_kwargs(target_url)
                    connect_args = self._build_connect_args(target_url, is_async=True)
                    pool_kwargs.update(kwargs)

                    self._async_engine = create_async_engine(
                        target_url,
                        connect_args=connect_args,
                        json_serializer=_json_serializer,
                        **pool_kwargs,
                    )
                    self._async_session_factory = async_sessionmaker(
                        bind=self._async_engine,
                        autocommit=False,
                        autoflush=False,
                        expire_on_commit=False,
                        class_=AsyncSession,
                    )
                    self._async_scoped_session = async_scoped_session(
                        session_factory=self._async_session_factory,
                        scopefunc=asyncio.current_task,
                    )
                    logger.info("Initialized async database engine: %s", self._async_engine.url)
        return self._async_engine

    def get_sync_session(self) -> DualSyncSessionContext:
        """Provides a sync database session supporting context manager ('with') and generator iteration."""
        if self._sync_session_factory is None:
            self.init_sync_engine()
        return DualSyncSessionContext(self._sync_session_factory)

    def get_async_session(self) -> DualAsyncSessionContext:
        """Provides an async database session supporting async context manager ('async with') and async generator iteration."""
        if self._async_session_factory is None:
            self.init_async_engine()
        return DualAsyncSessionContext(self._async_session_factory)

    def ping(self) -> bool:
        """Synchronous health check executing SELECT 1;. Returns True if database responds, False otherwise."""
        try:
            with self.sync_engine.connect() as conn:
                conn.execute(text("SELECT 1;"))
            return True
        except Exception as exc:
            logger.warning("Sync database health ping failed: %s", exc)
            return False

    async def aping(self) -> bool:
        """Asynchronous health check executing SELECT 1;. Returns True if database responds, False otherwise."""
        try:
            async with self.async_engine.connect() as conn:
                await conn.execute(text("SELECT 1;"))
            return True
        except Exception as exc:
            logger.warning("Async database health ping failed: %s", exc)
            return False

    def create_database(self) -> None:
        """Creates all tables defined in SQLModel metadata."""
        self.metadata.create_all(self.sync_engine)

    def create_all(self) -> None:
        """Alias for create_database."""
        self.create_database()

    def close(self) -> None:
        """Disposes sync and async engines synchronously."""
        with self._init_lock:
            if self._sync_engine is not None:
                self._sync_engine.dispose()
                self._sync_engine = None
                self._sync_session_factory = None
            if self._async_engine is not None:
                try:
                    loop = asyncio.get_running_loop()
                    if loop.is_running():
                        loop.create_task(self._async_engine.dispose())
                    else:
                        asyncio.run(self._async_engine.dispose())
                except RuntimeError:
                    try:
                        asyncio.run(self._async_engine.dispose())
                    except Exception:
                        pass
                self._async_engine = None
                self._async_session_factory = None
                self._async_scoped_session = None

    async def aclose(self) -> None:
        """Disposes sync and async engines asynchronously."""
        with self._init_lock:
            if self._async_engine is not None:
                await self._async_engine.dispose()
                self._async_engine = None
                self._async_session_factory = None
                self._async_scoped_session = None
            if self._sync_engine is not None:
                self._sync_engine.dispose()
                self._sync_engine = None
                self._sync_session_factory = None

    async def dispose(self) -> None:
        """Alias for aclose() for async engine disposal compatibility."""
        await self.aclose()

    async def adispose(self) -> None:
        """Alias for aclose() for async engine disposal compatibility."""
        await self.aclose()


# Module-level singleton
db = Database()
DBClient = Database


# ============================================================================
# FastAPI Dependency Session Providers
# ============================================================================

def get_session() -> Generator[Session, None, None]:
    """FastAPI dependency for sync database session."""
    for session in db.get_sync_session():
        yield session


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for async database session."""
    async for session in db.get_async_session():
        yield session


# ============================================================================
# Metadata and PK Helpers
# ============================================================================

def get_pk_list(table_or_record: Any) -> List[str]:
    """Returns the primary key field names of a SQLModel table or model instance."""
    if hasattr(table_or_record, "model_fields"):
        return [
            name
            for name, prop in table_or_record.model_fields.items()
            if isinstance(prop, sqlmodel_FieldInfo) and prop.primary_key
        ]
    return []


def get_pk_values(record: Any) -> List[Any]:
    """Returns the primary key values of a SQLModel model instance."""
    return [getattr(record, pk) for pk in get_pk_list(record)]


# ============================================================================
# Pagination Models & Engine
# ============================================================================

class PageMetadata(BaseModel):
    """Metadata describing a paginated result set."""

    number: int = Field(..., alias="page", description="Current 1-indexed page number")
    size: int = Field(..., description="Number of elements per page")
    total_elements: int = Field(..., alias="totalElements", description="Total elements across all pages")
    total_pages: int = Field(..., alias="totalPages", description="Total pages")
    has_next: bool = Field(default=False, description="Whether there is a subsequent page")
    has_previous: bool = Field(default=False, description="Whether there is a preceding page")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    def __init__(
        self,
        number: Optional[int] = None,
        size: Optional[int] = None,
        total_elements: Optional[int] = None,
        total_pages: Optional[int] = None,
        has_next: Optional[bool] = None,
        has_previous: Optional[bool] = None,
        **data: Any,
    ):
        """Initializes PageMetadata supporting positional arguments, keyword arguments, and aliases."""
        if number is not None:
            data.setdefault("number", number)
        if size is not None:
            data.setdefault("size", size)
        if total_elements is not None:
            data.setdefault("total_elements", total_elements)
        if total_pages is not None:
            data.setdefault("total_pages", total_pages)
        if has_next is not None:
            data.setdefault("has_next", has_next)
        if has_previous is not None:
            data.setdefault("has_previous", has_previous)
        super().__init__(**data)

    @property
    def page(self) -> int:
        """1-indexed page number alias conforming to PROJECT.md."""
        return self.number

    @property
    def totalElements(self) -> int:
        """CamelCase alias for total_elements."""
        return self.total_elements

    @property
    def totalPages(self) -> int:
        """CamelCase alias for total_pages."""
        return self.total_pages

    @classmethod
    def create(
        cls,
        number: Optional[int] = None,
        size: int = 10,
        total_elements: int = 0,
        *,
        page: Optional[int] = None,
    ) -> "PageMetadata":
        """Factory method to construct PageMetadata with auto-calculated total_pages, has_next, and has_previous."""
        actual_page = page if page is not None else (number if number is not None else 1)
        safe_elements = max(0, total_elements)
        total_pages = (safe_elements + size - 1) // size if size > 0 and safe_elements > 0 else 0
        return cls(
            number=actual_page,
            size=size,
            total_elements=safe_elements,
            total_pages=total_pages,
            has_next=actual_page < total_pages,
            has_previous=actual_page > 1,
        )


T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """Generic container for paginated query results."""

    items: List[T] = Field(default_factory=list, alias="content", description="List of items on this page")
    metadata: PageMetadata = Field(..., alias="pageMetadata", description="Pagination metadata")

    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    @property
    def content(self) -> List[T]:
        """Backward compatibility alias for items."""
        return self.items

    @property
    def pageMetadata(self) -> PageMetadata:
        """Backward compatibility alias for metadata."""
        return self.metadata


class PageableParams(BaseModel):
    """Query parameters for pagination and sorting."""

    page: int = Field(default=1, ge=1, description="1-indexed page number")
    size: int = Field(default=10, ge=1, le=100, description="Page size (max 100)")
    sort_by: Optional[str] = Field(default=None, description="Field name to sort by")
    sort_direction: Literal["asc", "desc"] = Field(default="asc", description="Sort direction ('asc' or 'desc')")

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("sort_by")
    @classmethod
    def validate_sort_by(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            if not re.match(r"^[a-zA-Z0-9_.]+$", v):
                raise ValueError(f"Invalid sort_by field: '{v}'. Must contain only alphanumeric characters, underscores, or dots.")
        return v


def apply_pageable_params(query: Any, params: PageableParams) -> Any:
    """Applies sorting, offset, and limit to a SQLAlchemy / SQLModel select query."""
    if params.sort_by:
        sort_expr = text(f"{params.sort_by} {params.sort_direction}")
        query = query.order_by(sort_expr)

    offset = (params.page - 1) * params.size
    limit = params.size
    return query.offset(offset).limit(limit)


def paginate(session: Any, query: Any, params: PageableParams) -> Any:
    """Paginates a query.

    Supports synchronous Session (returns Page[T] directly) and asynchronous
    AsyncSession (returns an awaitable coroutine yielding Page[T]).
    """
    is_async = (
        isinstance(session, (AsyncSession, SQLAlchemyAsyncSession))
        or hasattr(session, "run_sync")
    )

    if is_async:
        return apaginate(session, query, params)

    # Synchronous pagination
    count_subquery = query.order_by(None).subquery()
    count_query = select(func.count()).select_from(count_subquery)

    if hasattr(session, "exec"):
        count_res = session.exec(count_query)
        total_elements = count_res.one() if hasattr(count_res, "one") else count_res.scalar_one()
    else:
        total_elements = session.execute(count_query).scalar_one()

    if hasattr(total_elements, "__getitem__"):
        try:
            total_elements = total_elements[0]
        except Exception:
            pass

    paginated_query = apply_pageable_params(query, params)

    if hasattr(session, "exec"):
        items_res = session.exec(paginated_query)
        items = list(items_res.all() if hasattr(items_res, "all") else items_res)
    else:
        items = list(session.execute(paginated_query).scalars().all())

    metadata = PageMetadata.create(
        number=params.page,
        size=params.size,
        total_elements=int(total_elements),
    )
    return Page(items=items, metadata=metadata)


async def apaginate(session: Any, query: Any, params: PageableParams) -> Page[Any]:
    """Asynchronously paginates a query using an AsyncSession."""
    count_subquery = query.order_by(None).subquery()
    count_query = select(func.count()).select_from(count_subquery)

    if hasattr(session, "exec"):
        count_res = await session.exec(count_query)
        total_elements = count_res.one() if hasattr(count_res, "one") else count_res.scalar_one()
    else:
        raw_res = await session.execute(count_query)
        total_elements = raw_res.scalar_one()

    if hasattr(total_elements, "__getitem__"):
        try:
            total_elements = total_elements[0]
        except Exception:
            pass

    paginated_query = apply_pageable_params(query, params)

    if hasattr(session, "exec"):
        items_res = await session.exec(paginated_query)
        items = list(items_res.all() if hasattr(items_res, "all") else items_res)
    else:
        raw_items_res = await session.execute(paginated_query)
        items = list(raw_items_res.scalars().all())

    metadata = PageMetadata.create(
        number=params.page,
        size=params.size,
        total_elements=int(total_elements),
    )
    return Page(items=items, metadata=metadata)
