"""Tests for A2A executor: _handle_rename_task and ASTRefactorAgentExecutor."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from a2a.types import (
    Artifact,
    DataPart,
    Part,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)

from refactor_agent.a2a.executor import (
    PENDING_RENAME_KEY,
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
    """Executor enqueues rename-result artifact then TaskStatusUpdateEvent."""
    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.current_task = None
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

    assert len(events) == 2
    art_ev = events[0]
    assert isinstance(art_ev, TaskArtifactUpdateEvent)
    assert art_ev.artifact.name == "rename-result"
    data_part = next(
        p.root for p in art_ev.artifact.parts if isinstance(p.root, DataPart)
    )
    assert data_part.data.get("modified_source") is not None
    assert "def new_name(): pass" in data_part.data["modified_source"]
    ev = events[1]
    assert isinstance(ev, TaskStatusUpdateEvent)
    assert ev.status.state == TaskState.completed
    assert ev.status.message is not None
    part = ev.status.message.parts[0].root
    assert "Renamed" in part.text
    assert "def new_name(): pass" in part.text


@pytest.mark.asyncio
async def test_executor_multi_file_rename_enqueues_one_artifact_per_file() -> None:
    """Multi-file request: one rename-result artifact per file, then combined status."""
    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.current_task = None
    context.get_user_input.return_value = __import__("json").dumps(
        {
            "old_name": "greet",
            "new_name": "greet_by_name",
            "files": [
                {
                    "path": "python/greeter.py",
                    "source": "def greet(x):\n    return x\n",
                },
                {
                    "path": "python/caller.py",
                    "source": "from greeter import greet\n\nprint(greet(1))\n",
                },
            ],
        }
    )
    events: list = []
    queue = AsyncMock()
    queue.enqueue_event = AsyncMock(side_effect=events.append)

    executor = ASTRefactorAgentExecutor()
    await executor.execute(context, queue)

    # Two artifacts (one per file) + one status
    assert len(events) == 3
    art1, art2, status_ev = events[0], events[1], events[2]
    assert isinstance(art1, TaskArtifactUpdateEvent)
    assert isinstance(art2, TaskArtifactUpdateEvent)
    assert art1.artifact.name == art2.artifact.name == "rename-result"
    data1 = next(p.root for p in art1.artifact.parts if isinstance(p.root, DataPart))
    data2 = next(p.root for p in art2.artifact.parts if isinstance(p.root, DataPart))
    assert data1.data.get("path") == "python/greeter.py"
    assert data2.data.get("path") == "python/caller.py"
    assert "def greet_by_name(" in data1.data["modified_source"]
    assert "greet_by_name" in data2.data["modified_source"]
    assert isinstance(status_ev, TaskStatusUpdateEvent)
    assert status_ev.status.state == TaskState.completed
    assert "Renamed in 2 file(s)" in status_ev.status.message.parts[0].root.text


@pytest.mark.asyncio
async def test_executor_workspace_returns_artifacts_only_for_impacted_files() -> None:
    """Workspace: only files that reference the symbol get artifacts."""
    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.current_task = None
    context.get_user_input.return_value = __import__("json").dumps(
        {
            "old_name": "greet",
            "new_name": "greet_by_name",
            "workspace": [
                {
                    "path": "python/greeter.py",
                    "source": "def greet(x):\n    return x\n",
                },
                {
                    "path": "python/caller.py",
                    "source": "from greeter import greet\n\nprint(greet(1))\n",
                },
                {
                    "path": "python/other.py",
                    "source": "def unrelated():\n    pass\n",
                },
            ],
        }
    )
    events: list = []
    queue = AsyncMock()
    queue.enqueue_event = AsyncMock(side_effect=events.append)

    executor = ASTRefactorAgentExecutor()
    await executor.execute(context, queue)

    # Two artifacts (greeter, caller); other.py does not reference greet
    assert len(events) == 3
    art1, art2, status_ev = events[0], events[1], events[2]
    assert isinstance(art1, TaskArtifactUpdateEvent)
    assert isinstance(art2, TaskArtifactUpdateEvent)
    assert art1.artifact.name == art2.artifact.name == "rename-result"
    data1 = next(p.root for p in art1.artifact.parts if isinstance(p.root, DataPart))
    data2 = next(p.root for p in art2.artifact.parts if isinstance(p.root, DataPart))
    paths = {data1.data.get("path"), data2.data.get("path")}
    assert paths == {"python/greeter.py", "python/caller.py"}
    assert isinstance(status_ev, TaskStatusUpdateEvent)
    assert status_ev.status.state == TaskState.completed
    assert "Renamed in 2 file(s)" in status_ev.status.message.parts[0].root.text


@pytest.mark.asyncio
async def test_executor_workspace_no_references_returns_failed() -> None:
    """Workspace with no file referencing the symbol returns failed."""
    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.current_task = None
    context.get_user_input.return_value = __import__("json").dumps(
        {
            "old_name": "missing",
            "new_name": "other",
            "workspace": [
                {"path": "a.py", "source": "def foo(): pass\n"},
            ],
        }
    )
    events: list = []
    queue = AsyncMock()
    queue.enqueue_event = AsyncMock(side_effect=events.append)

    executor = ASTRefactorAgentExecutor()
    await executor.execute(context, queue)

    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TaskStatusUpdateEvent)
    assert ev.status.state == TaskState.failed
    assert "no files" in ev.status.message.parts[0].root.text
    assert "missing" in ev.status.message.parts[0].root.text


@pytest.mark.asyncio
async def test_executor_empty_input_returns_error() -> None:
    """Executor with empty input enqueues TaskStatusUpdateEvent (failed) with error."""
    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.current_task = None
    context.get_user_input.return_value = "   "
    events: list = []
    queue = AsyncMock()
    queue.enqueue_event = AsyncMock(side_effect=events.append)

    executor = ASTRefactorAgentExecutor()
    await executor.execute(context, queue)

    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TaskStatusUpdateEvent)
    assert ev.status.state == TaskState.failed
    part_text = ev.status.message.parts[0].root.text
    assert "ERROR" in part_text
    assert "empty" in part_text


@pytest.mark.asyncio
async def test_executor_collision_enqueues_artifact_and_status() -> None:
    """Collision: executor enqueues artifact + status, no rename message."""
    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.current_task = None
    # Source has main() and greet(); renaming greet -> main causes collision
    source = "def main() -> None:\n    pass\n\ndef greet(n):\n    return n\n"
    context.get_user_input.return_value = __import__("json").dumps(
        {
            "source": source,
            "old_name": "greet",
            "new_name": "main",
        }
    )
    events: list = []
    queue = AsyncMock()
    queue.enqueue_event = AsyncMock(side_effect=events.append)

    executor = ASTRefactorAgentExecutor()
    await executor.execute(context, queue)

    assert len(events) == 2
    # First event: TaskArtifactUpdateEvent with artifact containing pending_rename
    artifact_ev = events[0]
    assert getattr(artifact_ev, "artifact", None) is not None
    artifact = artifact_ev.artifact
    assert any(
        getattr(p.root, "data", {}).get(PENDING_RENAME_KEY)
        for p in artifact.parts
        if hasattr(p, "root") and hasattr(p.root, "data")
    )
    # Second event: TaskStatusUpdateEvent with input_required
    status_ev = events[1]
    assert getattr(status_ev, "status", None) is not None
    assert status_ev.status.state == TaskState.input_required
    # No "Renamed" message
    for e in events:
        if hasattr(e, "parts") and e.parts:
            text = getattr(e.parts[0].root, "text", "") or ""
            assert "Renamed" not in text


@pytest.mark.asyncio
async def test_executor_resumption_yes_proceeds_with_rename() -> None:
    """Resumption with 'yes' runs rename and enqueues result + completed."""
    pending = {
        "source": "def old_name(): pass\n",
        "old_name": "old_name",
        "new_name": "new_name",
        "scope_node": None,
    }
    artifact = Artifact(
        artifact_id="a1",
        parts=[
            Part(root=TextPart(text="Collision")),
            Part(root=DataPart(data={PENDING_RENAME_KEY: pending})),
        ],
    )
    task = MagicMock()
    task.status = TaskStatus(state=TaskState.input_required)
    task.artifacts = [artifact]

    context = MagicMock()
    context.task_id = "t1"
    context.context_id = "c1"
    context.current_task = task
    context.get_user_input.return_value = "yes"

    events: list = []
    queue = AsyncMock()
    queue.enqueue_event = AsyncMock(side_effect=events.append)

    executor = ASTRefactorAgentExecutor()
    await executor.execute(context, queue)

    assert len(events) == 2
    assert isinstance(events[0], TaskArtifactUpdateEvent)
    ev = events[1]
    assert ev.status.state == TaskState.completed
    assert "Renamed" in ev.status.message.parts[0].root.text


@pytest.mark.asyncio
async def test_executor_resumption_no_cancels() -> None:
    """Resumption with 'no' enqueues cancel message and completed."""
    pending = {
        "source": "def f(): pass\n",
        "old_name": "f",
        "new_name": "main",
        "scope_node": None,
    }
    artifact = Artifact(
        artifact_id="a1",
        parts=[
            Part(root=DataPart(data={PENDING_RENAME_KEY: pending})),
        ],
    )
    task = MagicMock()
    task.status = TaskStatus(state=TaskState.input_required)
    task.artifacts = [artifact]

    context = MagicMock()
    context.task_id = "t1"
    context.context_id = "c1"
    context.current_task = task
    context.get_user_input.return_value = "no"

    events: list = []
    queue = AsyncMock()
    queue.enqueue_event = AsyncMock(side_effect=events.append)

    executor = ASTRefactorAgentExecutor()
    await executor.execute(context, queue)

    assert len(events) == 1
    ev = events[0]
    assert ev.status.state == TaskState.completed
    assert "canceled" in ev.status.message.parts[0].root.text.lower()


@pytest.mark.asyncio
async def test_executor_cancel_raises() -> None:
    """Executor cancel() raises NotImplementedError."""
    executor = ASTRefactorAgentExecutor()
    with pytest.raises(NotImplementedError, match="cancel"):
        await executor.cancel(MagicMock(), AsyncMock())
