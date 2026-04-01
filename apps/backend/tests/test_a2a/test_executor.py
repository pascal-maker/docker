"""Tests for A2A executor: ASTRefactorAgentExecutor with shared orchestrator."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from a2a.types import (
    DataPart,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
)

from refactor_agent.a2a.executor import ASTRefactorAgentExecutor
from refactor_agent.a2a.models import OrchestratorStateEntry, StateStore
from refactor_agent.orchestrator import FinalOutput, NeedInputResult
from refactor_agent.orchestrator.deps import NeedInput, NeedInputPayload


async def test_executor_enqueues_artifact_and_status() -> None:
    """Executor enqueues rename-result artifact then completed status."""
    with tempfile.TemporaryDirectory() as tmp:
        replica = Path(tmp)
        (replica / "file.py").write_text("def old_name(): pass\n")
        with (
            patch(
                "refactor_agent.a2a.executor.run_orchestrator",
                new_callable=AsyncMock,
                return_value=(
                    FinalOutput(output="Rename complete (1 file(s)):\n- file.py"),
                    [],
                ),
            ),
            patch.dict("os.environ", {"REPLICA_DIR": str(replica)}, clear=False),
        ):
            context = MagicMock()
            context.task_id = "task-1"
            context.context_id = "ctx-1"
            context.current_task = None
            context.get_user_input.return_value = json.dumps(
                {
                    "old_name": "old_name",
                    "new_name": "new_name",
                    "use_replica": True,
                }
            )
            events: list[object] = []
            queue = AsyncMock()
            queue.enqueue_event = AsyncMock(side_effect=events.append)

            executor = ASTRefactorAgentExecutor(agent=MagicMock())
            await executor.execute(context, queue)

        assert len(events) >= 2
        art_ev = events[0]
        assert isinstance(art_ev, TaskArtifactUpdateEvent)
        assert art_ev.artifact.name == "rename-result"
        data_part = next(
            p.root for p in art_ev.artifact.parts if isinstance(p.root, DataPart)
        )
        assert data_part.data.get("modified_source") is not None
        assert data_part.data.get("path") is not None
        status_ev = events[-1]
        assert isinstance(status_ev, TaskStatusUpdateEvent)
        assert status_ev.status.state == TaskState.completed


async def test_executor_multi_file_rename_enqueues_one_artifact_per_file() -> None:
    """Multi-file request: one rename-result artifact per file, then status."""
    with tempfile.TemporaryDirectory() as tmp:
        replica = Path(tmp)
        (replica / "python").mkdir()
        (replica / "python" / "greeter.py").write_text("def greet(x):\n    return x\n")
        (replica / "python" / "caller.py").write_text(
            "from greeter import greet\n\nprint(greet(1))\n"
        )
        with (
            patch(
                "refactor_agent.a2a.executor.run_orchestrator",
                new_callable=AsyncMock,
                return_value=(
                    FinalOutput(output="Rename complete (2 file(s))"),
                    [],
                ),
            ),
            patch.dict("os.environ", {"REPLICA_DIR": str(replica)}, clear=False),
        ):
            context = MagicMock()
            context.task_id = "task-1"
            context.context_id = "ctx-1"
            context.current_task = None
            context.get_user_input.return_value = json.dumps(
                {
                    "old_name": "greet",
                    "new_name": "greet_by_name",
                    "use_replica": True,
                }
            )
            events: list[object] = []
            queue = AsyncMock()
            queue.enqueue_event = AsyncMock(side_effect=events.append)

            executor = ASTRefactorAgentExecutor(agent=MagicMock())
            await executor.execute(context, queue)

        assert len(events) == 3
        art1, art2, status_ev = events[0], events[1], events[2]
        assert isinstance(art1, TaskArtifactUpdateEvent)
        assert isinstance(art2, TaskArtifactUpdateEvent)
        assert art1.artifact.name == art2.artifact.name == "rename-result"
        data1 = next(
            p.root for p in art1.artifact.parts if isinstance(p.root, DataPart)
        )
        data2 = next(
            p.root for p in art2.artifact.parts if isinstance(p.root, DataPart)
        )
        paths = {data1.data.get("path"), data2.data.get("path")}
        assert paths == {"python/greeter.py", "python/caller.py"}
        assert isinstance(status_ev, TaskStatusUpdateEvent)
        assert status_ev.status.state == TaskState.completed


async def test_executor_empty_input_returns_error() -> None:
    """Executor with empty input enqueues failed status with error."""
    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.current_task = None
    context.get_user_input.return_value = "   "
    events: list[object] = []
    queue = AsyncMock()
    queue.enqueue_event = AsyncMock(side_effect=events.append)

    executor = ASTRefactorAgentExecutor(agent=MagicMock())
    await executor.execute(context, queue)

    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TaskStatusUpdateEvent)
    assert ev.status.state == TaskState.failed
    part_text = ev.status.message.parts[0].root.text
    assert "ERROR" in part_text
    assert "empty" in part_text.lower()


async def test_executor_collision_enqueues_artifact_and_input_required() -> None:
    """Collision: executor enqueues refactor-input-required and input_required."""
    need = NeedInput(
        type="rename_collision",
        message="Name collision for 'main'. Reply with: yes to force, no to cancel.",
        payload=NeedInputPayload.model_validate(
            {"old_name": "greet", "new_name": "main"}
        ),
    )
    with tempfile.TemporaryDirectory() as tmp:
        replica = Path(tmp)
        (replica / "file.py").write_text(
            "def main() -> None:\n    pass\n\ndef greet(n):\n    return n\n"
        )
        with (
            patch(
                "refactor_agent.a2a.executor.run_orchestrator",
                new_callable=AsyncMock,
                return_value=(NeedInputResult(need_input=need, run_state=[]), []),
            ),
            patch.dict("os.environ", {"REPLICA_DIR": str(replica)}, clear=False),
        ):
            context = MagicMock()
            context.task_id = "task-1"
            context.context_id = "ctx-1"
            context.current_task = None
            context.get_user_input.return_value = json.dumps(
                {
                    "old_name": "greet",
                    "new_name": "main",
                    "use_replica": True,
                }
            )
            events: list[object] = []
            queue = AsyncMock()
            queue.enqueue_event = AsyncMock(side_effect=events.append)

            executor = ASTRefactorAgentExecutor(agent=MagicMock())
            await executor.execute(context, queue)

        assert len(events) == 2
        artifact_ev = events[0]
        # A2A SDK event (untyped).
        assert getattr(artifact_ev, "artifact", None) is not None
        assert artifact_ev.artifact.name == "refactor-input-required"
        status_ev = events[1]
        assert status_ev.status.state == TaskState.input_required


async def test_executor_resumption_yes_proceeds_with_rename() -> None:
    """Resumption with 'yes' runs orchestrator again and enqueues result + completed."""
    with tempfile.TemporaryDirectory() as tmp:
        workspace_dir = Path(tmp)
        (workspace_dir / "file.py").write_text("def old_name(): pass\n")
        state_store = StateStore(
            {
                "t1": OrchestratorStateEntry(
                    message_history=[],
                    workspace_dir=str(workspace_dir),
                    use_replica=True,
                ),
            }
        )
        task = MagicMock()
        task.status = TaskStatus(state=TaskState.input_required)
        task.artifacts = []

        context = MagicMock()
        context.task_id = "t1"
        context.context_id = "c1"
        context.current_task = task
        context.get_user_input.return_value = "yes"

        events: list[object] = []
        queue = AsyncMock()
        queue.enqueue_event = AsyncMock(side_effect=events.append)

        with (
            patch.dict("os.environ", {"REPLICA_DIR": str(workspace_dir)}, clear=False),
            patch(
                "refactor_agent.a2a.executor.run_orchestrator",
                new_callable=AsyncMock,
                return_value=(
                    FinalOutput(output="Rename complete (1 file(s)):\n- file.py"),
                    [],
                ),
            ),
        ):
            executor = ASTRefactorAgentExecutor(
                state_store=state_store,
                agent=MagicMock(),
            )
            await executor.execute(context, queue)

        assert len(events) >= 2
        assert isinstance(events[0], TaskArtifactUpdateEvent)
        status_ev = events[-1]
        assert status_ev.status.state == TaskState.completed
        assert "Rename" in status_ev.status.message.parts[0].root.text


async def test_executor_resumption_no_cancels() -> None:
    """Resumption with 'no' enqueues completed with cancel message."""
    with tempfile.TemporaryDirectory() as tmp:
        workspace_dir = Path(tmp)
        (workspace_dir / "f.py").write_text("def f(): pass\n")
        state_store = StateStore(
            {
                "t1": OrchestratorStateEntry(
                    message_history=[],
                    workspace_dir=str(workspace_dir),
                    use_replica=True,
                ),
            }
        )
        task = MagicMock()
        task.status = TaskStatus(state=TaskState.input_required)
        task.artifacts = []

        context = MagicMock()
        context.task_id = "t1"
        context.context_id = "c1"
        context.current_task = task
        context.get_user_input.return_value = "no"

        events: list[object] = []
        queue = AsyncMock()
        queue.enqueue_event = AsyncMock(side_effect=events.append)

        with (
            patch.dict("os.environ", {"REPLICA_DIR": str(workspace_dir)}, clear=False),
            patch(
                "refactor_agent.a2a.executor.run_orchestrator",
                new_callable=AsyncMock,
                return_value=(
                    FinalOutput(output="Rename canceled."),
                    [],
                ),
            ),
        ):
            executor = ASTRefactorAgentExecutor(
                state_store=state_store,
                agent=MagicMock(),
            )
            await executor.execute(context, queue)

        assert len(events) >= 1
        ev = events[-1]
        assert ev.status.state == TaskState.completed
        assert "cancel" in ev.status.message.parts[0].root.text.lower()


async def test_executor_rejects_without_use_replica() -> None:
    """Executor rejects request without use_replica with failed status."""
    context = MagicMock()
    context.task_id = "task-1"
    context.context_id = "ctx-1"
    context.current_task = None
    context.get_user_input.return_value = json.dumps(
        {"old_name": "foo", "new_name": "bar"}
    )
    events: list[object] = []
    queue = AsyncMock()
    queue.enqueue_event = AsyncMock(side_effect=events.append)

    executor = ASTRefactorAgentExecutor(agent=MagicMock())
    await executor.execute(context, queue)

    assert len(events) == 1
    ev = events[0]
    assert isinstance(ev, TaskStatusUpdateEvent)
    assert ev.status.state == TaskState.failed
    part_text = ev.status.message.parts[0].root.text
    assert "use_replica" in part_text.lower()


async def test_executor_use_replica_uses_replica_dir() -> None:
    """When use_replica is true and REPLICA_DIR exists, executor uses it as workspace."""
    with tempfile.TemporaryDirectory() as tmp:
        replica = Path(tmp)
        (replica / "a.py").write_text("def foo(): pass\n")
        with (
            patch(
                "refactor_agent.a2a.executor.run_orchestrator",
                new_callable=AsyncMock,
                return_value=(
                    FinalOutput(output="Rename complete (1 file(s))"),
                    [],
                ),
            ),
            patch.dict("os.environ", {"REPLICA_DIR": str(replica)}, clear=False),
        ):
            context = MagicMock()
            context.task_id = "task-1"
            context.context_id = "ctx-1"
            context.current_task = None
            context.get_user_input.return_value = json.dumps(
                {"old_name": "foo", "new_name": "bar", "use_replica": True}
            )
            events: list[object] = []
            queue = AsyncMock()
            queue.enqueue_event = AsyncMock(side_effect=events.append)

            executor = ASTRefactorAgentExecutor(agent=MagicMock())
            await executor.execute(context, queue)

        assert len(events) >= 2
        art_ev = events[0]
        assert isinstance(art_ev, TaskArtifactUpdateEvent)
        assert art_ev.artifact.name == "rename-result"
        data_part = next(
            p.root for p in art_ev.artifact.parts if isinstance(p.root, DataPart)
        )
        assert data_part.data.get("path") == "a.py"
        assert data_part.data.get("modified_source") is not None
        status_ev = events[-1]
        assert status_ev.status.state == TaskState.completed


async def test_executor_cancel_raises() -> None:
    """Executor cancel() raises NotImplementedError."""
    executor = ASTRefactorAgentExecutor(agent=MagicMock())
    with pytest.raises(NotImplementedError, match="cancel"):
        await executor.cancel(MagicMock(), AsyncMock())


def test_executor_instances_have_isolated_state() -> None:
    """Two executors created without StateStore do not share state (INFRA-02)."""
    exec_a = ASTRefactorAgentExecutor(agent=MagicMock())
    exec_b = ASTRefactorAgentExecutor(agent=MagicMock())
    exec_a._state_store["task-1"] = OrchestratorStateEntry(
        message_history=[],
        workspace_dir="/nonexistent/ws",
        use_replica=True,
        language="python",
    )
    assert "task-1" not in exec_b._state_store


def test_executor_uses_injected_state_store() -> None:
    """Injected StateStore is used when provided."""
    store = StateStore.model_validate({})
    executor = ASTRefactorAgentExecutor(state_store=store, agent=MagicMock())
    assert executor._state_store is store.root
