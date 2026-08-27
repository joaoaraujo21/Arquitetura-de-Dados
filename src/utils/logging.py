"""Structured logging configuration using structlog."""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from pythonjsonlogger import jsonlogger

from src.settings import settings


def configure_logging() -> structlog.BoundLogger:
    """Configure structured logging.

    Returns:
        Configured structlog logger instance.
    """
    _configure_stdlib_logging()
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecodeFormatter(),
            structlog.processors.JSONRenderer()
            if settings.log_json
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    return structlog.get_logger()


def _configure_stdlib_logging() -> None:
    """Configure standard library logging for libraries."""
    level = getattr(logging, settings.log_level.upper(), logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s %(filename)s %(lineno)d"
        )
    )
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level)


logger = configure_logging()


def get_logger(name: str | None = None) -> structlog.BoundLogger:
    """Get a logger instance by name.

    Args:
        name: Optional logger name (typically __name__).

    Returns:
        Configured structlog BoundLogger instance.
    """
    return structlog.get_logger(name or "openrouteraula")