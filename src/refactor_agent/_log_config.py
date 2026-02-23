"""Repo-wide logging: structured (JSON) console and optional Sentry for errors.

Call configure_logging() once at app startup (e.g. from __main__ or __init__).
Module-level loggers import get_logger from here via their package logger.py.
"""

from __future__ import annotations

import contextlib
import logging
import os
import sys

import structlog

_CONFIGURED: list[bool] = [False]

_LOG_LEVEL_BY_NAME: dict[str, int] = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}


def configure_logging(
    *,
    level: int | str = logging.INFO,
) -> None:
    """Configure logging: structured JSON to console; errors to Sentry if DSN set.

    Call once at application startup. Safe to call multiple times (idempotent).
    """
    if _CONFIGURED[0]:
        return

    # Optional Sentry: capture error-level logs and exceptions.
    sentry_dsn = os.environ.get("SENTRY_DSN", "").strip()
    if sentry_dsn:
        with contextlib.suppress(Exception):
            import sentry_sdk  # noqa: PLC0415 — lazy optional dep
            from sentry_sdk.integrations.logging import (  # noqa: PLC0415
                LoggingIntegration,
            )

            sentry_sdk.init(
                dsn=sentry_dsn,
                integrations=[
                    LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
                ],
                traces_sample_rate=0.0,
            )

    log_level = (
        level
        if isinstance(level, int)
        else _LOG_LEVEL_BY_NAME.get(str(level).upper(), logging.INFO)
    )

    # Structlog: render to JSON and pass to stdlib. Root handler prints message only.
    structlog.configure(
        cache_logger_on_first_use=True,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stderr,
        level=log_level,
    )

    _CONFIGURED[0] = True


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Return a structured logger for the given name (e.g. refactor_agent.agent)."""
    # structlog.get_logger is generic; we configure BoundLogger at runtime.
    return structlog.get_logger(name)  # type: ignore[no-any-return]
