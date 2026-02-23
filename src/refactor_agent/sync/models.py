"""Pydantic models for sync server WebSocket messages."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SyncFileEntry(BaseModel):
    """Single file in a bootstrap or file message: path and content."""

    path: str = Field(..., min_length=1)
    content: str = ""


class BootstrapMessage(BaseModel):
    """Bootstrap message: wipe replica and write all files."""

    type: Literal["bootstrap"] = "bootstrap"
    files: list[SyncFileEntry]


class FileMessage(BaseModel):
    """Single-file message: write one file to the replica."""

    type: Literal["file"] = "file"
    path: str = Field(..., min_length=1)
    content: str = ""
