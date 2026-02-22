"""A2A executor: shared orchestrator; translate message, run, emit artifacts."""

from __future__ import annotations

import json
import shutil
import tempfile
import uuid
from pathlib import Path

from a2a.server.agent_execution import AgentExecutor, RequestContext  # noqa: TC002
from a2a.server.events import EventQueue  # noqa: TC002
from a2a.types import (
    Artifact,
    DataPart,
    Message,
    Part,
    Role,
    TaskArtifactUpdateEvent,
    TaskState,
    TaskStatus,
    TaskStatusUpdateEvent,
    TextPart,
)

from refactor_agent.orchestrator import (
    NeedInputResult,
    OrchestratorDeps,
    create_orchestrator_agent,
    run_orchestrator,
)

REPLICA_DIR_ENV = "REPLICA_DIR"
ORCHESTRATOR_STATE_KEY = "orchestrator_state"

# task_id -> {message_history, workspace_dir} for pause/resume
_orchestrator_state: dict[str, dict] = {}

_ARTIFACT_PREVIEW_LEN = 200


def _agent_message(text: str) -> Message:
    return Message(
        message_id=uuid.uuid4().hex,
        role=Role.agent,
        parts=[Part(root=TextPart(text=text))],
    )


def _status_event(
    task_id: str,
    context_id: str,
    state: TaskState,
    message_text: str,
    *,
    final: bool = True,
) -> TaskStatusUpdateEvent:
    return TaskStatusUpdateEvent(
        task_id=task_id,
        context_id=context_id,
        status=TaskStatus(state=state, message=_agent_message(message_text)),
        final=final,
    )


def _parse_rename_params(user_input: str) -> dict | str:  # noqa: C901, PLR0911, PLR0912
    """Parse JSON to rename params. Returns dict or error string. Backward compat."""
    try:
        data = json.loads(user_input)
    except json.JSONDecodeError as e:
        return f"ERROR: invalid JSON: {e}"
    old_name = data.get("old_name")
    new_name = data.get("new_name")
    scope_node = data.get("scope_node")
    if not isinstance(old_name, str):
        return "ERROR: missing or invalid 'old_name' (must be a string)"
    if not isinstance(new_name, str):
        return "ERROR: missing or invalid 'new_name' (must be a string)"
    if scope_node is not None and not isinstance(scope_node, str):
        return "ERROR: 'scope_node' must be a string or null"

    workspace = data.get("workspace")
    if isinstance(workspace, list) and len(workspace) > 0:
        out_workspace: list[dict[str, str]] = []
        for i, item in enumerate(workspace):
            if not isinstance(item, dict):
                return f"ERROR: 'workspace[{i}]' must be an object"
            p = item.get("path")
            s = item.get("source")
            if not isinstance(p, str) or not p.strip():
                return f"ERROR: 'workspace[{i}].path' must be a non-empty string"
            if not isinstance(s, str):
                return f"ERROR: 'workspace[{i}].source' must be a string"
            out_workspace.append({"path": p, "source": s})
        return {
            "workspace": out_workspace,
            "old_name": old_name,
            "new_name": new_name,
            "scope_node": scope_node,
        }

    files = data.get("files")
    if isinstance(files, list) and len(files) > 0:
        out_files: list[dict[str, str]] = []
        for i, item in enumerate(files):
            if not isinstance(item, dict):
                return f"ERROR: 'files[{i}]' must be an object"
            p = item.get("path")
            s = item.get("source")
            if not isinstance(p, str) or not p.strip():
                return f"ERROR: 'files[{i}].path' must be a non-empty string"
            if not isinstance(s, str):
                return f"ERROR: 'files[{i}].source' must be a string"
            out_files.append({"path": p, "source": s})
        return {
            "workspace": out_files,
            "old_name": old_name,
            "new_name": new_name,
            "scope_node": scope_node,
        }

    source = data.get("source")
    path = data.get("path")
    if not isinstance(source, str):
        return "ERROR: missing or invalid 'source' (must be a string)"
    if path is not None and not isinstance(path, str):
        return "ERROR: 'path' must be a string or null"
    return {
        "source": source,
        "old_name": old_name,
        "new_name": new_name,
        "scope_node": scope_node,
        "path": path,
    }


