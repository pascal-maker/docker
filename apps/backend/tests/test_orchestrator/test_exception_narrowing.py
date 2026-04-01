"""Tests for INFRA-01: exception handler narrowing in orchestrator/agent.py."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pydantic_ai.models.test import TestModel

from refactor_agent.engine.subprocess_engine import SubprocessError
from refactor_agent.orchestrator.agent import (
    _apply_renames_per_file,
    _check_all_collisions,
    create_orchestrator_agent,
)
from refactor_agent.orchestrator.deps import OrchestratorDeps


def _make_deps(tmp_path: Path) -> OrchestratorDeps:
    return OrchestratorDeps(
        language="python",
        workspace=tmp_path,
        mode="Ask",
        file_ext="*.py",
    )


def _make_files(tmp_path: Path) -> list[Path]:
    f = tmp_path / "example.py"
    f.write_text("def foo(): pass\n", encoding="utf-8")
    return [f]


def _get_skeleton_tool_fn(
    agent: object,
) -> Callable[..., Awaitable[str]]:
    """Extract the show_file_skeleton async callable from the agent's toolset.

    Uses getattr on pydantic_ai private API — untyped third-party SDK internals.
    """
    # pydantic_ai Agent._function_toolset.tools is dict[str, Tool]
    toolset = getattr(agent, "_function_toolset")  # noqa: B009
    tools: dict[str, object] = getattr(toolset, "tools")  # noqa: B009
    tool = tools["show_file_skeleton"]
    fn: Callable[..., Awaitable[str]] = getattr(tool, "function")  # noqa: B009
    return fn


# ---------------------------------------------------------------------------
# _check_all_collisions
# ---------------------------------------------------------------------------


async def test_check_collisions_catches_subprocess_error(
    tmp_path: Path,
) -> None:
    """SubprocessError from EngineRegistry.create is caught; file is skipped."""
    deps = _make_deps(tmp_path)
    files = _make_files(tmp_path)
    with patch(
        "refactor_agent.orchestrator.agent.EngineRegistry.create",
        side_effect=SubprocessError("bridge failed"),
    ):
        result = await _check_all_collisions(deps, files, "new_name", None)
    assert result == []


async def test_check_collisions_catches_key_error(
    tmp_path: Path,
) -> None:
    """KeyError from EngineRegistry.create is caught; file is skipped."""
    deps = _make_deps(tmp_path)
    files = _make_files(tmp_path)
    with patch(
        "refactor_agent.orchestrator.agent.EngineRegistry.create",
        side_effect=KeyError("no engine for language"),
    ):
        result = await _check_all_collisions(deps, files, "new_name", None)
    assert result == []


async def test_check_collisions_does_not_catch_type_error(
    tmp_path: Path,
) -> None:
    """TypeError propagates uncaught from _check_all_collisions."""
    deps = _make_deps(tmp_path)
    files = _make_files(tmp_path)
    with patch(
        "refactor_agent.orchestrator.agent.EngineRegistry.create",
        side_effect=TypeError("programming bug"),
    ):
        with pytest.raises(TypeError, match="programming bug"):
            await _check_all_collisions(deps, files, "new_name", None)


# ---------------------------------------------------------------------------
# _apply_renames_per_file
# ---------------------------------------------------------------------------


async def test_apply_renames_catches_subprocess_error(
    tmp_path: Path,
) -> None:
    """SubprocessError from EngineRegistry.create is caught; file is skipped."""
    deps = _make_deps(tmp_path)
    files = _make_files(tmp_path)
    with patch(
        "refactor_agent.orchestrator.agent.EngineRegistry.create",
        side_effect=SubprocessError("bridge failed"),
    ):
        result = await _apply_renames_per_file(
            deps, files, "old_name", "new_name", None
        )
    assert result == []


async def test_apply_renames_catches_key_error(
    tmp_path: Path,
) -> None:
    """KeyError from EngineRegistry.create is caught; file is skipped."""
    deps = _make_deps(tmp_path)
    files = _make_files(tmp_path)
    with patch(
        "refactor_agent.orchestrator.agent.EngineRegistry.create",
        side_effect=KeyError("no engine"),
    ):
        result = await _apply_renames_per_file(
            deps, files, "old_name", "new_name", None
        )
    assert result == []


async def test_apply_renames_does_not_catch_type_error(
    tmp_path: Path,
) -> None:
    """TypeError propagates uncaught from _apply_renames_per_file."""
    deps = _make_deps(tmp_path)
    files = _make_files(tmp_path)
    with patch(
        "refactor_agent.orchestrator.agent.EngineRegistry.create",
        side_effect=TypeError("programming bug"),
    ):
        with pytest.raises(TypeError, match="programming bug"):
            await _apply_renames_per_file(
                deps, files, "old_name", "new_name", None
            )


# ---------------------------------------------------------------------------
# show_file_skeleton (accessed via pydantic_ai agent toolset internals)
# ---------------------------------------------------------------------------


async def test_show_file_skeleton_catches_subprocess_error(
    tmp_path: Path,
) -> None:
    """show_file_skeleton returns error string for SubprocessError."""
    agent = create_orchestrator_agent(model=TestModel())
    tool_fn = _get_skeleton_tool_fn(agent)

    file_name = "test.py"
    (tmp_path / file_name).write_text("def foo(): pass\n", encoding="utf-8")
    deps = _make_deps(tmp_path)
    ctx = MagicMock()
    ctx.deps = deps

    with patch(
        "refactor_agent.orchestrator.agent.EngineRegistry.create",
        side_effect=SubprocessError("bridge failed"),
    ):
        result = await tool_fn(ctx, file_name)

    assert result == f"Could not parse {file_name}."


async def test_show_file_skeleton_catches_key_error(
    tmp_path: Path,
) -> None:
    """show_file_skeleton returns error string for KeyError."""
    agent = create_orchestrator_agent(model=TestModel())
    tool_fn = _get_skeleton_tool_fn(agent)

    file_name = "test.py"
    (tmp_path / file_name).write_text("def foo(): pass\n", encoding="utf-8")
    deps = _make_deps(tmp_path)
    ctx = MagicMock()
    ctx.deps = deps

    with patch(
        "refactor_agent.orchestrator.agent.EngineRegistry.create",
        side_effect=KeyError("no engine"),
    ):
        result = await tool_fn(ctx, file_name)

    assert result == f"Could not parse {file_name}."


async def test_show_file_skeleton_does_not_catch_type_error(
    tmp_path: Path,
) -> None:
    """TypeError propagates uncaught from show_file_skeleton."""
    agent = create_orchestrator_agent(model=TestModel())
    tool_fn = _get_skeleton_tool_fn(agent)

    file_name = "test.py"
    (tmp_path / file_name).write_text("def foo(): pass\n", encoding="utf-8")
    deps = _make_deps(tmp_path)
    ctx = MagicMock()
    ctx.deps = deps

    with patch(
        "refactor_agent.orchestrator.agent.EngineRegistry.create",
        side_effect=TypeError("programming bug"),
    ):
        with pytest.raises(TypeError, match="programming bug"):
            await tool_fn(ctx, file_name)
