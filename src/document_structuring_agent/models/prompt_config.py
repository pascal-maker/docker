from __future__ import annotations

from pydantic import BaseModel


class PromptConfig(BaseModel):
    """Configuration for an LLM prompt fetched from Langfuse."""

    model: str | None = None
    temperature: float | None = None
