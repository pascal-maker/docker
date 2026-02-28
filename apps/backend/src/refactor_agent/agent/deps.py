from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from refactor_agent.engine.base import RefactorEngine


@dataclass
class ASTDeps:
    """Dependencies injected into every AST refactor agent tool call."""

    engine: RefactorEngine
    target_rename: tuple[str, str]  # (old_name, new_name)