def _build_workspace_dir(parsed: dict) -> Path:
    """Create a temp dir and write workspace files from parsed. Caller must cleanup."""
    tmp = tempfile.mkdtemp(prefix="refactor_a2a_")
    root = Path(tmp)
    workspace = parsed.get("workspace")
    if isinstance(workspace, list):
        for item in workspace:
            path = item.get("path", "")
            source = item.get("source", "")
            out_path = root / path
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(source, encoding="utf-8")
    else:
        source = parsed.get("source", "")
        path = parsed.get("path") or "file.py"
        out_path = root / path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(source, encoding="utf-8")
    return root


def _internal_message_from_parsed(parsed: dict) -> str:
    """Build the prompt we send to the orchestrator for rename-shaped input."""
    old_name = parsed.get("old_name", "")
    new_name = parsed.get("new_name", "")
    return (
        f"Rename the symbol '{old_name}' to '{new_name}' across the workspace. "
        "Apply the rename to every file that references the symbol."
    )


def _artifact_from_modified_file(
    task_id: str,
    context_id: str,
    path: str,
    modified_source: str,
    *,
    append: bool = False,
) -> TaskArtifactUpdateEvent:
    """Build a rename-result artifact from path and modified source."""
    data: dict[str, str | None] = {
        "summary": f"Modified {path}",
        "modified_source": modified_source,
        "path": path,
    }
    artifact = Artifact(
        artifact_id=uuid.uuid4().hex,
        name="rename-result",
        description="Refactored source; apply modified_source to path.",
        parts=[
            Part(
                root=TextPart(
                    text=modified_source[:_ARTIFACT_PREVIEW_LEN]
                    + ("..." if len(modified_source) > _ARTIFACT_PREVIEW_LEN else "")
                )
            ),
            Part(root=DataPart(data=data)),
        ],
    )
    return TaskArtifactUpdateEvent(
        task_id=task_id,
        context_id=context_id,
        artifact=artifact,
        append=append,
    )


async def _emit_artifacts_from_workspace(
    workspace_dir: Path,
    task_id: str,
    context_id: str,
    event_queue: EventQueue,
) -> None:
    """Emit one rename-result artifact per .py file in the workspace."""
    first = True
    for fp in sorted(workspace_dir.rglob("*.py")):  # noqa: ASYNC240
        if not fp.is_file():
            continue
        rel = fp.relative_to(workspace_dir)
        path_str = str(rel).replace("\\", "/")
        content = fp.read_text(encoding="utf-8")
        await event_queue.enqueue_event(
            _artifact_from_modified_file(
                task_id,
                context_id,
                path_str,
                content,
                append=not first,
            )
        )
        first = False


