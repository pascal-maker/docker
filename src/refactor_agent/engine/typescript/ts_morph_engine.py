"""TypeScript refactoring engine using ts-morph via a subprocess bridge."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from refactor_agent.engine.base import CollisionInfo
from refactor_agent.engine.subprocess_engine import SubprocessEngine

if TYPE_CHECKING:
    from typing import Any

logger = logging.getLogger(__name__)

_BRIDGE_DIR = Path(__file__).resolve().parent / "bridge"
_BRIDGE_ENTRY = _BRIDGE_DIR / "src" / "index.ts"
_TSX_BIN = _BRIDGE_DIR / "node_modules" / ".bin" / "tsx"


class TsMorphEngine(SubprocessEngine):
    """TypeScript engine that delegates to a ts-morph JSON-RPC bridge.

    Must be used as an async context manager::

        async with TsMorphEngine(source) as engine:
            result = await engine.rename_symbol("foo", "bar")
            new_src = await engine.to_source()
    """

    language: str = "typescript"

    def __init__(self, source: str) -> None:
        """Store the source to be sent on bridge init."""
        super().__init__()
        self._source = source

    def _command(self) -> list[str]:
        """Return command to start the ts-morph bridge process."""
        return [str(_TSX_BIN), str(_BRIDGE_ENTRY)]

    async def __aenter__(self) -> TsMorphEngine:
        """Start the bridge and initialize it with the source."""
        await super().__aenter__()
        await self._call("init", {"source": self._source})
        return self

    async def get_skeleton(self) -> str:
        """Return a text skeleton of the TypeScript source."""
        result = await self._call("get_skeleton", {})
        return str(result)

    async def rename_symbol(
        self,
        old_name: str,
        new_name: str,
        scope_node: str | None = None,
    ) -> str:
        """Rename a symbol in the TypeScript source.

        Args:
            old_name: Current symbol name.
            new_name: Desired new name.
            scope_node: Optional function/class to restrict scope.
        """
        params: dict[str, Any] = {
            "old_name": old_name,
            "new_name": new_name,
        }
        if scope_node is not None:
            params["scope_node"] = scope_node
        result = await self._call("rename_symbol", params)
        return str(result)

    async def extract_function(
        self,
        _scope_function: str,
        _start_line: int,
        _end_line: int,
        _new_function_name: str,
    ) -> str:
        """Not implemented for TypeScript."""
        return (
            "ERROR: extract_function is not yet implemented for TypeScript; "
            "only rename_symbol is supported."
        )

    async def check_name_collisions(
        self,
        new_name: str,
        scope_node: str | None = None,
    ) -> list[CollisionInfo]:
        """Check for existing definitions that would conflict with new_name."""
        params: dict[str, Any] = {"new_name": new_name}
        if scope_node is not None:
            params["scope_node"] = scope_node
        result = await self._call("check_name_collisions", params)
        if not isinstance(result, list):
            return []
        return [
            CollisionInfo(
                location=item.get("location", "unknown"),
                kind=item.get("kind", "unknown"),
            )
            for item in result
            if isinstance(item, dict)
        ]

    async def to_source(self) -> str:
        """Return the current TypeScript source text."""
        result = await self._call("to_source", {})
        return str(result)
