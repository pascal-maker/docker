from __future__ import annotations

import contextlib
import os
import re
from pathlib import Path

from langfuse import get_client
from pydantic import BaseModel, ConfigDict
from pydantic_ai import Agent

from refactor_agent.models.prompt_config import PromptConfig


class LangfuseMetadata(BaseModel):
    """Arbitrary metadata for Langfuse spans (extra keys allowed)."""

    model_config = ConfigDict(extra="allow")


def _is_langfuse_available() -> bool:
    """True if Langfuse is configured (public key set)."""
    return bool(os.environ.get("LANGFUSE_PUBLIC_KEY"))


def _fallback_prompt_path(name: str) -> Path:
    """Path to local prompt file when Langfuse is not used."""
    base = Path(os.environ.get("REFACTOR_AGENT_PROMPTS_DIR", "prompts"))
    if not base.is_absolute():
        base = Path.cwd() / base
    return base / f"{name}.txt"


def _load_fallback_prompt(name: str, **variables: str) -> str:
    """Load prompt from prompts/<name>.txt and substitute {{key}} with variables."""
    path = _fallback_prompt_path(name)
    if not path.exists():
        return ""
    text = path.read_text()
    for key, value in variables.items():
        text = text.replace("{{" + key + "}}", value)
    # Replace any remaining {{...}} with empty string
    return re.sub(r"\{\{\w+\}\}", "", text)


def init_langfuse() -> None:
    """Initialize Langfuse tracing for all PydanticAI agents.

    Call once at application startup. Reads LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY, and LANGFUSE_BASE_URL from the environment.
    """
    Agent.instrument_all()


def get_prompt(name: str, **variables: str) -> str:
    """Fetch a prompt from the Langfuse registry and compile it with variables.

    When Langfuse is not configured (LANGFUSE_PUBLIC_KEY unset), loads from
    prompts/<name>.txt (or REFACTOR_AGENT_PROMPTS_DIR) and substitutes {{key}}.
    """
    if not _is_langfuse_available():
        return _load_fallback_prompt(name, **variables)
    langfuse = get_client()
    prompt = langfuse.get_prompt(name)
    return prompt.compile(**variables)


def get_prompt_config(name: str) -> PromptConfig:
    """Fetch a prompt's config from Langfuse (model, temperature, etc.).

    When Langfuse is not configured, returns empty config (callers use app defaults).
    """
    if not _is_langfuse_available():
        return PromptConfig()
    langfuse = get_client()
    prompt = langfuse.get_prompt(name)
    return PromptConfig.model_validate(prompt.config or {})


def get_prompt_name_and_version(name: str) -> tuple[str, str | int | None]:
    """Fetch prompt name and version from Langfuse for linked generation metadata.

    Returns (name, version). Version may be None if not available or when
    Langfuse is not configured.
    """
    if not _is_langfuse_available():
        return (name, None)
    try:
        langfuse = get_client()
        prompt = langfuse.get_prompt(name)
        # Langfuse SDK prompt object (untyped).
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
        span_input: object = None,
        metadata: LangfuseMetadata | None = None,
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
            meta = self._metadata.model_dump() if self._metadata else None
            # Langfuse SDK expects Any for metadata; we pass dict.
            self._inner_cm = client.start_as_current_observation(  # type: ignore[call-overload]
                name=self._name,
                as_type=self._as_type,
                input=self._span_input,
                metadata=meta,
            )
            cm = self._inner_cm
            obs = cm.__enter__() if cm is not None else None
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
        # Langfuse SDK can return non-None cm; mypy infers None from stub
        if self._inner_cm is not None:
            with contextlib.suppress(Exception):  # type: ignore[unreachable]
                self._inner_cm.__exit__(exc_type, exc_val, exc_tb)


def langfuse_span(
    name: str,
    *,
    as_type: str = "span",
    span_input: object = None,
    metadata: LangfuseMetadata | None = None,
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

    def update(self, **kwargs: object) -> None:
        """Forward keyword arguments to the underlying observation."""
        # Langfuse observation may be span or trace (untyped).
        update_fn = getattr(self._obs, "update", None)
        if callable(update_fn):
            update_fn(**kwargs)
