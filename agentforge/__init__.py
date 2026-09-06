"""AgentForge: Enterprise AI Agent Framework & Standalone Monorepo Scaffolding Engine."""

__version__ = "0.1.0"

from .core import (
    AgentChunk,
    AgentEventType,
    AgentInput,
    AgentMessage,
    AgentOutput,
    AgentRole,
    BaseAgentAdapter,
    BaseAppSettings,
    Database,
    JsonFormatter,
    Page,
    PageMetadata,
    PageableParams,
    RuntimeContext,
    SSETokenStreamer,
    get_adapter,
    get_settings,
    setup_logger,
)

__all__ = [
    "__version__",
    "BaseAgentAdapter",
    "AgentChunk",
    "AgentEventType",
    "AgentRole",
    "AgentMessage",
    "AgentInput",
    "AgentOutput",
    "SSETokenStreamer",
    "RuntimeContext",
    "Database",
    "Page",
    "PageMetadata",
    "PageableParams",
    "setup_logger",
    "JsonFormatter",
    "BaseAppSettings",
    "get_settings",
    "get_adapter",
    "ScaffoldingEngine",
    "copy_core_engine",
    "cli_app",
]

from .generator import ScaffoldingEngine, copy_core_engine
from .cli import app as cli_app
