"""FastAPI application entry point."""

# load_dotenv must run before any document_structuring_agent import so that
# env vars (ANTHROPIC_API_KEY, LANGFUSE_*) are set before _compat patches fire
# and before Langfuse initialises.
# ruff: noqa: E402
from __future__ import annotations

import logging

from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router


# Configure logging to show structured events from background tasks
class StructuredFormatter(logging.Formatter):
    """Formatter that includes extra fields from structured logs."""

    def format(self, record: logging.LogRecord) -> str:
        # Get the base message
        msg = record.getMessage()

        # Append extra fields if present (exclude internal logging fields)
        if hasattr(record, "__dict__"):
            extras = {
                k: v
                for k, v in record.__dict__.items()
                if k
                not in {
                    "name",
                    "msg",
                    "args",
                    "created",
                    "filename",
                    "funcName",
                    "levelname",
                    "levelno",
                    "lineno",
                    "module",
                    "msecs",
                    "message",
                    "pathname",
                    "process",
                    "processName",
                    "relativeCreated",
                    "thread",
                    "threadName",
                    "exc_info",
                    "exc_text",
                    "stack_info",
                    "taskName",  # asyncio internal
                }
            }
            if extras:
                extras_str = " ".join(f"{k}={v}" for k, v in extras.items())
                msg = f"{msg} {extras_str}"

        return f"{record.levelname}:     {msg}"


handler = logging.StreamHandler()
handler.setFormatter(StructuredFormatter())
logging.root.handlers = [handler]
logging.root.setLevel(logging.INFO)

# Ensure our module logger is visible
logging.getLogger("document_structuring_agent").setLevel(logging.INFO)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan — nothing to set up beyond dotenv (done at module level)."""
    yield


app = FastAPI(title="Document Structuring Agent API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(router)
