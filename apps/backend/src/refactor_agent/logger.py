"""Root package logger. Prefer per-package loggers (e.g. refactor_agent.agent)."""

from refactor_agent._log_config import get_logger

logger = get_logger("refactor_agent")
