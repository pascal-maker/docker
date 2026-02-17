"""FastAPI application entry point."""

# load_dotenv must run before any document_structuring_agent import so that
# env vars (ANTHROPIC_API_KEY, LANGFUSE_*) are set before _compat patches fire
# and before Langfuse initialises.
# ruff: noqa: E402
from __future__ import annotations

from dotenv import load_dotenv

load_dotenv()

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router

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