class ASTRefactorAgentExecutor(AgentExecutor):
    """Translate A2A message, run orchestrator, emit input_required or artifacts."""

    def __init__(
        self,
        state_store: dict[str, dict] | None = None,
        agent: object | None = None,
    ) -> None:
        self._state_store = (
            state_store if state_store is not None else _orchestrator_state
        )
        self._agent = agent if agent is not None else create_orchestrator_agent()

    async def execute(  # noqa: C901, PLR0911, PLR0912, PLR0915
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Run orchestrator; emit input_required or artifacts."""
        user_input = (context.get_user_input() or "").strip()
        task_id = context.task_id
        context_id = context.context_id
        if task_id is None or context_id is None:
            await event_queue.enqueue_event(
                _agent_message("ERROR: missing task_id or context_id")
            )
            return
        current_task = getattr(context, "current_task", None)

        # Resumption: we were waiting for user input
        saved = self._state_store.get(task_id)
        if (
            saved is not None
            and current_task is not None
            and current_task.status.state == TaskState.input_required
        ):
            message_history = saved.get("message_history")
            workspace_dir_str = saved.get("workspace_dir")
            if message_history is not None and workspace_dir_str is not None:
                workspace_dir = Path(workspace_dir_str)
                if not workspace_dir.exists():  # noqa: ASYNC240
                    del self._state_store[task_id]
                    await event_queue.enqueue_event(
                        _status_event(
                            task_id,
                            context_id,
                            TaskState.failed,
                            "Session expired; please submit the request again.",
                        )
                    )
                    return
                deps = OrchestratorDeps(
                    language="python",
                    workspace=workspace_dir,
                    mode="Auto",
                    file_ext="*.py",
                    get_user_input=None,
                )
                result, run_state = await run_orchestrator(
                    self._agent,
                    deps,
                    user_input,
                    message_history=message_history,
                )
                if isinstance(result, NeedInputResult):
                    await event_queue.enqueue_event(
                        TaskArtifactUpdateEvent(
                            task_id=task_id,
                            context_id=context_id,
                            artifact=Artifact(
                                artifact_id=uuid.uuid4().hex,
                                name="refactor-input-required",
                                description=result.need_input.message,
                                parts=[
                                    Part(root=TextPart(text=result.need_input.message)),
                                    Part(root=DataPart(data=result.need_input.payload)),
                                ],
                            ),
                            append=False,
                        )
                    )
                    await event_queue.enqueue_event(
                        _status_event(
                            task_id,
                            context_id,
                            TaskState.input_required,
                            result.need_input.message,
                            final=False,
                        )
                    )
                    self._state_store[task_id] = {
                        "message_history": run_state,
                        "workspace_dir": workspace_dir_str,
                    }
                    return
                # FinalOutput
                await _emit_artifacts_from_workspace(
                    workspace_dir, task_id, context_id, event_queue
                )
                await event_queue.enqueue_event(
                    _status_event(
                        task_id,
                        context_id,
                        TaskState.completed,
                        result.output,
                    )
                )
                del self._state_store[task_id]
                if workspace_dir.exists():  # noqa: ASYNC240
                    shutil.rmtree(workspace_dir, ignore_errors=True)
                return

        # Initial request
        if not user_input:
            await event_queue.enqueue_event(
                _status_event(
                    task_id,
                    context_id,
                    TaskState.failed,
                    "ERROR: empty input. Send JSON with refactor request (e.g. "
                    "old_name, new_name, source or workspace).",
                )
            )
            return

        parsed = _parse_rename_params(user_input)
        if isinstance(parsed, str):
            await event_queue.enqueue_event(
                _status_event(task_id, context_id, TaskState.failed, parsed)
            )
            return

        workspace_dir = _build_workspace_dir(parsed)
        try:
            deps = OrchestratorDeps(
                language="python",
                workspace=workspace_dir,
                mode="Auto",
                file_ext="*.py",
                get_user_input=None,
            )
            internal_message = _internal_message_from_parsed(parsed)
            result, run_state = await run_orchestrator(
                self._agent,
                deps,
                internal_message,
                message_history=None,
            )
            if isinstance(result, NeedInputResult):
                await event_queue.enqueue_event(
                    TaskArtifactUpdateEvent(
                        task_id=task_id,
                        context_id=context_id,
                        artifact=Artifact(
                            artifact_id=uuid.uuid4().hex,
                            name="refactor-input-required",
                            description=result.need_input.message,
                            parts=[
                                Part(root=TextPart(text=result.need_input.message)),
                                Part(root=DataPart(data=result.need_input.payload)),
                            ],
                        ),
                        append=False,
                    )
                )
                await event_queue.enqueue_event(
                    _status_event(
                        task_id,
                        context_id,
                        TaskState.input_required,
                        result.need_input.message,
                        final=False,
                    )
                )
                self._state_store[task_id] = {
                    "message_history": run_state,
                    "workspace_dir": str(workspace_dir),
                }
                return
            await _emit_artifacts_from_workspace(
                workspace_dir, task_id, context_id, event_queue
            )
            await event_queue.enqueue_event(
                _status_event(
                    task_id,
                    context_id,
                    TaskState.completed,
                    result.output,
                )
            )
        finally:
            # Cleanup temp dir only when we are not storing state (no NeedInput)
            if task_id not in self._state_store and workspace_dir.exists():
                shutil.rmtree(workspace_dir, ignore_errors=True)

    async def cancel(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Cancel is not supported."""
        raise NotImplementedError("cancel not supported")
