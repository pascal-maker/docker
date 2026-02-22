from __future__ import annotations

from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

from langfuse import get_client
from pydantic_ai import Agent

from refactor_agent.models.prompt_config import PromptConfig

if TYPE_CHECKING:
    from collections.abc import Generator


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


def get_prompt_config(name: str) -> PromptConfig:
    """Fetch a prompt's config from Langfuse (model, temperature, etc.)."""
    langfuse = get_client()
    prompt = langfuse.get_prompt(name)
    return PromptConfig.model_validate(prompt.config or {})


@contextmanager
def langfuse_span(
    name: str,
    *,
    as_type: str = "span",
    span_input: Any = None,  # noqa: ANN401 — Langfuse accepts arbitrary JSON
    metadata: dict[str, Any] | None = None,
) -> Generator[_SpanHandle, None, None]:
    """Create a Langfuse observation span; yields a no-op handle if unavailable.

    Exceptions from the body are not thrown into the inner observation context
    manager, to avoid "generator didn't stop after throw()" from Langfuse.
    """
    inner_cm = None
    try:
        client = get_client()
        inner_cm = client.start_as_current_observation(
            name=name,
            as_type=as_type,
            input=span_input,
            metadata=metadata,
        )
        obs = inner_cm.__enter__()
        try:
            yield _SpanHandle(obs)
        finally:
            inner_cm.__exit__(None, None, None)
    except Exception:
        yield _SpanHandle(None)


class _SpanHandle:
    """Thin wrapper around a Langfuse observation; safe to call on a disabled client."""

    def __init__(self, obs: object | None) -> None:
        self._obs = obs

    def update(self, **kwargs: Any) -> None:  # noqa: ANN401 — Langfuse accepts arbitrary JSON
        """Forward keyword arguments to the underlying observation."""
        if self._obs is not None and hasattr(self._obs, "update"):
            self._obs.update(**kwargs)  # type: ignore[union-attr]
