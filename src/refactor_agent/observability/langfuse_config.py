from __future__ import annotations

from typing import Any

from langfuse import get_client
from pydantic_ai import Agent

from refactor_agent.models.prompt_config import PromptConfig


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


def get_prompt_name_and_version(name: str) -> tuple[str, str | int | None]:
    """Fetch prompt name and version from Langfuse for linked generation metadata.

    Returns (name, version). Version may be None if not available.
    """
    try:
        langfuse = get_client()
        prompt = langfuse.get_prompt(name)
        pname = getattr(prompt, "name", name)
        pversion = getattr(prompt, "version", None)
        return (str(pname), pversion)
    except Exception:
        return (name, None)


class _LangfuseSpanContext:
    """Class-based context manager so no generator is used; avoids throw() bugs."""

    def __init__(
        self,
        name: str,
        *,
        as_type: str = "span",
        span_input: Any = None,  # noqa: ANN401
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._name = name
        self._as_type = as_type
        self._span_input = span_input
        self._metadata = metadata
        self._inner_cm = None
        self._handle: _SpanHandle = _SpanHandle(None)

    def __enter__(self) -> _SpanHandle:
        try:
            client = get_client()
            self._inner_cm = client.start_as_current_observation(
                name=self._name,
                as_type=self._as_type,
                input=self._span_input,
                metadata=self._metadata,
            )
            obs = self._inner_cm.__enter__()
            self._handle = _SpanHandle(obs)
        except Exception:
            self._handle = _SpanHandle(None)
        return self._handle

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        if self._inner_cm is not None:
            try:
                self._inner_cm.__exit__(exc_type, exc_val, exc_tb)
            except Exception:
                pass
        return None


def langfuse_span(
    name: str,
    *,
    as_type: str = "span",
    span_input: Any = None,  # noqa: ANN401 — Langfuse accepts arbitrary JSON
    metadata: dict[str, Any] | None = None,
) -> _LangfuseSpanContext:
    """Create a Langfuse observation span; yields a no-op handle if unavailable.

    Class-based (no generator) so exceptions from the with-block are passed
    to Langfuse's __exit__ normally, avoiding "generator didn't stop after throw()".
    """
    return _LangfuseSpanContext(
        name,
        as_type=as_type,
        span_input=span_input,
        metadata=metadata,
    )


class _SpanHandle:
    """Thin wrapper around a Langfuse observation; safe to call on a disabled client."""

    def __init__(self, obs: object | None) -> None:
        self._obs = obs

    def update(self, **kwargs: Any) -> None:  # noqa: ANN401 — Langfuse accepts arbitrary JSON
        """Forward keyword arguments to the underlying observation."""
        if self._obs is not None and hasattr(self._obs, "update"):
            self._obs.update(**kwargs)  # type: ignore[union-attr]
