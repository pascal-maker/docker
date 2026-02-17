from __future__ import annotations

from langfuse import get_client
from pydantic_ai import Agent


def init_langfuse() -> None:
    """Initialize Langfuse tracing for all PydanticAI agents.

    Call once at application startup. Reads LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY, and LANGFUSE_BASE_URL from the environment.
    """
    Agent.instrument_all()


def get_prompt(name: str, **variables: str) -> str:
    """Fetch a prompt from the Langfuse registry and compile it with variables."""
    langfuse = get_client()
    prompt = langfuse.get_prompt(name)
    return prompt.compile(**variables)


def get_prompt_config(name: str) -> dict:
    """Fetch a prompt's config from Langfuse (model, temperature, etc.)."""
    langfuse = get_client()
    prompt = langfuse.get_prompt(name)
    return prompt.config or {}
