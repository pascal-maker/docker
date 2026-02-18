"""Tests for A2A executor: _handle_rename_task and ASTRefactorAgentExecutor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from document_structuring_agent.ast_refactor.a2a_executor import (
    ASTRefactorAgentExecutor,
    _handle_rename_task,
)


def test_handle_rename_task_success() -> None:
    """Structured JSON yields rename summary and modified source."""
    payload = {
        "source": "def calculate_tax(amount, rate):\n    return amount * rate\n",
        "old_name": "calculate_tax",
        "new_name": "compute_tax",
    }
    result = _handle_rename_task(__import__("json").dumps(payload))
    assert "Renamed" in result
    assert "compute_tax" in result
    assert "--- Modified source ---" in result
    assert "def compute_tax(" in result
    # Modified source block must not contain the old name as definition
    assert "def calculate_tax(" not in result


def test_handle_rename_task_invalid_json() -> None:
    """Invalid JSON returns error."""
    result = _handle_rename_task("not json")
    assert "ERROR" in result
    assert "JSON" in result


def test_handle_rename_task_missing_fields() -> None:
    """Missing required fields return error."""
    result = _handle_rename_task('{"source": "def f(): pass"}')
    assert "ERROR" in result
    assert "old_name" in result or "new_name" in result


def test_handle_rename_task_symbol_not_found() -> None:
    """Symbol not in source returns error from engine."""
    payload = {
        "source": "def foo(): pass\n",
        "old_name": "bar",
        "new_name": "baz",
    }
    result = _handle_rename_task(__import__("json").dumps(payload))
    assert "ERROR" in result


def test_handle_rename_task_scope_node() -> None:
    """Optional scope_node is passed to engine."""
    payload = {
        "source": "def outer():\n    x = 1\n    return x\n\ndef other():\n    x = 2\n",
        "old_name": "x",
        "new_name": "value",
        "scope_node": "outer",
    }
    result = _handle_rename_task(__import__("json").dumps(payload))
    assert "Renamed" in result
    assert "value = 1" in result
    assert "x = 2" in result


@pytest.mark.asyncio
async def test_executor_enqueues_agent_message() -> None:
    """Executor execute() enqueues one agent message with rename result."""
    context = MagicMock()
    context.get_user_input.return_value = __import__("json").dumps(
        {
            "source": "def old_name(): pass\n",
            "old_name": "old_name",
            "new_name": "new_name",
        }
    )
    events: list = []
    queue = AsyncMock()
    queue.enqueue_event = AsyncMock(side_effect=events.append)

    executor = ASTRefactorAgentExecutor()
    await executor.execute(context, queue)

    assert len(events) == 1
    msg = events[0]
    assert msg.role.value == "agent"
    assert len(msg.parts) == 1
    part = msg.parts[0].root
    assert "Renamed" in part.text
    assert "def new_name(): pass" in part.text


@pytest.mark.asyncio
async def test_executor_empty_input_returns_error() -> None:
    """Executor with empty input enqueues error message."""
    context = MagicMock()
    context.get_user_input.return_value = "   "
    events: list = []
    queue = AsyncMock()
    queue.enqueue_event = AsyncMock(side_effect=events.append)

    executor = ASTRefactorAgentExecutor()
    await executor.execute(context, queue)

    assert len(events) == 1
    part_text = events[0].parts[0].root.text
    assert "ERROR" in part_text
    assert "empty" in part_text


@pytest.mark.asyncio
async def test_executor_cancel_raises() -> None:
    """Executor cancel() raises NotImplementedError."""
    executor = ASTRefactorAgentExecutor()
    with pytest.raises(NotImplementedError, match="cancel"):
        await executor.cancel(MagicMock(), AsyncMock())
