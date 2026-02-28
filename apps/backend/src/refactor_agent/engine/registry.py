"""Language-to-engine factory registry."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

if TYPE_CHECKING:
    from collections.abc import Callable

    from refactor_agent.engine.base import RefactorEngine


class EngineRegistry:
    """Maps language strings to engine factory functions.

    Factories accept a source string and return a ``RefactorEngine`` instance.
    """

    _factories: ClassVar[dict[str, Callable[[str], RefactorEngine]]] = {}

    @classmethod
    def register(
        cls,
        language: str,
        factory: Callable[[str], RefactorEngine],
    ) -> None:
        """Register a factory for the given language."""
        cls._factories[language] = factory

    @classmethod
    def create(cls, language: str, source: str) -> RefactorEngine:
        """Create an engine for *language* by passing *source* to its factory.

        Raises:
            KeyError: If no factory is registered for *language*.
        """
        try:
            factory = cls._factories[language]
        except KeyError:
            supported = ", ".join(sorted(cls._factories)) or "(none)"
            msg = (
                f"No engine registered for language {language!r}. "
                f"Supported: {supported}"
            )
            raise KeyError(msg) from None
        return factory(source)

    @classmethod
    def supported_languages(cls) -> list[str]:
        """Return sorted list of registered language names."""
        return sorted(cls._factories)
