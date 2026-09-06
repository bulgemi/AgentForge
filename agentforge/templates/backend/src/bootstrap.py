"""Application composition root and lifespan manager."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import SQLModel

from .core.config import get_settings
from .core.database import db
from .core.logging import setup_logger
from .infrastructure.auth.auth_config import get_auth_config
from .infrastructure.auth.auth_runtime import build_auth_runtime
from .infrastructure.rest.routes import get_all_routers

logger = setup_logger("agentforge.backend")


def create_agent_app(agent_adapter: Any = None) -> FastAPI:
    """Compose and build production FastAPI application with Clean Architecture."""
    settings = get_settings()
    auth_config = get_auth_config()

    @asynccontextmanager
    async def app_lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logger.info("Starting up AgentForge backend application...")
        # 1. Initialize Database tables
        try:
            async with db.engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            logger.info("Database schema initialized successfully.")
        except Exception as e:
            logger.warning("Auto-migration skipped or failed: %s", e)

        # 2. Initialize Authentication Runtime
        runtime = await build_auth_runtime(auth_config)
        app.state.auth_runtime = runtime
        if agent_adapter:
            app.state.agent_adapter = agent_adapter
        logger.info("AuthRuntime bound to application state.")

        try:
            yield
        finally:
            logger.info("Shutting down AgentForge backend application...")
            await runtime.close()
            await db.dispose()

    app = FastAPI(
        title="{{ project_name }} API",
        version="0.1.0",
        description="Standalone AI Agent Service with Authentication & SSE Streaming",
        lifespan=app_lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=auth_config.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Healthcheck endpoints
    @app.get("/healthz", tags=["System"])
    @app.get("/health", tags=["System"])
    async def healthcheck() -> dict[str, str]:
        return {"status": "ok", "service": "{{ project_name }}"}

    # Register all modular routes
    for router in get_all_routers():
        app.include_router(router)

    return app
