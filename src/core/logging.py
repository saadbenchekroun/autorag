"""Structured logging factory for AutoRAG Architect.

Usage::

    from src.core.logging import get_logger
    logger = get_logger(__name__)
    logger.info("indexing_started", project_id=project_id, chunks=n)
"""

import logging
import os
import sys
from typing import Any


def get_logger(name: str) -> "BoundLogger":
    """Return a logger bound to *name* that emits structured key=value lines."""
    return BoundLogger(logging.getLogger(name))


class BoundLogger:
    """Thin wrapper that adds key=value structured context to log messages."""

    def __init__(self, logger: logging.Logger) -> None:
        self._logger = logger

    def _format(self, event: str, **kwargs: Any) -> str:
        parts = [event]
        for k, v in kwargs.items():
            parts.append(f"{k}={v!r}")
        return " ".join(parts)

    def debug(self, event: str, **kwargs: Any) -> None:
        if self._logger.isEnabledFor(logging.DEBUG):
            self._logger.debug(self._format(event, **kwargs))

    def info(self, event: str, **kwargs: Any) -> None:
        self._logger.info(self._format(event, **kwargs))

    def warning(self, event: str, **kwargs: Any) -> None:
        self._logger.warning(self._format(event, **kwargs))

    def error(self, event: str, **kwargs: Any) -> None:
        self._logger.error(self._format(event, **kwargs))

    def exception(self, event: str, **kwargs: Any) -> None:
        self._logger.exception(self._format(event, **kwargs))


def configure_logging() -> None:
    """Configure the root logger once at application startup."""
    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        stream=sys.stdout,
        level=getattr(logging, log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    # Silence noisy third-party loggers
    for noisy in ("httpx", "httpcore", "chromadb", "sentence_transformers"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
