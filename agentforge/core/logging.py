"""AgentForge Core Runtime Logging Module.

Provides structured JSON logging with context-safe correlation ID propagation.
Designed for standalone zero-dependency execution.
"""

from __future__ import annotations

import contextvars
from datetime import datetime, timezone
import json
import logging
import sys
import traceback
from typing import Any, Optional

# Context-safe variable for correlation ID propagation across async tasks
correlation_id_ctx: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)

# Standard LogRecord attributes to exclude when gathering custom 'extra' fields
_STANDARD_LOG_RECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "correlation_id", "asctime",
}


def get_correlation_id() -> Optional[str]:
    """Retrieve the current correlation ID from the execution context.

    Returns:
        Optional[str]: Active correlation ID, or None if not set.
    """
    return correlation_id_ctx.get()


def set_correlation_id(correlation_id: Optional[str]) -> contextvars.Token:
    """Set the correlation ID for the current execution context.

    Args:
        correlation_id: The correlation ID string to associate with this context.

    Returns:
        contextvars.Token: Token to restore previous context state.
    """
    return correlation_id_ctx.set(correlation_id)


def reset_correlation_id(token: contextvars.Token) -> None:
    """Reset the correlation ID back to the state before set_correlation_id was called.

    Args:
        token: The token returned by set_correlation_id.
    """
    correlation_id_ctx.reset(token)


class CorrelationIdFilter(logging.Filter):
    """Logging filter that enriches records with the context correlation ID."""

    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "correlation_id") or record.correlation_id is None:
            record.correlation_id = get_correlation_id()
        return True


class JsonFormatter(logging.Formatter):
    """Structured JSON log formatter.

    Outputs single-line JSON strings conforming to enterprise observability standards.
    Handles non-serializable objects and exceptions safely.
    """

    def format(self, record: logging.LogRecord) -> str:
        # Compute ISO8601 UTC timestamp with 'Z' suffix
        created_dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        timestamp_str = created_dt.isoformat().replace("+00:00", "Z")

        # Resolve correlation_id
        corr_id = getattr(record, "correlation_id", None) or get_correlation_id()

        # Handle exception information
        exception_text = None
        if record.exc_info:
            exception_text = self.formatException(record.exc_info)
        elif record.exc_text:
            exception_text = record.exc_text

        # Base structured payload
        payload: dict[str, Any] = {
            "timestamp": timestamp_str,
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "correlation_id": corr_id,
            "path": record.pathname,
            "line": record.lineno,
            "exception": exception_text,
        }

        # Extract extra fields attached to the LogRecord
        extra_fields: dict[str, Any] = {}
        for key, value in record.__dict__.items():
            if key not in _STANDARD_LOG_RECORD_ATTRS and not key.startswith("_"):
                extra_fields[key] = value

        if extra_fields:
            payload["extra"] = extra_fields

        # Fail-safe JSON serialization
        return json.dumps(payload, default=str, ensure_ascii=False)


def setup_logger(
    name: str,
    level: str | int = "INFO",
    json_format: bool = True,
) -> logging.Logger:
    """Configure and return a standardized logger.

    Args:
        name: Logger name (typically __name__ or module path).
        level: Logging level as a string ("DEBUG", "INFO", "WARNING", "ERROR") or int.
        json_format: True for single-line JSON formatting, False for human-readable text.

    Returns:
        logging.Logger: Configured logger instance.
    """
    logger = logging.getLogger(name)

    # Convert string level to integer if necessary
    if isinstance(level, str):
        numeric_level = getattr(logging, level.upper(), logging.INFO)
    else:
        numeric_level = level

    logger.setLevel(numeric_level)
    logger.propagate = False

    # Idempotent handler setup: clear existing handlers to avoid duplicates
    if logger.handlers:
        for handler in tuple(logger.handlers):
            logger.removeHandler(handler)
            try:
                handler.close()
            except Exception:
                pass

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(numeric_level)
    stream_handler.addFilter(CorrelationIdFilter())

    if json_format:
        stream_handler.setFormatter(JsonFormatter())
    else:
        text_fmt = "%(asctime)s [%(levelname)s] [%(name)s] [%(correlation_id)s] %(message)s"
        stream_handler.setFormatter(logging.Formatter(text_fmt))

    logger.addHandler(stream_handler)
    return logger
