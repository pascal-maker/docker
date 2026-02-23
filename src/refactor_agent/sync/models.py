"""Pydantic models for sync server WebSocket messages."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SyncFileEntry(BaseModel):
    """Single file in a bootstrap or file message: path and content."""

    path: str = Field(..., min_length=1)
    content: str = ""


class BootstrapMessage(BaseModel):
    """Bootstrap message: optionally clone repo, then write files (delta over clone)."""

    type: Literal["bootstrap"] = "bootstrap"
    files: list[SyncFileEntry]
    repo_url: str | None = Field(
        default=None,
        description="GitHub repo URL for git clone; used with auth token to seed replica",
    )


class FileMessage(BaseModel):
    """Single-file message: write one file to the replica."""

    type: Literal["file"] = "file"
    path: str = Field(..., min_length=1)
    content: str = ""
